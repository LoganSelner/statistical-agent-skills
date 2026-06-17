"""Skill data model (ROADMAP §5).

A skill is an Anthropic Agent-Skills folder: ``SKILL.md`` (YAML frontmatter + markdown
body) plus optional bundled ``scripts/``/``references/``/``assets/``. These are the
parsed, in-memory types. The progressive-disclosure loader (:mod:`.loader`) controls
how much of a skill enters context at each level (L0-L3, the ablation axis), and a
:class:`SkillRouter` selects which skills a task receives. Domain code depends on these
types; they depend on nothing else in the harness.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from statskills.skills.library import SkillLibrary
    from statskills.tasks.schema import Task


class SkillResolution(IntEnum):
    """Progressive-disclosure level: how much of a skill enters context (§5)."""

    L0 = 0  # name + description (discovery surface)
    L1 = 1  # + SKILL.md body (instructions)
    L2 = 2  # + inline executable examples
    L3 = 3  # + bundled scripts / reference resources

    @classmethod
    def parse(cls, value: object) -> SkillResolution:
        """Resolve a config value (``"L1"``, ``"l1"``, ``1``) to a level."""
        if isinstance(value, SkillResolution):
            return value
        if isinstance(value, bool):  # avoid bool-is-int surprises
            raise ValueError(f"Invalid skill resolution: {value!r}")
        if isinstance(value, int):
            return cls(value)
        text = str(value).strip().upper().removeprefix("L")
        try:
            return cls(int(text))
        except ValueError:
            raise ValueError(f"Invalid skill resolution: {value!r}") from None


@dataclass(frozen=True)
class SkillResource:
    """A bundled file a skill ships (L3)."""

    relative_path: str
    kind: str  # "script" | "reference"


@dataclass(frozen=True)
class Skill:
    """A parsed skill (ROADMAP §5); each field maps to a disclosure level."""

    name: str  # frontmatter — the L0 discovery surface
    description: str  # frontmatter — the L0 discovery surface
    body: str  # L1 — instructions (SKILL.md body, minus the Examples section)
    examples: tuple[str, ...] = ()  # L2 — code blocks from the ``## Examples`` section
    resources: tuple[SkillResource, ...] = ()  # L3 — bundled scripts/references
    path: Path = field(default_factory=Path)


@runtime_checkable
class SkillRouter(Protocol):
    """Selects the skills a task receives (forced / description_match / ...)."""

    def select(self, task: Task, library: SkillLibrary) -> list[Skill]: ...
