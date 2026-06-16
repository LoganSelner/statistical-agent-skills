"""Deterministic, closed-form scoring (ROADMAP §8).

A task's ``ExpectedAnswer`` is scored by a registered ``Verifier`` into a ``Verdict``;
:func:`grading.grade` applies verifiers across a run's saved trajectories — separately
from running, so re-grading never re-runs the agent (ROADMAP §3). Validity
decomposition, error-mode classification, and integrity probing are seamed
(interfaces only) in :mod:`._deferred`.

Importing anything from ``verifiers`` registers the built-in verifiers.
"""

from statskills.evaluation.results import ScoreRecord
from statskills.evaluation.verifiers import Verdict, Verifier

__all__ = ["ScoreRecord", "Verdict", "Verifier"]
