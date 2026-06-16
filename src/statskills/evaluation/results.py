"""The scored-result record — kept separate from trajectories (ROADMAP §3)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ScoreRecord:
    """One graded task: the verdict plus a few fields for analysis."""

    task_id: str
    passed: bool
    score: float
    submitted: str | None
    detail: str
    stop_reason: str
    num_steps: int
    prompt_tokens: int
    completion_tokens: int
