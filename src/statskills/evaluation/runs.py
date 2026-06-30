"""Run-artifact I/O — read, grade, and load a results run directory (ROADMAP §3, §8).

A run directory written by ``scripts/run.py`` holds ``trajectories.jsonl`` (the
agent's saved runs), ``run.json`` (provenance, including the task set), and — after
grading — ``scores.jsonl``. This module centralises that on-disk contract so the grading
CLI, the comparison CLI, and the experiment matrix all read it the same way. Grading is
kept separate from running: it never re-runs the agent (§3).

Importing :func:`grade` from :mod:`.grading` registers the built-in verifiers (via that
module's ``verifiers`` import), so callers need no extra registration step.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict
import json
from pathlib import Path
from typing import Any

from statskills.evaluation.engagement import EngagementRecord, extract_engagement
from statskills.evaluation.grading import grade
from statskills.evaluation.results import ScoreRecord
from statskills.tasks.loader import load_tasks

TRAJECTORIES = "trajectories.jsonl"
RUN_META = "run.json"
SCORES = "scores.jsonl"
ENGAGEMENT = "engagement.jsonl"


def _read_trajectories(run_dir: Path) -> list[dict[str, object]]:
    """Read a run directory's saved trajectories, or raise if it has none."""
    traj_path = run_dir / TRAJECTORIES
    if not traj_path.exists():
        raise FileNotFoundError(f"No {TRAJECTORIES} in {run_dir}")
    return [
        json.loads(line) for line in traj_path.read_text().splitlines() if line.strip()
    ]


def grade_run(run_dir: Path) -> list[ScoreRecord]:
    """Grade a run directory and write ``scores.jsonl``; return the score records.

    Reads ``trajectories.jsonl`` and reconstructs the task set from ``run.json`` (so the
    answer keys match the run that produced the trajectories), scores each trajectory
    against its task, and writes ``scores.jsonl``. Raises ``FileNotFoundError`` if the
    run has no trajectories to grade.
    """
    trajectories = _read_trajectories(run_dir)
    meta_path = run_dir / RUN_META
    task_set = (
        json.loads(meta_path.read_text()).get("task_set")
        if meta_path.exists()
        else None
    )
    tasks_by_id = {t.id: t for t in load_tasks(task_set)}
    records = grade(trajectories, tasks_by_id)
    write_scores(run_dir, records)
    return records


def write_scores(run_dir: Path, records: list[ScoreRecord]) -> None:
    """Write ``scores.jsonl`` for a run directory."""
    lines = "".join(json.dumps(asdict(r)) + "\n" for r in records)
    (run_dir / SCORES).write_text(lines)


def load_scores(run_dir: Path) -> list[ScoreRecord]:
    """Read ``scores.jsonl`` for a graded run directory."""
    path = run_dir / SCORES
    if not path.exists():
        raise FileNotFoundError(f"No {SCORES} in {run_dir} — grade the run first.")
    return [
        ScoreRecord(**json.loads(line))
        for line in path.read_text().splitlines()
        if line.strip()
    ]


def is_graded(run_dir: Path) -> bool:
    """True if the run directory already holds ``scores.jsonl`` (for resume/caching)."""
    return (run_dir / SCORES).exists()


def extract_run_engagement(run_dir: Path) -> list[EngagementRecord]:
    """Extract a run's skill-engagement records; write ``engagement.jsonl``.

    A pure trajectory consumer (no agent re-run, no task answer keys): scans the saved
    trajectories for skill-file reads and writes the per-(task, trial) records.
    Idempotent — safe to call again to refresh it. Raises ``FileNotFoundError`` when the
    run has no trajectories.
    """
    records = extract_engagement(_read_trajectories(run_dir))
    write_engagement(run_dir, records)
    return records


def write_engagement(run_dir: Path, records: list[EngagementRecord]) -> None:
    """Write ``engagement.jsonl`` for a run directory."""
    lines = "".join(json.dumps(asdict(r)) + "\n" for r in records)
    (run_dir / ENGAGEMENT).write_text(lines)


def load_engagement(run_dir: Path) -> list[EngagementRecord]:
    """Read ``engagement.jsonl``, deriving it from the trajectories if not yet written.

    Engagement is re-derivable from the saved trajectories (which every graded run
    keeps), so — unlike :func:`load_scores` — a missing artifact is extracted on demand
    rather than raising. This lets old runs and resumed cells gain the metric for free.
    """
    path = run_dir / ENGAGEMENT
    if not path.exists():
        return extract_run_engagement(run_dir)
    return [
        _engagement_from_dict(json.loads(line))
        for line in path.read_text().splitlines()
        if line.strip()
    ]


def _engagement_from_dict(d: Mapping[str, Any]) -> EngagementRecord:
    """Rebuild an :class:`EngagementRecord` from its JSON dict (list -> tuple)."""
    return EngagementRecord(
        task_id=str(d["task_id"]),
        trial=int(d["trial"]),
        skills_read=tuple(d["skills_read"]),
    )
