"""Tests for the skill-context facade (config → per-task payload)."""

from __future__ import annotations

from pathlib import Path

import pytest

from statskills.skills import build_skill_context
from statskills.skills.schema import SkillResolution
from statskills.tasks.schema import Task

FIXTURES = Path(__file__).parent / "fixtures" / "skills"


def test_off_or_missing_yields_no_context():
    assert build_skill_context(None) is None
    assert build_skill_context({"mode": "off"}) is None
    assert build_skill_context({}) is None


def test_curated_builds_context_and_payload():
    ctx = build_skill_context(
        {
            "mode": "curated",
            "library": str(FIXTURES),
            "resolution": "L1",
            "router": "forced",
        }
    )
    assert ctx is not None
    assert ctx.level is SkillResolution.L1
    assert ctx.library.names == ("another-skill", "sample-skill")

    selection = ctx.resolve(Task(id="t", prompt="p"))
    assert selection.names == ("another-skill", "sample-skill")
    assert selection.payload is not None
    assert "sample-skill" in selection.payload


def test_unknown_mode_raises():
    with pytest.raises(ValueError, match="Unknown skills mode"):
        build_skill_context({"mode": "bogus"})


def test_resolution_parse_accepts_variants():
    assert SkillResolution.parse("L2") is SkillResolution.L2
    assert SkillResolution.parse("l3") is SkillResolution.L3
    assert SkillResolution.parse(1) is SkillResolution.L1
    with pytest.raises(ValueError):
        SkillResolution.parse("nope")
