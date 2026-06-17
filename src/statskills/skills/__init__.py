"""Curated agent skills (ROADMAP §5).

Parse Anthropic Agent-Skills ``SKILL.md`` folders, control progressive disclosure
(L0-L3 via :mod:`.loader`) and route skills to tasks. The runner builds a
:class:`SkillContext` from the config ``skills`` block and feeds each task's rendered
payload to the agent; the agent itself stays unaware of skills. Importing this package
registers the built-in routers.
"""

from statskills.skills.context import (
    SkillContext,
    SkillSelection,
    build_skill_context,
)
from statskills.skills.schema import Skill, SkillResolution

__all__ = [
    "Skill",
    "SkillContext",
    "SkillResolution",
    "SkillSelection",
    "build_skill_context",
]
