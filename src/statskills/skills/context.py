"""Skill context — turn a config block into a per-task skill payload (ROADMAP §5).

The runner builds a :class:`SkillContext` (library + router + disclosure level) from the
config ``skills`` block and asks it to :meth:`resolve` each task; the agent receives
only the rendered string, staying unaware of skills (the harness/experiment seam, §2).
``mode: off`` (or no ``skills`` block) yields no context — the no-skills baseline,
byte-for-byte unchanged.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from statskills.skills.library import SkillLibrary, load_library
from statskills.skills.loader import render, render_discovery, render_library
from statskills.skills.router import get_router
from statskills.skills.schema import SkillResolution, SkillRouter
from statskills.tasks.schema import Task

_LIBRARY_ROOT = Path(__file__).resolve().parent / "library"

_DELIVERIES = ("injected", "agentic")


@dataclass(frozen=True)
class SkillSelection:
    """What one task got, plus how the skills reach the agent (provenance).

    ``injected`` delivery fills ``payload`` (skill bodies for the system prompt).
    ``agentic`` delivery fills ``discovery`` (the L0 names+descriptions surface) and
    ``files`` (``filename -> body``, staged in the sandbox for the agent to read on
    demand), leaving ``payload`` empty. ``names`` is the selected set either way.
    """

    payload: str | None
    names: tuple[str, ...]
    discovery: str | None = None
    files: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class SkillContext:
    """A resolved skills condition (library + router + disclosure level + delivery)."""

    library: SkillLibrary
    router: SkillRouter
    level: SkillResolution
    delivery: str = "injected"

    def resolve(self, task: Task) -> SkillSelection:
        """Select skills for ``task`` and render them for this delivery + level."""
        skills = self.router.select(task, self.library)
        names = tuple(s.name for s in skills)
        if not skills:
            return SkillSelection(payload=None, names=())
        if self.delivery == "agentic":
            return SkillSelection(
                payload=None,
                names=names,
                discovery=render_discovery(skills),
                files={f"{s.name}.md": render(s, self.level) for s in skills},
            )
        return SkillSelection(payload=render_library(skills, self.level), names=names)


def build_skill_context(cfg: Mapping[str, Any] | None) -> SkillContext | None:
    """Build the skills condition from a config ``skills`` block; ``off`` → ``None``."""
    cfg = dict(cfg or {})
    mode = str(cfg.get("mode", "off")).lower()
    if mode in ("off", "none", ""):
        return None
    if mode != "curated":
        raise ValueError(f"Unknown skills mode {mode!r}. Known: off, curated.")
    delivery = str(cfg.get("delivery", "injected")).lower()
    if delivery not in _DELIVERIES:
        raise ValueError(
            f"Unknown skills delivery {delivery!r}. Known: {', '.join(_DELIVERIES)}."
        )
    library = load_library(_resolve_library(str(cfg.get("library", "statistics"))))
    router = get_router(str(cfg.get("router", "forced")))
    level = SkillResolution.parse(cfg.get("resolution", "L1"))
    return SkillContext(library=library, router=router, level=level, delivery=delivery)


def _resolve_library(value: str) -> Path:
    """Resolve the ``library`` config value to a directory.

    A bare name (no path separator) is a bundled library under ``library/``, resolved
    independently of the process CWD so the same config always loads the same skills
    (reproducibility, §9) — never a same-named directory that happens to sit in the CWD.
    A value with a separator (or an absolute path) is used as a filesystem path; a
    relative path is relative to the CWD.
    """
    if "/" in value or Path(value).is_absolute():
        return Path(value)
    return _LIBRARY_ROOT / value
