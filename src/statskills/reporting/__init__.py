"""Reporting — narrate a trajectory into a typed, traceable report (ROADMAP §10).

The deliverable-track sibling of :mod:`statskills.evaluation`: where evaluation *scores*
a saved trajectory, reporting *narrates* one into a :class:`Report`. It is a pure
trajectory consumer — it never re-runs the agent. A deterministic backbone extracts the
citable evidence (:func:`observed_steps`) and enforces the anti-fabrication contract
(:func:`verify` — every cited number must appear in its observation); an injected
LLM-composer (:mod:`.compose`) fills the narrative, constrained by the schema and
checked by that backbone. The verify/evidence sub-layer is stdlib-only; the composer
uses the agent's ``LLM``.
"""

from statskills.reporting.compose import ReportComposeError, compose_report
from statskills.reporting.evidence import ObservedStep, observed_steps
from statskills.reporting.figures import FiguresUnavailable, generate_figures
from statskills.reporting.render import render_markdown
from statskills.reporting.schema import (
    Claim,
    Figure,
    Report,
    ReportSchemaError,
    parse_report,
)
from statskills.reporting.verify import unverified, verify

__all__ = [
    "Claim",
    "Figure",
    "FiguresUnavailable",
    "ObservedStep",
    "Report",
    "ReportComposeError",
    "ReportSchemaError",
    "compose_report",
    "generate_figures",
    "observed_steps",
    "parse_report",
    "render_markdown",
    "unverified",
    "verify",
]
