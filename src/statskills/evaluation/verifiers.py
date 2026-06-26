"""Closed-form verifiers — deterministic, model-free scoring (ROADMAP §8).

A :class:`Verifier` scores a submitted answer against a task's ``ExpectedAnswer``,
returning a :class:`Verdict`. The default ``closed_form`` verifier scores each
``AnswerKey``: an unnamed key against the whole submission, a named key against its
``@name[value]`` token (benchmark multi-part answers). Per key it dispatches on
``kind`` (numeric tolerance, exact/categorical, set, regex). ``passed`` is all keys
correct (DABench ABQ); ``score`` is the fraction correct (PASQ). A task selects its
verifier by name (``Task.verifier``).
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Protocol, runtime_checkable

from statskills.core.registry import registry
from statskills.tasks.schema import AnswerKey, Task


@dataclass(frozen=True)
class Verdict:
    """The outcome of scoring one submission."""

    passed: bool  # all keys correct (all-or-nothing per task)
    score: float  # fraction of keys correct
    detail: str = ""


@runtime_checkable
class Verifier(Protocol):
    """Scores a submitted answer against a task's expected answer."""

    def score(self, submitted: str, task: Task) -> Verdict: ...


# --- per-key value comparisons, keyed by AnswerKey.kind -------------------------

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


_MD_EMPHASIS = re.compile(r"[*_`]+")


def _strip_md(text: str) -> str:
    """Remove Markdown emphasis (``*``/``_``/`` ` ``) so a model that bolds its answer
    (frontier models routinely emit ``**Yes**``) still matches the category."""
    return _MD_EMPHASIS.sub("", text)


def _to_set(value: object) -> set[str]:
    items = (
        [str(v) for v in value]
        if isinstance(value, (list, tuple, set))
        else re.split(r"[,\s]+", str(value).strip())
    )
    return {_norm(i).casefold() for i in items if i}


def _numeric(submitted: str, key: AnswerKey) -> tuple[bool, str]:
    got = _extract_number(submitted)
    if got is None:
        return False, f"no number in {submitted!r}"
    want = float(str(key.value))
    tol = key.tolerance if key.tolerance is not None else _DEFAULT_TOLERANCE
    return abs(got - want) <= tol, f"{got} vs {want} (tol {tol})"


def _exact(submitted: str, key: AnswerKey) -> tuple[bool, str]:
    return _norm(submitted) == _norm(key.value), f"{submitted!r} vs {key.value!r}"


def _categorical(submitted: str, key: AnswerKey) -> tuple[bool, str]:
    """Case-insensitive match, lenient only to a trailing *justification*.

    Passes if the whole submission equals the category, or leads with it followed by a
    clause delimiter — comma, period, colon, semicolon, dash, paren, or newline — so
    ``No, because p > 0.16`` scores as ``No``. A plain space or slash does not qualify,
    so a short label is not falsely matched by ``A result`` or ``Yes/No`` (DABench runs
    every non-numeric label through here), nor ``No`` by ``Not significant``.
    """
    want = _norm(key.value).casefold()
    detail = f"{submitted!r} vs {key.value!r}"  # keep the original for the trace
    cleaned = _strip_md(submitted)  # tolerate ``**Yes**`` emphasis from the model
    if _norm(cleaned).casefold() == want:
        return True, detail
    if want == "":
        return False, detail
    pattern = re.escape(want) + r"[ \t]*[,.;:!?()\n-]"
    return re.match(pattern, cleaned.strip().casefold()) is not None, detail


def _set(submitted: str, key: AnswerKey) -> tuple[bool, str]:
    got, want = _to_set(submitted), _to_set(key.value)
    return got == want, f"{got} vs {want}"


def _regex(submitted: str, key: AnswerKey) -> tuple[bool, str]:
    ok = re.search(str(key.value), submitted) is not None
    return ok, f"{submitted!r} ~ /{key.value}/"


_COMPARISONS = {
    "numeric": _numeric,
    "exact": _exact,
    "categorical": _categorical,
    "set": _set,
    "regex": _regex,
}


def _extract_named(text: str, name: str) -> str | None:
    """The value inside a ``@name[value]`` token, or ``None`` if absent."""
    match = re.search(rf"@{re.escape(name)}\[([^\]]*)\]", text)
    return match.group(1) if match else None


@registry.register("verifier", "closed_form")
class ClosedFormVerifier:
    """Scores each AnswerKey (the whole submission, or its ``@name[value]`` token)."""

    def score(self, submitted: str, task: Task) -> Verdict:
        expected = task.expected
        if expected is None or not expected.keys:
            return Verdict(False, 0.0, "task has no expected answer")

        results: list[tuple[str, bool, str]] = []
        for key in expected.keys:
            value = submitted if not key.name else _extract_named(submitted, key.name)
            compare = _COMPARISONS.get(key.kind)
            if compare is None:
                results.append((key.name, False, f"unknown kind {key.kind!r}"))
            elif value is None:
                # Absent named token only. A present-but-empty value (``@name[]``) is a
                # real answer ("none"), so it is compared — empty ground truth can pass.
                results.append((key.name, False, "missing"))
            else:
                passed, detail = compare(value, key)
                results.append((key.name, passed, detail))

        n = len(results)
        n_passed = sum(passed for _, passed, _ in results)
        detail = "; ".join(
            f"{name or 'answer'}: {'ok' if passed else 'X'} ({d})"
            for name, passed, d in results
        )
        return Verdict(n_passed == n, n_passed / n, detail)


def get_verifier(name: str) -> Verifier:
    """Resolve a registered verifier by name (e.g. ``Task.verifier``)."""
    verifier: Verifier = registry.get("verifier", name)()
    return verifier
