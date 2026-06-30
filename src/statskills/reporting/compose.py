"""LLM-composer: narrate a saved trajectory into a typed :class:`Report` (ROADMAP §10).

One LLM pass turns a completed analysis — the trajectory's code steps, their printed
observations, and the final answer — into the structured report schema, citing the step
behind every quantitative result. The model is constrained by the schema and re-prompted
on malformed output (bounded retries with the parse error); the parsed report is then
run through :func:`verify`, so each cited number is checked against its observation. It
stays provider-agnostic (prompt + parse, not a provider strict-mode), matching the
harness-parsed action protocol; a pure consumer that never re-runs the agent.
"""

from __future__ import annotations

from collections.abc import Mapping
import json
import re
from typing import Any

from statskills.agent.llm import LLM
from statskills.core.types import Message
from statskills.reporting.evidence import observed_steps
from statskills.reporting.schema import Report, ReportSchemaError, parse_report
from statskills.reporting.verify import verify
from statskills.tasks.schema import Task

_MAX_RETRIES = 2
_MAX_OBS_CHARS = 2000  # cap each step's observation in the prompt

_SYSTEM = """\
You turn a completed data-analysis transcript into a STRUCTURED statistical report.

Return ONLY a JSON object (no prose around it) with these keys:
- "question", "data_summary", "method", "assumption_checks", "interpretation",
  "caveats": strings. "method" says which method was used and why; "assumption_checks"
  states the checks performed and their results.
- "results": a list of objects {"label": str, "value": str, "step": int}, one per
  quantitative finding. "value" is the number exactly as printed by the analysis; "step"
  is the [Step N] whose output printed it.

Hard rule: NEVER state a number that does not appear verbatim in a step's output, and
cite the step that printed it. Ground every figure in the transcript."""

_REPAIR = (
    "That response was not a schema-valid report ({error}). Return ONLY the JSON "
    "object with the required keys; cite a real [Step N] for every result value."
)

_FENCE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


class ReportComposeError(RuntimeError):
    """No schema-valid report was produced within the retry budget."""


def compose_report(
    trajectory: Mapping[str, Any],
    task: Task,
    llm: LLM,
    *,
    max_retries: int = _MAX_RETRIES,
) -> Report:
    """Narrate ``trajectory`` into a verified :class:`Report` (one retried LLM pass)."""
    task_id = str(trajectory.get("task_id") or task.id)
    messages: list[Message] = [
        {"role": "system", "content": _SYSTEM},
        {"role": "user", "content": _user_prompt(trajectory, task)},
    ]
    last_error = "no response"
    for _ in range(max_retries + 1):
        text = llm.complete(messages).text
        try:
            report = parse_report(task_id, _parse_json(text))
        except (ReportSchemaError, ValueError) as exc:
            last_error = str(exc)
            messages.append({"role": "assistant", "content": text})
            messages.append(
                {"role": "user", "content": _REPAIR.format(error=last_error)}
            )
            continue
        return verify(report, trajectory)
    raise ReportComposeError(
        f"no schema-valid report after {max_retries + 1} attempt(s): {last_error}"
    )


def _user_prompt(trajectory: Mapping[str, Any], task: Task) -> str:
    lines = [f"Question:\n{task.prompt}\n", "Analysis steps (cite these [Step N]):"]
    for step in observed_steps(trajectory):
        observation = step.observation
        if len(observation) > _MAX_OBS_CHARS:
            observation = observation[:_MAX_OBS_CHARS] + "\n…[truncated]"
        lines.append(
            f"\n[Step {step.index}] code:\n{step.code}\noutput:\n{observation}"
        )
    final = trajectory.get("final_answer")
    if final:
        lines.append(f"\nThe agent's final answer was: {final}")
    return "\n".join(lines)


def _parse_json(text: str) -> Mapping[str, Any]:
    """Parse a JSON object from the model text, tolerating a ```json fence."""
    match = _FENCE.search(text)
    raw = match.group(1) if match else text
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"not valid JSON ({exc})") from exc
    if not isinstance(obj, dict):
        raise ValueError("expected a JSON object")
    return obj
