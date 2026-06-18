"""Distribution-aware summaries over N trials per task (ROADMAP §5, §8).

A stochastic agent is run N times per task; this turns the resulting score records into
per-task pass-frequencies and a per-condition pass rate / PASQ with bootstrap confidence
intervals. **Stdlib only** — the scientific stack is not a harness runtime dependency.
The bootstrap resamples *whole trials* (the independent replicate, preserving the
within-trial task structure) and is seeded, so the intervals are reproducible.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Sequence
from dataclasses import dataclass
import random
from statistics import fmean

from statskills.evaluation.results import ScoreRecord

_BOOTSTRAP_SAMPLES = 10_000
_SEED = 0

Trial = Sequence[ScoreRecord]
Statistic = Callable[[Sequence[ScoreRecord]], float]


@dataclass(frozen=True)
class CI:
    """A point estimate with a percentile bootstrap confidence interval."""

    point: float
    low: float
    high: float


@dataclass(frozen=True)
class TrialSummary:
    """One condition summarised over its trials."""

    n_tasks: int
    n_trials: int
    pass_rate: CI  # ABQ, micro-averaged over task x trial
    mean_score: CI  # PASQ
    per_task_pass_freq: dict[str, float]  # task_id -> fraction of trials passed
    mean_steps: float
    mean_prompt_tokens: float
    mean_completion_tokens: float


def by_trial(records: Sequence[ScoreRecord]) -> list[list[ScoreRecord]]:
    """Group records into trial blocks, ordered by trial index."""
    groups: dict[int, list[ScoreRecord]] = defaultdict(list)
    for record in records:
        groups[record.trial].append(record)
    return [groups[t] for t in sorted(groups)]


def pass_rate(records: Sequence[ScoreRecord]) -> float:
    """ABQ pass rate over a flat record list."""
    return sum(r.passed for r in records) / len(records) if records else 0.0


def mean_score(records: Sequence[ScoreRecord]) -> float:
    """PASQ (mean per-task subquestion score) over a flat record list."""
    return fmean(r.score for r in records) if records else 0.0


def bootstrap_ci(
    trials: Sequence[Trial], statistic: Statistic, *, level: float = 0.95
) -> CI:
    """Percentile bootstrap CI for ``statistic``, resampling whole trials."""
    point = statistic([r for trial in trials for r in trial])
    n = len(trials)
    if n <= 1:
        return CI(point, point, point)
    rng = random.Random(_SEED)
    estimates = sorted(
        statistic([r for _ in range(n) for r in rng.choice(trials)])
        for _ in range(_BOOTSTRAP_SAMPLES)
    )
    lo = estimates[int((1 - level) / 2 * _BOOTSTRAP_SAMPLES)]
    hi = estimates[int((1 + level) / 2 * _BOOTSTRAP_SAMPLES) - 1]
    return CI(point, lo, hi)


def delta_pass_rate_ci(
    baseline: Sequence[ScoreRecord],
    treatment: Sequence[ScoreRecord],
    *,
    level: float = 0.95,
) -> CI:
    """Bootstrap CI for the (treatment - baseline) pass-rate delta over trials."""
    base, treat = by_trial(baseline), by_trial(treatment)
    point = pass_rate(treatment) - pass_rate(baseline)
    if len(base) <= 1 or len(treat) <= 1:
        return CI(point, point, point)
    rng = random.Random(_SEED)
    deltas = sorted(
        pass_rate([r for _ in treat for r in rng.choice(treat)])
        - pass_rate([r for _ in base for r in rng.choice(base)])
        for _ in range(_BOOTSTRAP_SAMPLES)
    )
    lo = deltas[int((1 - level) / 2 * _BOOTSTRAP_SAMPLES)]
    hi = deltas[int((1 + level) / 2 * _BOOTSTRAP_SAMPLES) - 1]
    return CI(point, lo, hi)


def summarize_trials(records: Sequence[ScoreRecord]) -> TrialSummary:
    """Per-task pass-frequencies + pass rate / PASQ with bootstrap CIs over trials."""
    trials = by_trial(records)
    by_task: dict[str, list[ScoreRecord]] = defaultdict(list)
    for record in records:
        by_task[record.task_id].append(record)
    return TrialSummary(
        n_tasks=len(by_task),
        n_trials=len(trials),
        pass_rate=bootstrap_ci(trials, pass_rate),
        mean_score=bootstrap_ci(trials, mean_score),
        per_task_pass_freq={t: pass_rate(rs) for t, rs in sorted(by_task.items())},
        mean_steps=fmean(r.num_steps for r in records) if records else 0.0,
        mean_prompt_tokens=fmean(r.prompt_tokens for r in records) if records else 0.0,
        mean_completion_tokens=(
            fmean(r.completion_tokens for r in records) if records else 0.0
        ),
    )
