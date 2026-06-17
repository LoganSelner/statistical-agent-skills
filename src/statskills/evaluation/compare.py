"""Compare two graded runs — per-condition deltas (ROADMAP §8).

Given two sets of :class:`ScoreRecord` (e.g. skills ``off`` vs ``curated``), restrict to
the tasks they share, aggregate each side, and report the pass-rate (ABQ) and
subquestion (PASQ) deltas plus which tasks flipped. Pure and order-independent; the CLI
(``scripts/compare.py``) handles loading and printing.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from statskills.evaluation.metrics import Metrics, aggregate
from statskills.evaluation.results import ScoreRecord
from statskills.evaluation.trials import (
    CI,
    TrialSummary,
    delta_pass_rate_ci,
    summarize_trials,
)


@dataclass(frozen=True)
class Comparison:
    """Baseline vs treatment over the tasks they share."""

    n_common: int
    baseline: Metrics
    treatment: Metrics
    gained: tuple[str, ...]  # failed in baseline, passed in treatment
    lost: tuple[str, ...]  # passed in baseline, failed in treatment

    @property
    def pass_rate_delta(self) -> float:
        return self.treatment.pass_rate - self.baseline.pass_rate

    @property
    def mean_score_delta(self) -> float:
        return self.treatment.mean_score - self.baseline.mean_score


def compare_runs(
    baseline: Sequence[ScoreRecord], treatment: Sequence[ScoreRecord]
) -> Comparison:
    """Compare two graded runs over the tasks present in both."""
    by_base = {r.task_id: r for r in baseline}
    by_treat = {r.task_id: r for r in treatment}
    common = sorted(by_base.keys() & by_treat.keys())
    return Comparison(
        n_common=len(common),
        baseline=aggregate([by_base[t] for t in common]),
        treatment=aggregate([by_treat[t] for t in common]),
        gained=tuple(t for t in common if not by_base[t].passed and by_treat[t].passed),
        lost=tuple(t for t in common if by_base[t].passed and not by_treat[t].passed),
    )


@dataclass(frozen=True)
class TrialComparison:
    """Baseline vs treatment, each summarised over its trials (ROADMAP §5)."""

    baseline: TrialSummary
    treatment: TrialSummary
    pass_rate_delta: CI  # treatment - baseline, with a bootstrap CI over trials
    per_task_freq_delta: dict[str, float]  # task_id -> treatment freq - baseline freq


def compare_trials(
    baseline: Sequence[ScoreRecord], treatment: Sequence[ScoreRecord]
) -> TrialComparison:
    """Compare two N-trial runs: per-task frequency deltas + a bootstrapped delta CI."""
    base, treat = summarize_trials(baseline), summarize_trials(treatment)
    common = sorted(set(base.per_task_pass_freq) & set(treat.per_task_pass_freq))
    return TrialComparison(
        baseline=base,
        treatment=treat,
        pass_rate_delta=delta_pass_rate_ci(baseline, treatment),
        per_task_freq_delta={
            t: treat.per_task_pass_freq[t] - base.per_task_pass_freq[t] for t in common
        },
    )
