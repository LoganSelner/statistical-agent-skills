"""Tests for the closed-form verifiers (single- and multi-key)."""

from __future__ import annotations

from statskills.evaluation.verifiers import ClosedFormVerifier, Verdict, get_verifier
from statskills.tasks.schema import AnswerKey, ExpectedAnswer, Task


def _score(submitted: str, expected: ExpectedAnswer | None) -> Verdict:
    return ClosedFormVerifier().score(
        submitted, Task(id="t", prompt="p", expected=expected)
    )


# --- single-key comparisons -----------------------------------------------------


def test_numeric_trailing_zero_passes():
    v = _score("16.00", ExpectedAnswer.single(16.0, "numeric", tolerance=5e-3))
    assert v.passed and v.score == 1.0


def test_numeric_within_tolerance_passes():
    assert _score(
        "0.999", ExpectedAnswer.single(0.999, "numeric", tolerance=5e-4)
    ).passed


def test_numeric_genuine_error_fails():
    v = _score("0.0040", ExpectedAnswer.single(0.0039, "numeric", tolerance=5e-5))
    assert not v.passed and v.score == 0.0


def test_numeric_extracts_first_number_ignoring_notes():
    assert _score(
        "16.00 (rounded to 2 decimals)",
        ExpectedAnswer.single(16.0, "numeric", tolerance=5e-3),
    ).passed
    assert _score(
        "p=0.0039 rounded to 4 decimals",
        ExpectedAnswer.single(0.0039, "numeric", tolerance=5e-5),
    ).passed


def test_numeric_no_number_fails():
    assert not _score("no number here", ExpectedAnswer.single(1.0, "numeric")).passed


def test_numeric_discrete_count_rejects_non_integer():
    assert _score("3", ExpectedAnswer.single(3, "numeric", tolerance=1e-9)).passed
    assert not _score("2.6", ExpectedAnswer.single(3, "numeric", tolerance=1e-9)).passed


def test_categorical_is_case_insensitive():
    assert _score("south", ExpectedAnswer.single("South", "categorical")).passed
    assert not _score("North", ExpectedAnswer.single("South", "categorical")).passed


def test_categorical_accepts_leading_answer_with_justification():
    # models routinely answer "No, because ..." rather than a bare "No"
    assert _score(
        "No, because the Welch p-value is 0.16.",
        ExpectedAnswer.single("No", "categorical"),
    ).passed
    assert _score(
        "Yes\n\nThe difference is significant.",
        ExpectedAnswer.single("Yes", "categorical"),
    ).passed


def test_categorical_rejects_ambiguous_or_unrelated_lead():
    # only a real delimiter qualifies (not any word boundary), protecting short labels
    assert not _score("Yes/No", ExpectedAnswer.single("Yes", "categorical")).passed
    assert not _score("A result", ExpectedAnswer.single("A", "categorical")).passed
    no = ExpectedAnswer.single("No", "categorical")
    assert not _score("Not significant", no).passed


def test_categorical_tolerates_markdown_emphasis():
    # frontier models routinely bold their answer; emphasis must not block the match
    yes = ExpectedAnswer.single("Yes", "categorical")
    assert _score("**Yes**", yes).passed
    assert _score("_No_", ExpectedAnswer.single("No", "categorical")).passed
    # the exact Haiku smoke case: "Yes**" + a Markdown-broken justification
    assert _score(
        "Yes**\n\nThere is a statistically significant change (p < 0.001).", yes
    ).passed
    # stripping emphasis must not manufacture a false positive
    assert not _score("Yesterday", yes).passed


def test_categorical_preserves_literal_emphasis_characters():
    # emphasis is unwrapped at the edges only — markers *inside* a label are kept, so a
    # legitimate snake_case label matches and an internal marker is not silently removed
    # (DABench routes every non-numeric label through `categorical`).
    group_a = ExpectedAnswer.single("group_a", "categorical")
    assert _score("group_a", group_a).passed
    assert _score("**group_a**", group_a).passed  # bold wrapper ok, the "_" is kept
    assert not _score("Y_es", ExpectedAnswer.single("Yes", "categorical")).passed


def test_exact_is_case_sensitive():
    assert _score("South", ExpectedAnswer.single("South", "exact")).passed
    assert not _score("south", ExpectedAnswer.single("South", "exact")).passed


def test_set_is_unordered():
    assert _score("a, b, c", ExpectedAnswer.single(["c", "b", "a"], "set")).passed
    assert not _score("a, b", ExpectedAnswer.single(["a", "b", "c"], "set")).passed


def test_regex_matches():
    assert _score("p=0.03", ExpectedAnswer.single(r"0\.0\d", "regex")).passed
    assert not _score("p=0.3", ExpectedAnswer.single(r"0\.0\d", "regex")).passed


def test_empty_submission_fails():
    assert not _score("   ", ExpectedAnswer.single(1.0, "numeric")).passed


def test_no_expected_answer_fails():
    assert not _score("16.0", None).passed
    assert not _score("16.0", ExpectedAnswer(keys=())).passed


def test_unknown_kind_fails():
    v = _score("x", ExpectedAnswer.single("x", "bogus"))
    assert not v.passed and "unknown kind" in v.detail


# --- multi-key (@name[value]) ---------------------------------------------------


def _multi() -> ExpectedAnswer:
    return ExpectedAnswer(
        keys=(
            AnswerKey("43.47", "numeric", tolerance=5e-3, name="mean_fare_elderly"),
            AnswerKey("31.98", "numeric", tolerance=5e-3, name="mean_fare_teenager"),
        )
    )


def test_multi_key_all_correct_passes():
    v = _score("@mean_fare_elderly[43.47] @mean_fare_teenager[31.98]", _multi())
    assert v.passed and v.score == 1.0


def test_multi_key_partial_gives_fractional_score():
    v = _score("@mean_fare_elderly[43.47] @mean_fare_teenager[99.0]", _multi())
    assert not v.passed and v.score == 0.5


def test_multi_key_missing_key_fails():
    v = _score("@mean_fare_elderly[43.47]", _multi())  # teenager missing
    assert not v.passed and v.score == 0.5
    assert "missing" in v.detail


def test_empty_named_value_matches_empty_expected():
    # DABench labels an empty answer (e.g. "no outliers") as ``@name[]``; the exact
    # empty token must pass, not be treated as a missing answer.
    expected = ExpectedAnswer(keys=(AnswerKey("", "categorical", name="outliers"),))
    assert _score("@outliers[]", expected).passed


def test_absent_named_token_is_missing_even_for_empty_expected():
    # Omitting the token entirely is still missing — the model asserted nothing.
    expected = ExpectedAnswer(keys=(AnswerKey("", "categorical", name="outliers"),))
    v = _score("the dataset has no outliers", expected)
    assert not v.passed and "missing" in v.detail


def test_empty_named_value_fails_when_expected_is_nonempty():
    expected = ExpectedAnswer(keys=(AnswerKey("South", "categorical", name="region"),))
    assert not _score("@region[]", expected).passed


def test_get_verifier_resolves_closed_form():
    assert isinstance(get_verifier("closed_form"), ClosedFormVerifier)
