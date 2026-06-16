"""Tests for metric aggregation."""

from __future__ import annotations

from statskills.evaluation.metrics import aggregate
from statskills.evaluation.results import ScoreRecord


def _rec(passed: bool, steps: int = 2, pt: int = 10, ct: int = 5) -> ScoreRecord:
    return ScoreRecord(
        "t", passed, 1.0 if passed else 0.0, "x", "", "final", steps, pt, ct
    )


def test_aggregate_pass_rate_and_means():
    m = aggregate([_rec(True), _rec(False), _rec(True), _rec(True)])
    assert m.n == 4
    assert m.pass_rate == 0.75
    assert m.mean_steps == 2.0
    assert m.mean_prompt_tokens == 10.0
    assert m.mean_completion_tokens == 5.0


def test_aggregate_empty_is_zeros():
    m = aggregate([])
    assert m.n == 0 and m.pass_rate == 0.0
