"""Skill routers — select skills for a task. Import registers the built-ins."""

from __future__ import annotations

from statskills.core.registry import registry
from statskills.skills.router import (
    forced as _forced,  # noqa: F401 - registers "forced"
)
from statskills.skills.schema import SkillRouter


def get_router(name: str) -> SkillRouter:
    """Resolve a registered router by name (config ``skills.router``)."""
    router: SkillRouter = registry.get("router", name)()
    return router


__all__ = ["SkillRouter", "get_router"]
