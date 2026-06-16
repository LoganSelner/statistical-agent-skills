"""Single-agent ReAct loop with the CodeAct action protocol (ROADMAP §6).

plan -> write code -> execute -> observe -> iterate, up to a step budget. The
action mechanism is harness-parsed code (not provider tool-calling): each turn
the model's text is parsed into a code action (run it, feed back the
observation) or a final answer (stop). A turn with neither is nudged and
retried. One sandbox session is opened per task and closed when the loop ends.
"""

from __future__ import annotations

from statskills.agent.action import CodeAction, FinalAnswer, parse_action
from statskills.agent.context import initial_messages, render_observation
from statskills.agent.llm import LLM
from statskills.agent.prompts import SYSTEM_PROMPT
from statskills.agent.trajectory import AgentStep, Trajectory
from statskills.core.types import Message
from statskills.sandbox.base import Executor
from statskills.tasks.schema import Task

_NUDGE = (
    "Please respond with either a single ```python code block to run, or a line "
    "starting with 'FINAL ANSWER:'."
)
_REPEAT_NUDGE = (
    "You already ran that exact code and its output is shown above. If it answers "
    "the task, reply now with only `FINAL ANSWER: <value>` (no code). Otherwise run "
    "different code."
)


class ReActAgent:
    """Drives one task to a final answer (or the step budget) via CodeAct."""

    def __init__(
        self,
        llm: LLM,
        executor: Executor,
        *,
        max_steps: int = 10,
        system_prompt: str = SYSTEM_PROMPT,
    ) -> None:
        self._llm = llm
        self._executor = executor
        self._max_steps = max_steps
        self._system_prompt = system_prompt

    def run(self, task: Task) -> Trajectory:
        filenames = tuple(d.name for d in task.datasets)
        messages: list[Message] = initial_messages(
            task.prompt, filenames, system_prompt=self._system_prompt
        )
        steps: list[AgentStep] = []
        ran_code: set[str] = set()
        final_answer: str | None = None
        stop_reason = "max_steps"
        prompt_tokens = completion_tokens = 0

        session = self._executor.start(datasets=task.dataset_paths)
        try:
            for i in range(self._max_steps):
                resp = self._llm.complete(messages)
                prompt_tokens += resp.prompt_tokens or 0
                completion_tokens += resp.completion_tokens or 0
                messages.append({"role": "assistant", "content": resp.text})
                action = parse_action(resp.text)

                if isinstance(action, FinalAnswer):
                    steps.append(
                        AgentStep(
                            index=i,
                            kind="final",
                            thought=resp.text,
                            prompt_tokens=resp.prompt_tokens,
                            completion_tokens=resp.completion_tokens,
                        )
                    )
                    final_answer = action.answer
                    stop_reason = "final"
                    break

                if isinstance(action, CodeAction):
                    if action.code in ran_code:
                        # Stuck re-running identical code — nudge to finalize rather
                        # than re-execute (breaks pointless loops).
                        messages.append({"role": "user", "content": _REPEAT_NUDGE})
                        steps.append(
                            AgentStep(
                                index=i,
                                kind="repeat",
                                thought=resp.text,
                                code=action.code,
                                prompt_tokens=resp.prompt_tokens,
                                completion_tokens=resp.completion_tokens,
                            )
                        )
                        continue
                    ran_code.add(action.code)
                    result = session.run(action.code)
                    observation = render_observation(result)
                    messages.append(
                        {"role": "user", "content": f"Observation:\n{observation}"}
                    )
                    steps.append(
                        AgentStep(
                            index=i,
                            kind="code",
                            thought=resp.text,
                            code=action.code,
                            observation=observation,
                            ok=result.ok,
                            prompt_tokens=resp.prompt_tokens,
                            completion_tokens=resp.completion_tokens,
                        )
                    )
                    continue

                # Neither code nor a final answer — nudge and retry.
                messages.append({"role": "user", "content": _NUDGE})
                steps.append(
                    AgentStep(
                        index=i,
                        kind="no_action",
                        thought=resp.text,
                        prompt_tokens=resp.prompt_tokens,
                        completion_tokens=resp.completion_tokens,
                    )
                )
        finally:
            session.close()

        return Trajectory(
            task_id=task.id,
            model=self._llm.model,
            steps=tuple(steps),
            final_answer=final_answer,
            stop_reason=stop_reason,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )
