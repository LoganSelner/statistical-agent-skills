"""Closed-form verifiers — deterministic, model-free scoring (ROADMAP §8).

A :class:`Verifier` scores a submitted answer string against a task's
:class:`~statskills.tasks.schema.ExpectedAnswer`, returning a :class:`Verdict`. The
default ``closed_form`` verifier dispatches on ``ExpectedAnswer.kind`` to a comparison
(numeric tolerance, exact/categorical string, unordered set, regex). Verifiers are
registered so a task selects one by name (``Task.verifier``) and future specialised
verifiers drop in without touching the loop or the grader.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Protocol, runtime_checkable

from statskills.core.registry import registry
from statskills.tasks.schema import ExpectedAnswer, Task


@dataclass(frozen=True)
class Verdict:
    """The outcome of scoring one submission."""

    passed: bool
    score: float  # 1.0 / 0.0 for a single closed-form answer
    detail: str = ""


@runtime_checkable
class Verifier(Protocol):
    """Scores a submitted answer against a task's expected answer."""

    def score(self, submitted: str, task: Task) -> Verdict: ...


# --- comparisons, keyed by ExpectedAnswer.kind ----------------------------------

_NUMBER = re.compile(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?")
_DEFAULT_TOLERANCE = 1e-6


def _extract_number(text: str) -> float | None:
    """Best-effort: the whole string as a float, else the FIRST number in it.

    The value leads the answer (the prompt is ``FINAL ANSWER: <value>``); explanatory
    notes like ``(rounded to 2 decimals)`` follow and must not be graded instead of it.
    """
    try:
        return float(text.strip())
    except ValueError:
        pass
    matches = _NUMBER.findall(text)
    return float(matches[0]) if matches else None


def _norm(value: object) -> str:
    return " ".join(str(value).strip().split())


def _to_set(value: object) -> set[str]:
    items = (
        [str(v) for v in value]
        if isinstance(value, (list, tuple, set))
        else re.split(r"[,\s]+", str(value).strip())
    )
    return {_norm(i).casefold() for i in items if i}


def _numeric(submitted: str, expected: ExpectedAnswer) -> tuple[bool, str]:
    got = _extract_number(submitted)
    if got is None:
        return False, f"no number found in {submitted!r}"
    want = float(str(expected.value))
    tol = expected.tolerance if expected.tolerance is not None else _DEFAULT_TOLERANCE
    return abs(got - want) <= tol, f"{got} vs {want} (tol {tol})"


def _exact(submitted: str, expected: ExpectedAnswer) -> tuple[bool, str]:
    return _norm(submitted) == _norm(
        expected.value
    ), f"{submitted!r} vs {expected.value!r}"


def _categorical(submitted: str, expected: ExpectedAnswer) -> tuple[bool, str]:
    ok = _norm(submitted).casefold() == _norm(expected.value).casefold()
    return ok, f"{submitted!r} vs {expected.value!r}"


def _set(submitted: str, expected: ExpectedAnswer) -> tuple[bool, str]:
    got, want = _to_set(submitted), _to_set(expected.value)
    return got == want, f"{got} vs {want}"


def _regex(submitted: str, expected: ExpectedAnswer) -> tuple[bool, str]:
    ok = re.search(str(expected.value), submitted) is not None
    return ok, f"{submitted!r} ~ /{expected.value}/"


_COMPARISONS = {
    "numeric": _numeric,
    "exact": _exact,
    "categorical": _categorical,
    "set": _set,
    "regex": _regex,
}


@registry.register("verifier", "closed_form")
class ClosedFormVerifier:
    """Scores a single closed-form answer, dispatching on ``ExpectedAnswer.kind``."""

    def score(self, submitted: str, task: Task) -> Verdict:
        expected = task.expected
        if expected is None:
            return Verdict(False, 0.0, "task has no expected answer")
        compare = _COMPARISONS.get(expected.kind)
        if compare is None:
            return Verdict(False, 0.0, f"unknown answer kind {expected.kind!r}")
        if not submitted.strip():
            return Verdict(False, 0.0, "empty submission")
        passed, detail = compare(submitted, expected)
        return Verdict(passed, 1.0 if passed else 0.0, detail)


def get_verifier(name: str) -> Verifier:
    """Resolve a registered verifier by name (e.g. ``Task.verifier``)."""
    verifier: Verifier = registry.get("verifier", name)()
    return verifier
