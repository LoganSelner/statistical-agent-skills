"""Aggregate metrics over scored tasks (ROADMAP §8).

Pass rate + token/step efficiency. Per-condition deltas and confidence intervals
arrive once the experiment matrix introduces conditions (Phase 3+).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from statskills.evaluation.results import ScoreRecord


@dataclass(frozen=True)
class Metrics:
    """Headline metrics for a graded set of tasks."""

    n: int
    pass_rate: float
    mean_steps: float
    mean_prompt_tokens: float
    mean_completion_tokens: float


def aggregate(records: Sequence[ScoreRecord]) -> Metrics:
    """Pass rate + mean step/token efficiency over the scored tasks."""
    n = len(records)
    if n == 0:
        return Metrics(0, 0.0, 0.0, 0.0, 0.0)
    return Metrics(
        n=n,
        pass_rate=sum(r.passed for r in records) / n,
        mean_steps=sum(r.num_steps for r in records) / n,
        mean_prompt_tokens=sum(r.prompt_tokens for r in records) / n,
        mean_completion_tokens=sum(r.completion_tokens for r in records) / n,
    )
