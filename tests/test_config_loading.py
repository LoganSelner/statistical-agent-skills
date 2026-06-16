"""Tests for YAML config loading with ``extends:`` inheritance."""

from __future__ import annotations

from pathlib import Path
import textwrap

import pytest

from statskills.core.config import ConfigValidationError, load_yaml_with_inheritance
from statskills.core.config.loading import _deep_merge


def _write(path: Path, text: str) -> None:
    path.write_text(textwrap.dedent(text))


def test_extends_deep_merges_nested_and_overrides_scalars(tmp_path: Path) -> None:
    _write(
        tmp_path / "base.yaml",
        """
        model:
          provider: edenai
          temperature: 0.0
          max_tokens: 1024
        trials: 5
        """,
    )
    _write(
        tmp_path / "child.yaml",
        """
        extends: base.yaml
        model:
          temperature: 0.7
        trials: 10
        """,
    )
    cfg = load_yaml_with_inheritance(tmp_path / "child.yaml")
    assert cfg["model"]["provider"] == "edenai"  # inherited
    assert cfg["model"]["temperature"] == 0.7  # overridden
    assert cfg["model"]["max_tokens"] == 1024  # inherited
    assert cfg["trials"] == 10  # overridden


def test_lists_replace_not_merge(tmp_path: Path) -> None:
    _write(tmp_path / "base.yaml", "skills: [a, b, c]\n")
    _write(tmp_path / "child.yaml", "extends: base.yaml\nskills: [x]\n")
    cfg = load_yaml_with_inheritance(tmp_path / "child.yaml")
    assert cfg["skills"] == ["x"]


def test_changed_impl_selector_replaces_whole_subtree(tmp_path: Path) -> None:
    # Switching ``provider`` discards the parent's provider-private params
    # rather than leaking them onto a different implementation.
    _write(
        tmp_path / "base.yaml",
        """
        model:
          provider: edenai
          sub_provider: openai
        """,
    )
    _write(
        tmp_path / "child.yaml",
        """
        extends: base.yaml
        model:
          provider: ollama
          base_url: http://localhost:11434
        """,
    )
    cfg = load_yaml_with_inheritance(tmp_path / "child.yaml")
    assert cfg["model"] == {
        "provider": "ollama",
        "base_url": "http://localhost:11434",
    }


def test_root_level_impl_selector_replaces_wholesale(tmp_path: Path) -> None:
    # A config whose *root* is itself a component: switching the root selector
    # must drop the parent implementation's private params, not inherit them.
    _write(
        tmp_path / "base.yaml",
        """
        provider: edenai
        sub_provider: openai
        """,
    )
    _write(
        tmp_path / "child.yaml",
        """
        extends: base.yaml
        provider: ollama
        base_url: http://localhost:11434
        """,
    )
    cfg = load_yaml_with_inheritance(tmp_path / "child.yaml")
    assert cfg == {"provider": "ollama", "base_url": "http://localhost:11434"}
    assert "sub_provider" not in cfg


def test_multilevel_inheritance(tmp_path: Path) -> None:
    _write(tmp_path / "a.yaml", "x: 1\ny: 1\nz: 1\n")
    _write(tmp_path / "b.yaml", "extends: a.yaml\ny: 2\n")
    _write(tmp_path / "c.yaml", "extends: b.yaml\nz: 3\n")
    cfg = load_yaml_with_inheritance(tmp_path / "c.yaml")
    assert cfg == {"x": 1, "y": 2, "z": 3}


def test_circular_inheritance_raises(tmp_path: Path) -> None:
    _write(tmp_path / "a.yaml", "extends: b.yaml\n")
    _write(tmp_path / "b.yaml", "extends: a.yaml\n")
    with pytest.raises(ConfigValidationError, match="Circular"):
        load_yaml_with_inheritance(tmp_path / "a.yaml")


def test_deep_merge_does_not_mutate_inputs() -> None:
    base = {"a": {"x": 1}}
    override = {"a": {"y": 2}}
    merged = _deep_merge(base, override)
    assert merged == {"a": {"x": 1, "y": 2}}
    assert base == {"a": {"x": 1}}  # base untouched
