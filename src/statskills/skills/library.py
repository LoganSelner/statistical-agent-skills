"""A collection of parsed skills loaded from a directory (ROADMAP §5)."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from pathlib import Path

from statskills.skills.parser import SkillError, parse_skill
from statskills.skills.schema import Skill


class SkillLibrary:
    """An ordered (by name), name-indexed set of skills."""

    def __init__(self, skills: Sequence[Skill]) -> None:
        self._skills = tuple(sorted(skills, key=lambda s: s.name))
        names = [s.name for s in self._skills]
        duplicates = sorted({n for n in names if names.count(n) > 1})
        if duplicates:
            raise SkillError(f"Duplicate skill names in library: {duplicates}")
        self._by_name = {s.name: s for s in self._skills}

    def __iter__(self) -> Iterator[Skill]:
        return iter(self._skills)

    def __len__(self) -> int:
        return len(self._skills)

    def __contains__(self, name: object) -> bool:
        return name in self._by_name

    def get(self, name: str) -> Skill:
        try:
            return self._by_name[name]
        except KeyError:
            raise SkillError(f"No skill {name!r}; have {list(self._by_name)}") from None

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(self._by_name)


def load_library(directory: Path) -> SkillLibrary:
    """Parse every ``<skill>/SKILL.md`` under ``directory`` into a library."""
    if not directory.is_dir():
        raise SkillError(f"Skill library directory not found: {directory}")
    skills = [parse_skill(md.parent) for md in sorted(directory.glob("*/SKILL.md"))]
    return SkillLibrary(skills)
