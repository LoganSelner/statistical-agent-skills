#!/usr/bin/env python3
"""Grade a saved run — score trajectories against its task set.

Reads ``<run_dir>/trajectories.jsonl``, reconstructs the run's task set from the
``task_set`` in ``run.json``, scores each trajectory against its task's expected answer
(no agent re-run; ROADMAP §3), writes ``<run_dir>/scores.jsonl``, and prints a pass rate
+ efficiency summary.

Usage:
    python scripts/grade.py results/run-20260616T153053Z
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys

import statskills.evaluation  # noqa: F401 - registers the built-in verifiers
from statskills.evaluation.grading import grade
from statskills.evaluation.metrics import aggregate
from statskills.evaluation.results import ScoreRecord
from statskills.evaluation.trials import summarize_trials
from statskills.tasks.loader import load_tasks


def _print_single(run_name: str, records: list[ScoreRecord]) -> None:
    print(f"\n=== Scores ({run_name}) ===")
    for record in records:
        flag = "PASS" if record.passed else "FAIL"
        print(f"  {record.task_id:24} {flag}  answer={record.submitted!r}")
    metrics = aggregate(records)
    passed = sum(r.passed for r in records)
    print(
        f"\nABQ pass rate: {metrics.pass_rate:.0%} ({passed}/{metrics.n})"
        f"  ·  PASQ: {metrics.mean_score:.0%}"
        f"  ·  mean steps: {metrics.mean_steps:.1f}"
        f"  ·  mean tokens: {metrics.mean_prompt_tokens:.0f}p"
        f"/{metrics.mean_completion_tokens:.0f}c\n"
    )


def _print_trials(run_name: str, records: list[ScoreRecord]) -> None:
    summary = summarize_trials(records)
    print(f"\n=== {run_name}: {summary.n_trials} trials x {summary.n_tasks} tasks ===")
    for task_id, freq in summary.per_task_pass_freq.items():
        print(f"  {task_id:24} passed {freq:.0%} of trials")
    rate, pasq = summary.pass_rate, summary.mean_score
    print(
        f"\nABQ pass rate: {rate.point:.0%}  (95% CI [{rate.low:.0%}, {rate.high:.0%}])"
        f"  ·  PASQ: {pasq.point:.0%}  (95% CI [{pasq.low:.0%}, {pasq.high:.0%}])"
    )
    print(
        f"mean steps: {summary.mean_steps:.1f}  ·  mean tokens: "
        f"{summary.mean_prompt_tokens:.0f}p/{summary.mean_completion_tokens:.0f}c\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Grade a saved run.")
    parser.add_argument("run_dir", type=Path, help="A results/run-* directory.")
    args = parser.parse_args()

    traj_path = args.run_dir / "trajectories.jsonl"
    if not traj_path.exists():
        print(f"No trajectories.jsonl in {args.run_dir}", file=sys.stderr)
        return 1
    trajectories = [
        json.loads(line) for line in traj_path.read_text().splitlines() if line.strip()
    ]

    run_meta_path = args.run_dir / "run.json"
    task_set = (
        json.loads(run_meta_path.read_text()).get("task_set")
        if run_meta_path.exists()
        else None
    )
    tasks_by_id = {t.id: t for t in load_tasks(task_set)}
    records = grade(trajectories, tasks_by_id)

    (args.run_dir / "scores.jsonl").write_text(
        "".join(json.dumps(asdict(r)) + "\n" for r in records)
    )

    n_trials = len({r.trial for r in records})
    if n_trials > 1:
        _print_trials(args.run_dir.name, records)
    else:
        _print_single(args.run_dir.name, records)
    return 0


if __name__ == "__main__":
    sys.exit(main())
