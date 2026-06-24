"""Tests for the skill-context facade (config → per-task payload)."""

from __future__ import annotations

from pathlib import Path

import pytest

from statskills.skills import build_skill_context
from statskills.skills.context import _LIBRARY_ROOT, _resolve_library
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


def test_delivery_defaults_to_injected():
    ctx = build_skill_context(
        {"mode": "curated", "library": str(FIXTURES), "router": "forced"}
    )
    assert ctx is not None and ctx.delivery == "injected"
    selection = ctx.resolve(Task(id="t", prompt="p"))
    assert selection.payload is not None
    assert selection.discovery is None and selection.files == {}


def test_agentic_delivery_yields_discovery_and_files_not_payload():
    ctx = build_skill_context(
        {
            "mode": "curated",
            "library": str(FIXTURES),
            "resolution": "L1",
            "router": "forced",
            "delivery": "agentic",
        }
    )
    assert ctx is not None and ctx.delivery == "agentic"

    selection = ctx.resolve(Task(id="t", prompt="p"))
    assert selection.payload is None  # nothing force-injected
    assert selection.discovery is not None
    assert "- sample-skill:" in selection.discovery  # L0 names + descriptions
    # One readable file per selected skill, named <skill>.md, holding its body.
    assert set(selection.files) == {"another-skill.md", "sample-skill.md"}
    assert "sample-skill" in selection.files["sample-skill.md"]


def test_unknown_delivery_raises():
    with pytest.raises(ValueError, match="Unknown skills delivery"):
        build_skill_context(
            {"mode": "curated", "library": str(FIXTURES), "delivery": "bogus"}
        )


def test_bare_library_name_resolves_to_bundled_ignoring_cwd(tmp_path, monkeypatch):
    # A bare name must be the bundled library even if a same-named dir sits in the CWD,
    # so the same config always loads the same skills (reproducibility).
    (tmp_path / "statistics").mkdir()
    monkeypatch.chdir(tmp_path)
    assert _resolve_library("statistics") == _LIBRARY_ROOT / "statistics"


def test_explicit_path_library_is_used_as_given():
    assert _resolve_library(str(FIXTURES)) == FIXTURES  # absolute path
    assert _resolve_library("a/b/skills") == Path("a/b/skills")  # has a separator


def test_resolution_parse_accepts_variants():
    assert SkillResolution.parse("L2") is SkillResolution.L2
    assert SkillResolution.parse("l3") is SkillResolution.L3
    assert SkillResolution.parse(1) is SkillResolution.L1
    with pytest.raises(ValueError):
        SkillResolution.parse("nope")
