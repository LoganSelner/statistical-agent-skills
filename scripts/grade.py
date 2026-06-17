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
from statskills.tasks.loader import load_tasks


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

    print(f"\n=== Scores ({args.run_dir.name}) ===")
    for r in records:
        flag = "PASS" if r.passed else "FAIL"
        print(f"  {r.task_id:18} {flag}  answer={r.submitted!r}  ({r.detail})")

    metrics = aggregate(records)
    passed = sum(r.passed for r in records)
    print(
        f"\nABQ pass rate: {metrics.pass_rate:.0%} ({passed}/{metrics.n})"
        f"  ·  PASQ: {metrics.mean_score:.0%}"
        f"  ·  mean steps: {metrics.mean_steps:.1f}"
        f"  ·  mean tokens: {metrics.mean_prompt_tokens:.0f}p"
        f"/{metrics.mean_completion_tokens:.0f}c\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
