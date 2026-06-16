"""Tests for the task-set loader dispatch + deterministic sampling."""

from __future__ import annotations

import pytest

from statskills.tasks.loader import _sample, load_tasks


def test_load_tasks_defaults_to_authored():
    assert len(load_tasks(None)) == 5


def test_load_tasks_authored_explicit():
    assert len(load_tasks({"set": "authored"})) == 5


def test_load_tasks_unknown_set_raises():
    with pytest.raises(ValueError, match="Unknown task set"):
        load_tasks({"set": "bogus"})


def test_sample_is_deterministic_and_limited():
    tasks = load_tasks({"set": "authored"})
    first = _sample(tasks, 3, seed=0)
    second = _sample(tasks, 3, seed=0)
    assert len(first) == 3
    assert [t.id for t in first] == [t.id for t in second]


def test_sample_limit_at_or_above_size_returns_all():
    tasks = load_tasks({"set": "authored"})
    assert _sample(tasks, 99, seed=0) == tasks
