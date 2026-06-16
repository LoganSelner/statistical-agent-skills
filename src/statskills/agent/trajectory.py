"""The agent trajectory — the per-step log of one task run (ROADMAP §6, §9).

Every step records the model's message (``thought``), the code it ran and the
sandbox observation, and token usage. The trajectory is serialisable to a dict
for JSONL storage, kept separate from any score so re-grading never re-runs the
agent.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class AgentStep:
    """One step of the loop."""

    index: int
    kind: str  # "code" | "final" | "no_action"
    thought: str
    code: str | None = None
    observation: str | None = None
    ok: bool | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None


@dataclass(frozen=True)
class Trajectory:
    """The full record of one task run."""

    task_id: str
    model: str
    steps: tuple[AgentStep, ...]
    final_answer: str | None
    stop_reason: str  # "final" | "max_steps" | "no_action"
    prompt_tokens: int
    completion_tokens: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "model": self.model,
            "final_answer": self.final_answer,
            "stop_reason": self.stop_reason,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "steps": [asdict(s) for s in self.steps],
        }
