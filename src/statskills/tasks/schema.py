"""Task schema — the minimal, forward-compatible shape for Phase 1.

A seed of the full model in ROADMAP §4 (task arms, ``ExpectedAnswer``, verifier
keys, ...): the vertical slice only needs an id, a prompt, and the datasets to
mount. ``expected`` is carried for eyeballing now; deterministic scoring against
it arrives in Phase 2.
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
class Task:
    """A single data-analysis task."""

    id: str
    prompt: str
    datasets: tuple[Dataset, ...] = ()
    expected: str | None = None  # informational in Phase 1 (no scoring yet)
    concepts: tuple[str, ...] = ()
    source: str = "authored"

    @property
    def dataset_paths(self) -> tuple[Path, ...]:
        return tuple(d.path for d in self.datasets)
