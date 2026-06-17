"""Task schema — the data contracts for a data-analysis task and its answer.

Aligns with ROADMAP §4: a task carries the prompt, the datasets to mount, an
``ExpectedAnswer`` (the closed-form ground truth — one or more named keys), and a
``verifier`` key naming the scorer. Scoring lives in :mod:`statskills.evaluation`, which
depends on these types (never the reverse).
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
class AnswerKey:
    """One expected sub-answer.

    ``kind`` selects the comparison: ``numeric`` (within ``tolerance``), ``exact`` or
    ``categorical`` string (the latter case-insensitive), ``set``, or ``regex``.

    ``name`` is empty for a single answer (the whole submission is compared), or the
    ``@name`` label of a benchmark's ``@name[value]`` multi-part answer.
    """

    value: object
    kind: str
    tolerance: float | None = None
    name: str = ""


@dataclass(frozen=True)
class ExpectedAnswer:
    """The closed-form ground truth: one or more ``AnswerKey`` parts (ROADMAP §4)."""

    keys: tuple[AnswerKey, ...]
    format_spec: str | None = None

    @classmethod
    def single(
        cls,
        value: object,
        kind: str,
        *,
        tolerance: float | None = None,
        format_spec: str | None = None,
    ) -> ExpectedAnswer:
        """A one-part expected answer (the whole submission is compared)."""
        return cls((AnswerKey(value, kind, tolerance),), format_spec=format_spec)


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
