"""Grade saved trajectories against a task set — no agent re-run (ROADMAP §3)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from statskills.evaluation.results import ScoreRecord
from statskills.evaluation.verifiers import get_verifier
from statskills.tasks.schema import Task


def grade_trajectory(trajectory: Mapping[str, Any], task: Task) -> ScoreRecord:
    """Score one trajectory dict (as written to trajectories.jsonl) against its task."""
    submitted = trajectory.get("final_answer")
    verdict = get_verifier(task.verifier).score(submitted or "", task)
    return ScoreRecord(
        task_id=task.id,
        passed=verdict.passed,
        score=verdict.score,
        submitted=submitted,
        detail=verdict.detail,
        stop_reason=str(trajectory.get("stop_reason", "")),
        num_steps=len(trajectory.get("steps", [])),
        prompt_tokens=int(trajectory.get("prompt_tokens", 0)),
        completion_tokens=int(trajectory.get("completion_tokens", 0)),
    )


def grade(
    trajectories: Sequence[Mapping[str, Any]],
    tasks_by_id: Mapping[str, Task],
) -> list[ScoreRecord]:
    """Grade each trajectory against its task.

    A trajectory whose task is unknown is skipped (nothing to grade against); one the
    run recorded as an error counts as a failure (the agent produced no answer).
    """
    records: list[ScoreRecord] = []
    for traj in trajectories:
        task = tasks_by_id.get(str(traj.get("task_id", "")))
        if task is None:
            continue
        if "error" in traj:
            records.append(
                ScoreRecord(
                    task_id=task.id,
                    passed=False,
                    score=0.0,
                    submitted=None,
                    detail=f"run error: {traj['error']}",
                    stop_reason="error",
                    num_steps=0,
                    prompt_tokens=0,
                    completion_tokens=0,
                )
            )
            continue
        records.append(grade_trajectory(traj, task))
    return records
