"""Tests for run-artifact I/O: grade_run / load_scores over a run directory."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from statskills.evaluation import runs
from statskills.tasks.schema import ExpectedAnswer, Task


def _write_run(
    run_dir: Path,
    trajectories: list[dict[str, Any]],
    *,
    task_set: dict[str, Any] | None,
) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / runs.TRAJECTORIES).write_text(
        "".join(json.dumps(t) + "\n" for t in trajectories)
    )
    if task_set is not None:
        (run_dir / runs.RUN_META).write_text(json.dumps({"task_set": task_set}))


def test_grade_run_reconstructs_tasks_writes_and_returns_scores(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    task = Task(
        id="t",
        prompt="p",
        expected=ExpectedAnswer.single(1.0, "numeric", tolerance=0.5),
    )
    captured: dict[str, Any] = {}

    def fake_load_tasks(spec: Any) -> list[Task]:
        captured["spec"] = spec
        return [task]

    monkeypatch.setattr(runs, "load_tasks", fake_load_tasks)

    run_dir = tmp_path / "run-x"
    _write_run(
        run_dir,
        [
            {"task_id": "t", "final_answer": "1", "steps": [{}], "trial": 0},
            {"task_id": "t", "final_answer": "9", "steps": [{}], "trial": 1},
        ],
        task_set={"set": "demo"},
    )

    records = runs.grade_run(run_dir)

    # The task set is reconstructed from run.json (so answer keys match the run).
    assert captured["spec"] == {"set": "demo"}
    assert [(r.task_id, r.passed, r.trial) for r in records] == [
        ("t", True, 0),
        ("t", False, 1),
    ]
    # scores.jsonl is written and round-trips byte-for-value through load_scores.
    assert runs.is_graded(run_dir)
    assert runs.load_scores(run_dir) == records


def test_grade_run_missing_trajectories_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="trajectories"):
        runs.grade_run(tmp_path / "empty")


def test_load_scores_missing_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match=r"scores\.jsonl"):
        runs.load_scores(tmp_path)
