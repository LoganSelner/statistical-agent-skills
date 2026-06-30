"""Deterministic scoring + skill-engagement measurement (ROADMAP §8, §9).

A task's ``ExpectedAnswer`` is scored by a registered ``Verifier`` into a ``Verdict``;
:func:`grading.grade` applies verifiers across a run's saved trajectories — separately
from running, so re-grading never re-runs the agent (ROADMAP §3). Skill *engagement*
(which skills the agent read, and the read/pass contingency) is recovered the same way
by :mod:`.engagement` — also a pure trajectory consumer. Validity decomposition,
error-mode classification, and integrity probing are seamed (interfaces only) in
:mod:`._deferred`.

Importing anything from ``verifiers`` registers the built-in verifiers.
"""

from statskills.evaluation.engagement import (
    EngagementRecord,
    EngagementSummary,
    ReadPass,
)
from statskills.evaluation.results import ScoreRecord
from statskills.evaluation.verifiers import Verdict, Verifier

__all__ = [
    "EngagementRecord",
    "EngagementSummary",
    "ReadPass",
    "ScoreRecord",
    "Verdict",
    "Verifier",
]
