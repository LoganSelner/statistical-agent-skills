"""Tests for the SKILL.md parser (frontmatter, examples, resources, validation)."""

from __future__ import annotations

from pathlib import Path

import pytest

from statskills.skills.parser import SkillError, parse_skill

FIXTURES = Path(__file__).parent / "fixtures" / "skills"


def test_parses_frontmatter_body_examples_resources():
    skill = parse_skill(FIXTURES / "sample-skill")
    assert skill.name == "sample-skill"
    assert skill.description.startswith("A sample skill")
    assert "check assumptions" in skill.body
    assert "## Examples" not in skill.body  # the Examples section is lifted out
    assert len(skill.examples) == 1
    assert "mannwhitneyu" in skill.examples[0]
    assert [(r.relative_path, r.kind) for r in skill.resources] == [
        ("scripts/helper.py", "script")
    ]
    assert skill.path == FIXTURES / "sample-skill"


def test_parses_minimal_skill_without_examples_or_resources():
    skill = parse_skill(FIXTURES / "another-skill")
    assert skill.examples == ()
    assert skill.resources == ()
    assert "confidence interval" in skill.body


def _write(tmp_path: Path, text: str) -> Path:
    (tmp_path / "SKILL.md").write_text(text)
    return tmp_path


def test_missing_frontmatter_raises(tmp_path: Path):
    with pytest.raises(SkillError, match="frontmatter"):
        parse_skill(_write(tmp_path, "no frontmatter here"))


def test_invalid_name_raises(tmp_path: Path):
    with pytest.raises(SkillError, match="name"):
        parse_skill(_write(tmp_path, "---\nname: Bad_Name\ndescription: ok\n---\nbody"))


def test_missing_description_raises(tmp_path: Path):
    with pytest.raises(SkillError, match="description"):
        parse_skill(_write(tmp_path, "---\nname: good-name\n---\nbody"))


def test_oversized_description_raises(tmp_path: Path):
    text = f"---\nname: good-name\ndescription: {'x' * 1025}\n---\nbody"
    with pytest.raises(SkillError, match="1024"):
        parse_skill(_write(tmp_path, text))


def test_missing_skill_md_raises(tmp_path: Path):
    with pytest.raises(SkillError, match="No SKILL"):
        parse_skill(tmp_path)  # empty dir
