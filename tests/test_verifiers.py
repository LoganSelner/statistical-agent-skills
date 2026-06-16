"""Tests for the closed-form verifiers."""

from __future__ import annotations

from statskills.evaluation.verifiers import ClosedFormVerifier, Verdict, get_verifier
from statskills.tasks.schema import ExpectedAnswer, Task


def _score(submitted: str, expected: ExpectedAnswer | None) -> Verdict:
    return ClosedFormVerifier().score(
        submitted, Task(id="t", prompt="p", expected=expected)
    )


def test_numeric_trailing_zero_passes():
    v = _score("16.00", ExpectedAnswer(16.0, "numeric", tolerance=5e-3))
    assert v.passed and v.score == 1.0


def test_numeric_within_tolerance_passes():
    assert _score("0.999", ExpectedAnswer(0.999, "numeric", tolerance=5e-4)).passed


def test_numeric_genuine_error_fails():
    # The t-test case: model said 0.0040, ground truth 0.0039 (off by 1e-4 > 5e-5).
    v = _score("0.0040", ExpectedAnswer(0.0039, "numeric", tolerance=5e-5))
    assert not v.passed and v.score == 0.0


def test_numeric_extracts_number_from_text():
    assert _score(
        "The mean is 16.0", ExpectedAnswer(16.0, "numeric", tolerance=1e-3)
    ).passed


def test_numeric_no_number_fails():
    assert not _score("no number here", ExpectedAnswer(1.0, "numeric")).passed


def test_numeric_ignores_trailing_explanatory_note():
    # The value leads; a trailing "(rounded to N decimals)" must not be graded.
    assert _score(
        "16.00 (rounded to 2 decimals)", ExpectedAnswer(16.0, "numeric", tolerance=5e-3)
    ).passed
    assert _score(
        "p=0.0039 rounded to 4 decimals",
        ExpectedAnswer(0.0039, "numeric", tolerance=5e-5),
    ).passed


def test_numeric_discrete_count_rejects_non_integer():
    # A near-zero tolerance must reject a non-integer count, not accept ~3.
    assert _score("3", ExpectedAnswer(3, "numeric", tolerance=1e-9)).passed
    assert not _score("2.6", ExpectedAnswer(3, "numeric", tolerance=1e-9)).passed


def test_categorical_is_case_insensitive():
    assert _score("south", ExpectedAnswer("South", "categorical")).passed
    assert not _score("North", ExpectedAnswer("South", "categorical")).passed


def test_exact_is_case_sensitive():
    assert _score("South", ExpectedAnswer("South", "exact")).passed
    assert not _score("south", ExpectedAnswer("South", "exact")).passed


def test_set_is_unordered():
    assert _score("a, b, c", ExpectedAnswer(["c", "b", "a"], "set")).passed
    assert not _score("a, b", ExpectedAnswer(["a", "b", "c"], "set")).passed


def test_regex_matches():
    assert _score("p=0.03", ExpectedAnswer(r"0\.0\d", "regex")).passed
    assert not _score("p=0.3", ExpectedAnswer(r"0\.0\d", "regex")).passed


def test_empty_submission_fails():
    assert not _score("   ", ExpectedAnswer(1.0, "numeric")).passed


def test_no_expected_answer_fails():
    v = _score("16.0", None)
    assert not v.passed and "no expected" in v.detail


def test_unknown_kind_fails():
    v = _score("x", ExpectedAnswer("x", "bogus"))
    assert not v.passed and "unknown answer kind" in v.detail


def test_get_verifier_resolves_closed_form():
    assert isinstance(get_verifier("closed_form"), ClosedFormVerifier)
