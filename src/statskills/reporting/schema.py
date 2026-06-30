"""The typed report — a narrated, traceable trajectory (ROADMAP §10).

Where an :class:`~statskills.evaluation.results.ScoreRecord` *scores* a trajectory, a
:class:`Report` *narrates* one: the sections a reader of a statistical analysis expects
(question & data → method → assumptions → results → interpretation → caveats), with each
quantitative finding carried as a :class:`Claim` that points back to the trajectory step
that computed it. Frozen dataclasses + ``to_dict`` mirror the rest of the harness;
:func:`parse_report` turns a composer's JSON payload into a validated ``Report``.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import Any


class ReportSchemaError(ValueError):
    """A composer payload did not match the report schema (drives the compose retry)."""


@dataclass(frozen=True)
class Claim:
    """One traceable quantitative finding: a value and the step that computed it.

    ``verified`` is filled by :func:`statskills.reporting.verify.verify` — ``True`` when
    ``value``'s number appears in the cited step's observation, ``False`` when it does
    not, ``None`` before verification.
    """

    label: str  # e.g. "Welch t-test p-value"
    value: str  # the number as stated, e.g. "0.155"
    step: int  # cited trajectory step index (the provenance pointer)
    verified: bool | None = None


@dataclass(frozen=True)
class Figure:
    """A diagnostic figure: a saved image, its caption, and the step it visualises.

    ``path`` is relative to the rendered report. ``step`` is the trajectory step whose
    diagnostic this figure visualises (the provenance pointer), or ``None`` if ungated.
    """

    path: str
    caption: str
    step: int | None = None


@dataclass(frozen=True)
class Report:
    """A structured narration of one trajectory (the §10 sections)."""

    task_id: str
    question: str  # the task question, restated
    data_summary: str  # what the data is
    method: str  # the method chosen and why
    assumption_checks: str  # assumptions performed and their results
    results: tuple[Claim, ...]  # the quantitative findings, each traceable
    interpretation: str
    caveats: str
    figures: tuple[Figure, ...] = ()  # diagnostic plots, attached at report time

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# The free-text sections a composer payload must supply (``results`` is handled apart).
_TEXT_FIELDS = (
    "question",
    "data_summary",
    "method",
    "assumption_checks",
    "interpretation",
    "caveats",
)


def parse_report(task_id: str, payload: Mapping[str, Any]) -> Report:
    """Build a :class:`Report` from a composer's JSON payload, validating its shape.

    ``task_id`` comes from the trajectory (not the model — it must not be invented).
    Raises :class:`ReportSchemaError` with a specific message on any missing/mistyped
    field, so :func:`statskills.reporting.compose.compose_report` can re-prompt with it.
    """
    missing = [f for f in (*_TEXT_FIELDS, "results") if f not in payload]
    if missing:
        raise ReportSchemaError(f"missing field(s): {', '.join(missing)}")
    raw_results = payload["results"]
    if not isinstance(raw_results, list):
        raise ReportSchemaError("'results' must be a list of {label, value, step}")
    claims: list[Claim] = []
    for i, item in enumerate(raw_results):
        if not isinstance(item, Mapping):
            raise ReportSchemaError(f"results[{i}] must be an object")
        try:
            claims.append(
                Claim(
                    label=str(item["label"]),
                    value=str(item["value"]),
                    step=int(item["step"]),
                )
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ReportSchemaError(
                f"results[{i}] is not a valid claim: {exc}"
            ) from exc
    return Report(
        task_id=task_id,
        question=str(payload["question"]),
        data_summary=str(payload["data_summary"]),
        method=str(payload["method"]),
        assumption_checks=str(payload["assumption_checks"]),
        results=tuple(claims),
        interpretation=str(payload["interpretation"]),
        caveats=str(payload["caveats"]),
    )
