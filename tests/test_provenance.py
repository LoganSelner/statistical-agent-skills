"""Tests for best-effort run provenance capture."""

from __future__ import annotations

import platform

from statskills.core.provenance import RunProvenance, get_git_dirty, get_git_sha


def test_get_git_sha_returns_nonempty_str():
    sha = get_git_sha()
    assert isinstance(sha, str)
    assert sha  # a real short SHA, or the "unknown" fallback — never empty


def test_get_git_dirty_returns_bool():
    assert isinstance(get_git_dirty(), bool)


def test_capture_populates_all_fields():
    prov = RunProvenance.capture()
    assert prov.python_version == platform.python_version()
    assert isinstance(prov.git_dirty, bool)
    assert prov.git_sha
    assert "T" in prov.timestamp  # ISO-8601 timestamp


def test_run_provenance_is_frozen():
    prov = RunProvenance.capture()
    try:
        prov.git_sha = "tampered"  # type: ignore[misc]
    except Exception as exc:  # frozen dataclass raises FrozenInstanceError
        assert "cannot assign" in str(exc).lower() or "frozen" in str(exc).lower()
    else:
        raise AssertionError("RunProvenance should be immutable (frozen)")
