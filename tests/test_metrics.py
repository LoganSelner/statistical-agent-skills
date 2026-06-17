"""Tests for metric aggregation."""

from __future__ import annotations

import pytest

from statskills.evaluation.metrics import aggregate
from statskills.evaluation.results import ScoreRecord


def _rec(
    passed: bool, score: float | None = None, steps: int = 2, pt: int = 10, ct: int = 5
) -> ScoreRecord:
    score = (1.0 if passed else 0.0) if score is None else score
    return ScoreRecord("t", passed, score, "x", "", "final", steps, pt, ct)


def test_aggregate_pass_rate_and_means():
    m = aggregate([_rec(True), _rec(False), _rec(True), _rec(True)])
    assert m.n == 4
    assert m.pass_rate == 0.75
    assert m.mean_steps == 2.0
    assert m.mean_prompt_tokens == 10.0
    assert m.mean_completion_tokens == 5.0


def test_pasq_is_mean_subquestion_score():
    # a partially-correct task (score 0.5) lifts PASQ above the all-or-nothing pass rate
    m = aggregate([_rec(True, 1.0), _rec(False, 0.5), _rec(False, 0.0)])
    assert m.pass_rate == pytest.approx(1 / 3)
    assert m.mean_score == pytest.approx(0.5)


def test_aggregate_empty_is_zeros():
    m = aggregate([])
    assert m.n == 0 and m.pass_rate == 0.0 and m.mean_score == 0.0
