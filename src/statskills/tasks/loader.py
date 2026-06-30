"""Task-set loading — dispatch a config ``tasks`` spec to a concrete task list.

A run/grade selects its task set by a small spec: ``{"set": "authored"}`` or
``{"set": "dabench", "limit": 20, "seed": 0}``. Recording the spec in run.json lets the
grader reconstruct exactly the same tasks without re-running the agent (ROADMAP §3).
"""

from __future__ import annotations

from collections.abc import Mapping
import random
from typing import Any

from statskills.tasks.adapters.dabench import load_dabench_tasks
from statskills.tasks.authored.regression_trap_tasks import load_regression_trap_tasks
from statskills.tasks.authored.slice_tasks import load_slice_tasks
from statskills.tasks.authored.trap_tasks import load_trap_tasks
from statskills.tasks.schema import Task


def load_tasks(spec: Mapping[str, Any] | None) -> list[Task]:
    """Load the task set named by ``spec`` (default: the authored slice)."""
    spec = spec or {}
    name = str(spec.get("set", "authored"))
    if name == "authored":
        return load_slice_tasks()
    if name == "authored_trap":
        return load_trap_tasks()
    if name == "authored_regression":
        return load_regression_trap_tasks()
    if name == "dabench":
        tasks = load_dabench_tasks()
        limit = spec.get("limit")
        if limit is not None:
            tasks = _sample(tasks, int(limit), int(spec.get("seed", 0)))
        return tasks
    raise ValueError(
        f"Unknown task set {name!r}. "
        "Known: authored, authored_trap, authored_regression, dabench."
    )


def _sample(tasks: list[Task], limit: int, seed: int) -> list[Task]:
    """A deterministic, seeded subset — reproducible so grading rebuilds it exactly."""
    if limit >= len(tasks):
        return tasks
    return random.Random(seed).sample(tasks, limit)
