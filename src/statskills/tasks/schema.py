"""Task schema — the data contracts for a data-analysis task and its answer.

Aligns with ROADMAP §4: a task carries the prompt, the datasets to mount, an
``ExpectedAnswer`` (the closed-form ground truth), and a ``verifier`` key naming the
scorer. Scoring itself lives in :mod:`statskills.evaluation`, which depends on these
types (never the reverse).
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path


@dataclass(frozen=True)
class Dataset:
    """A data file made available to the agent in its working directory."""

    path: Path

    @property
    def name(self) -> str:
        return self.path.name

    def sha256(self) -> str:
        """Content hash of the file, for provenance (ROADMAP §9)."""
        return hashlib.sha256(self.path.read_bytes()).hexdigest()


@dataclass(frozen=True)
class ExpectedAnswer:
    """The closed-form ground truth for a task (ROADMAP §4).

    ``kind`` selects how the verifier compares a submission to ``value``:
    ``"numeric"`` (parse a number, compare within ``tolerance``), ``"exact"`` /
    ``"categorical"`` (string match; ``categorical`` is case-insensitive), ``"set"``
    (compare as an unordered set), or ``"regex"`` (``value`` is a pattern the answer
    must match). ``format_spec`` records any required output format from the task.
    """

    value: object
    kind: str
    tolerance: float | None = None
    format_spec: str | None = None


@dataclass(frozen=True)
class Task:
    """A single data-analysis task."""

    id: str
    prompt: str
    datasets: tuple[Dataset, ...] = ()
    expected: ExpectedAnswer | None = None
    verifier: str = "closed_form"  # evaluation registry key
    concepts: tuple[str, ...] = ()
    source: str = "authored"

    @property
    def dataset_paths(self) -> tuple[Path, ...]:
        return tuple(d.path for d in self.datasets)
