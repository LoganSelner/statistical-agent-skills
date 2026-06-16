"""Deferred evaluation seams — interfaces only (ROADMAP §8, future work).

Not implemented in this phase; they exist so validity decomposition (method /
assumptions / interpretation / fabrication), trajectory error-mode classification, and
integrity-under-pressure probing become drop-ins rather than refactors later.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from statskills.evaluation.verifiers import Verdict
from statskills.tasks.schema import Task


@runtime_checkable
class ValidityScorer(Protocol):
    """Decompose validity into method / assumptions / interpretation / fabrication."""

    def score(self, trajectory: dict[str, Any], task: Task) -> dict[str, float]: ...


@runtime_checkable
class ErrorModeClassifier(Protocol):
    """Classify the dominant error mode of a (failed) trajectory."""

    def classify(self, trajectory: dict[str, Any], task: Task) -> str: ...


@runtime_checkable
class IntegrityProbe(Protocol):
    """Does a correct conclusion survive leading pressure?"""

    def probe(self, trajectory: dict[str, Any], task: Task) -> Verdict: ...
