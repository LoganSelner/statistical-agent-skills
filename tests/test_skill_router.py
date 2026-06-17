"""Tests for skill routers (forced)."""

from __future__ import annotations

from pathlib import Path

from statskills.core.registry import registry
from statskills.skills.library import load_library
from statskills.skills.router import get_router
from statskills.tasks.schema import Task

FIXTURES = Path(__file__).parent / "fixtures" / "skills"


def test_forced_router_is_registered():
    assert registry.is_registered("router", "forced")


def test_forced_router_selects_whole_library():
    selected = get_router("forced").select(
        Task(id="t", prompt="p"), load_library(FIXTURES)
    )
    assert {s.name for s in selected} == {"another-skill", "sample-skill"}
