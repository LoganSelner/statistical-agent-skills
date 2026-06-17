"""Tests for run comparison (baseline vs treatment deltas)."""

from __future__ import annotations

import pytest

from statskills.evaluation.compare import compare_runs, compare_trials
from statskills.evaluation.results import ScoreRecord


def _rec(task_id: str, passed: bool, score: float | None = None) -> ScoreRecord:
    score = (1.0 if passed else 0.0) if score is None else score
    return ScoreRecord(task_id, passed, score, "x", "", "final", 2, 10, 5)


def test_compare_reports_deltas_and_flips():
    baseline = [_rec("a", True), _rec("b", False), _rec("c", True)]
    treatment = [_rec("a", False), _rec("b", True), _rec("c", True)]
    cmp = compare_runs(baseline, treatment)
    assert cmp.n_common == 3
    assert cmp.pass_rate_delta == pytest.approx(0.0)  # one gained, one lost
    assert cmp.gained == ("b",)
    assert cmp.lost == ("a",)


def test_compare_uses_only_shared_tasks():
    baseline = [_rec("a", True), _rec("only_base", False)]
    treatment = [_rec("a", True), _rec("only_treat", True)]
    cmp = compare_runs(baseline, treatment)
    assert cmp.n_common == 1
    assert cmp.baseline.n == 1 and cmp.treatment.n == 1


def test_compare_pasq_delta_tracks_partial_credit():
    baseline = [_rec("a", False, 0.0)]
    treatment = [_rec("a", False, 0.5)]  # partial improvement, still not a pass
    cmp = compare_runs(baseline, treatment)
    assert cmp.pass_rate_delta == pytest.approx(0.0)
    assert cmp.mean_score_delta == pytest.approx(0.5)


def _trial_recs(task_id: str, outcomes: list[bool]) -> list[ScoreRecord]:
    return [
        ScoreRecord(task_id, o, float(o), "x", "", "final", 2, 10, 5, trial=i)
        for i, o in enumerate(outcomes)
    ]


def test_compare_trials_per_task_freq_and_delta():
    off = _trial_recs("welch", [False, False, False, False])
    curated = _trial_recs("welch", [True, False, True, False])
    cmp = compare_trials(off, curated)
    assert cmp.per_task_freq_delta["welch"] == pytest.approx(0.5)  # 0.5 - 0.0
    assert cmp.pass_rate_delta.point == pytest.approx(0.5)
    assert cmp.baseline.n_trials == 4 and cmp.treatment.n_trials == 4
