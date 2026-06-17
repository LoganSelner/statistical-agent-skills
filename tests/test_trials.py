"""Tests for N-trials summaries + stdlib bootstrap CIs."""

from __future__ import annotations

import pytest

from statskills.evaluation.results import ScoreRecord
from statskills.evaluation.trials import delta_pass_rate_ci, summarize_trials


def _records(per_task: dict[str, list[bool]]) -> list[ScoreRecord]:
    """Build score records from {task_id: [outcome per trial]}."""
    records = []
    n_trials = len(next(iter(per_task.values())))
    for trial in range(n_trials):
        for task_id, outcomes in per_task.items():
            passed = outcomes[trial]
            records.append(
                ScoreRecord(
                    task_id,
                    passed,
                    float(passed),
                    "x",
                    "",
                    "final",
                    2,
                    10,
                    5,
                    trial=trial,
                )
            )
    return records


def test_per_task_pass_frequency():
    summary = summarize_trials(
        _records({"a": [True, True, False, False, True], "b": [False] * 5})
    )
    assert summary.n_trials == 5 and summary.n_tasks == 2
    assert summary.per_task_pass_freq["a"] == pytest.approx(0.6)  # 3/5
    assert summary.per_task_pass_freq["b"] == 0.0


def test_pass_rate_point_and_ci_brackets_it():
    summary = summarize_trials(
        _records(
            {
                "a": [True, True, False, False, True],
                "b": [True, False, False, False, False],
            }
        )
    )
    assert summary.pass_rate.point == pytest.approx(0.4)  # 4 of 10 records
    assert summary.pass_rate.low <= summary.pass_rate.point <= summary.pass_rate.high
    assert summary.pass_rate.low < summary.pass_rate.high  # non-degenerate CI


def test_bootstrap_ci_is_deterministic():
    records = _records({"a": [True, False, True, False, True]})
    first, second = summarize_trials(records), summarize_trials(records)
    assert (first.pass_rate.low, first.pass_rate.high) == (
        second.pass_rate.low,
        second.pass_rate.high,
    )


def test_single_trial_ci_is_degenerate():
    summary = summarize_trials(_records({"a": [True], "b": [False]}))
    assert summary.n_trials == 1
    assert summary.pass_rate.low == summary.pass_rate.point == summary.pass_rate.high


def test_delta_pass_rate_ci_brackets_point():
    off = _records({"a": [True, False, True, False, False]})  # 2/5 = 0.4
    curated = _records({"a": [True, True, True, False, True]})  # 4/5 = 0.8
    ci = delta_pass_rate_ci(off, curated)
    assert ci.point == pytest.approx(0.4)  # 0.8 - 0.4
    assert ci.low <= ci.point <= ci.high
