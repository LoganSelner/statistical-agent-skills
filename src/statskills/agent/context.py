"""Explicit context assembly + observation rendering for the agent loop.

Keeps the message list the model sees inspectable and deterministic: a system
prompt, the task turn, then alternating assistant turns and rendered sandbox
observations.
"""

from __future__ import annotations

from statskills.agent.prompts import SYSTEM_PROMPT, build_task_prompt
from statskills.core.types import Message
from statskills.sandbox.base import ExecResult

_MAX_OBS_CHARS = 4000


def initial_messages(
    task_prompt: str,
    filenames: tuple[str, ...],
    *,
    system_prompt: str = SYSTEM_PROMPT,
) -> list[Message]:
    """The opening system + task messages."""
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": build_task_prompt(task_prompt, filenames)},
    ]


def render_observation(result: ExecResult, *, max_chars: int = _MAX_OBS_CHARS) -> str:
    """Render a sandbox result as the observation text fed back to the agent."""
    if result.timed_out:
        return "[Execution timed out before producing output.]"
    parts: list[str] = []
    if result.stdout.strip():
        parts.append(result.stdout.rstrip())
    if result.stderr.strip():
        parts.append("[stderr]\n" + result.stderr.rstrip())
    body = (
        "\n".join(parts)
        if parts
        else "[No output — remember to print() what you want to see.]"
    )
    return _truncate(body, max_chars)


def _truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    half = max_chars // 2
    dropped = len(text) - 2 * half
    return f"{text[:half]}\n... [truncated {dropped} chars] ...\n{text[-half:]}"
