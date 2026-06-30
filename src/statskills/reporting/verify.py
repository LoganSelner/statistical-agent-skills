"""Anti-fabrication check: every cited number must appear in its observation (§10).

The ``compute-dont-fabricate`` skill, mechanized as an *output contract*: a report may
not state a statistic the agent did not compute and print. For each :class:`Claim` we
check — **deterministically**, never by asking a model — whether its number is among the
numbers printed in its cited step's observation. (Numeric self-verification by an LLM is
unreliable, so the contract has teeth only if the check is mechanical.) The match
tolerates rounding: the claim is supported if its value equals a printed number at the
claim's stated precision or within a small relative tolerance. stdlib only.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
import re
from typing import Any

from statskills.reporting.evidence import observed_steps
from statskills.reporting.schema import Claim, Report

_NUMBER = re.compile(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?")
_REL_TOLERANCE = 1e-3


def verify(report: Report, trajectory: Mapping[str, Any]) -> Report:
    """Return ``report`` with each :attr:`Claim.verified` set against the trajectory."""
    observations = {step.index: step.observation for step in observed_steps(trajectory)}
    checked = tuple(
        replace(claim, verified=_supported(claim, observations.get(claim.step)))
        for claim in report.results
    )
    return replace(report, results=checked)


def unverified(report: Report) -> tuple[Claim, ...]:
    """Claims whose number could not be traced to their cited observation."""
    return tuple(claim for claim in report.results if claim.verified is False)


def _supported(claim: Claim, observation: str | None) -> bool:
    if observation is None:  # cited a step that ran no code / does not exist
        return False
    want = _first_number(claim.value)
    if want is None:  # a quantitative claim must carry a number
        return False
    decimals = _decimals(claim.value)
    return any(_matches(want, n, decimals) for n in _numbers(observation))


def _matches(want: float, printed: float, decimals: int) -> bool:
    """A claim is supported if it equals a printed number — exactly, at the claim's
    stated precision (0.16 matches a printed 0.1551), or within a small relative tol."""
    return (
        abs(printed - want) <= 1e-9
        or round(printed, decimals) == round(want, decimals)
        or abs(printed - want) <= _REL_TOLERANCE * max(1.0, abs(want))
    )


def _numbers(text: str) -> list[float]:
    out: list[float] = []
    for token in _NUMBER.findall(text):
        try:
            out.append(float(token))
        except ValueError:
            pass
    return out


def _first_number(text: str) -> float | None:
    numbers = _numbers(text)
    return numbers[0] if numbers else None


def _decimals(text: str) -> int:
    match = re.search(r"\.(\d+)", text)
    return len(match.group(1)) if match else 0
