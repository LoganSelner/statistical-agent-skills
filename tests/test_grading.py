"""Tests for grading saved trajectories against tasks."""

from __future__ import annotations

from typing import Any

from statskills.evaluation.grading import grade, grade_trajectory
from statskills.tasks.schema import ExpectedAnswer, Task


def _task(task_id: str, expected: ExpectedAnswer) -> Task:
    return Task(id=task_id, prompt="p", expected=expected)


def test_grade_trajectory_scores_and_carries_efficiency():
    task = _task("m", ExpectedAnswer.single(16.0, "numeric", tolerance=5e-3))
    traj = {
        "task_id": "m",
        "final_answer": "16.00",
        "stop_reason": "final",
        "steps": [{}, {}],
        "prompt_tokens": 30,
        "completion_tokens": 8,
    }
    r = grade_trajectory(traj, task)
    assert r.passed and r.score == 1.0
    assert r.task_id == "m"
    assert r.num_steps == 2 and r.prompt_tokens == 30 and r.completion_tokens == 8


def test_grade_skips_unknown_task_and_fails_errors():
    tasks = {"a": _task("a", ExpectedAnswer.single(1.0, "numeric", tolerance=0.5))}
    trajectories: list[dict[str, Any]] = [
        {"task_id": "a", "final_answer": "1", "steps": [], "stop_reason": "final"},
        {"task_id": "unknown", "final_answer": "x"},  # no task → skipped
        {"task_id": "a", "error": "boom"},  # run error → failure
    ]
    records = grade(trajectories, tasks)
    assert [(r.task_id, r.passed) for r in records] == [("a", True), ("a", False)]
    assert records[1].detail.startswith("run error")
