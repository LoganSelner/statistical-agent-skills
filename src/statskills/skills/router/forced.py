"""Forced router — inject the whole library, deterministically (ROADMAP §3 router).

The oracle "all curated skills are available" condition: it ignores the task and returns
every skill. ``description_match`` / ``model_choice`` routers are later drop-ins.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from statskills.core.registry import registry
from statskills.skills.schema import Skill

if TYPE_CHECKING:
    from statskills.skills.library import SkillLibrary
    from statskills.tasks.schema import Task


@registry.register("router", "forced")
class ForcedRouter:
    """Selects every skill in the library."""

    def select(self, task: Task, library: SkillLibrary) -> list[Skill]:
        return list(library)
