#!/usr/bin/env python3
"""Grade a saved slice run — score trajectories against the authored tasks.

Reads ``<run_dir>/trajectories.jsonl``, scores each trajectory against its task's
expected answer (no agent re-run; ROADMAP §3), writes ``<run_dir>/scores.jsonl``, and
prints a pass rate + efficiency summary.

Usage:
    python scripts/grade.py results/slice-20260616T153053Z
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
from statskills.tasks.authored.slice_tasks import load_slice_tasks


def main() -> int:
    parser = argparse.ArgumentParser(description="Grade a saved slice run.")
    parser.add_argument("run_dir", type=Path, help="A results/slice-* directory.")
    args = parser.parse_args()

    traj_path = args.run_dir / "trajectories.jsonl"
    if not traj_path.exists():
        print(f"No trajectories.jsonl in {args.run_dir}", file=sys.stderr)
        return 1
    trajectories = [
        json.loads(line) for line in traj_path.read_text().splitlines() if line.strip()
    ]

    tasks_by_id = {t.id: t for t in load_slice_tasks()}
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
        f"\npass rate: {metrics.pass_rate:.0%} ({passed}/{metrics.n})"
        f"  ·  mean steps: {metrics.mean_steps:.1f}"
        f"  ·  mean tokens: {metrics.mean_prompt_tokens:.0f}p"
        f"/{metrics.mean_completion_tokens:.0f}c\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
