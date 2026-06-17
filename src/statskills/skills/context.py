"""Skill context — turn a config block into a per-task skill payload (ROADMAP §5).

The runner builds a :class:`SkillContext` (library + router + disclosure level) from the
config ``skills`` block and asks it to :meth:`resolve` each task; the agent receives
only the rendered string, staying unaware of skills (the harness/experiment seam, §2).
``mode: off`` (or no ``skills`` block) yields no context — the no-skills baseline,
byte-for-byte unchanged.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from statskills.skills.library import SkillLibrary, load_library
from statskills.skills.loader import render_library
from statskills.skills.router import get_router
from statskills.skills.schema import SkillResolution, SkillRouter
from statskills.tasks.schema import Task

_LIBRARY_ROOT = Path(__file__).resolve().parent / "library"


@dataclass(frozen=True)
class SkillSelection:
    """What one task got: the rendered payload + selected skill names (provenance)."""

    payload: str | None
    names: tuple[str, ...]


@dataclass(frozen=True)
class SkillContext:
    """A resolved skills condition (library + router + disclosure level)."""

    library: SkillLibrary
    router: SkillRouter
    level: SkillResolution

    def resolve(self, task: Task) -> SkillSelection:
        """Select skills for ``task`` and render the context payload at this level."""
        skills = self.router.select(task, self.library)
        names = tuple(s.name for s in skills)
        payload = render_library(skills, self.level) if skills else None
        return SkillSelection(payload=payload, names=names)


def build_skill_context(cfg: Mapping[str, Any] | None) -> SkillContext | None:
    """Build the skills condition from a config ``skills`` block; ``off`` → ``None``."""
    cfg = dict(cfg or {})
    mode = str(cfg.get("mode", "off")).lower()
    if mode in ("off", "none", ""):
        return None
    if mode != "curated":
        raise ValueError(f"Unknown skills mode {mode!r}. Known: off, curated.")
    library = load_library(_resolve_library(str(cfg.get("library", "statistics"))))
    router = get_router(str(cfg.get("router", "forced")))
    level = SkillResolution.parse(cfg.get("resolution", "L1"))
    return SkillContext(library=library, router=router, level=level)


def _resolve_library(value: str) -> Path:
    """A bare name resolves under the bundled ``library/`` dir; a path is used as-is."""
    path = Path(value)
    return path if path.is_absolute() or path.exists() else _LIBRARY_ROOT / value
