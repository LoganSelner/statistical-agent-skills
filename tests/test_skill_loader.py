"""Tests for progressive-disclosure rendering (L0-L3)."""

from __future__ import annotations

from pathlib import Path

from statskills.skills.loader import render, render_library
from statskills.skills.parser import parse_skill
from statskills.skills.schema import SkillResolution

FIXTURES = Path(__file__).parent / "fixtures" / "skills"


def _sample():
    return parse_skill(FIXTURES / "sample-skill")


def test_l0_is_name_and_description_only():
    out = render(_sample(), SkillResolution.L0)
    assert "sample-skill" in out and "A sample skill" in out
    assert "check assumptions" not in out  # body excluded
    assert "mannwhitneyu" not in out  # examples excluded


def test_l1_adds_body_not_examples():
    out = render(_sample(), SkillResolution.L1)
    assert "check assumptions" in out
    assert "mannwhitneyu" not in out


def test_l2_adds_examples():
    assert "mannwhitneyu" in render(_sample(), SkillResolution.L2)


def test_l3_inlines_resource_contents():
    out = render(_sample(), SkillResolution.L3)
    assert "scripts/helper.py" in out
    assert "def cohens_d" in out  # the bundled file content is inlined


def test_levels_are_cumulative_and_distinct():
    sizes = [len(render(_sample(), level)) for level in SkillResolution]
    assert sizes == sorted(sizes)
    assert len(set(sizes)) == 4  # each level adds content for this skill


def test_render_library_is_sorted_by_name():
    library = [
        parse_skill(FIXTURES / "sample-skill"),
        parse_skill(FIXTURES / "another-skill"),
    ]
    out = render_library(library, SkillResolution.L0)
    assert out.index("another-skill") < out.index("sample-skill")
