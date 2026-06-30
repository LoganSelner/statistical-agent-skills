#!/usr/bin/env python3
"""Compose a traceable statistical report from a saved run's trajectory (ROADMAP §10).

Reads ``<run_dir>/trajectories.jsonl`` + ``run.json``, reconstructs the task, narrates
one trajectory into a typed, verified report with the run's model (or an override), and
writes Markdown. A pure consumer — it never re-runs the agent; it does make one LLM call
to compose (set ANTHROPIC_API_KEY / the provider's key).

Usage:
    python scripts/report.py results/<run-dir> --task-id reg-heteroskedasticity
    python scripts/report.py results/<run-dir>/<cell> --out report.md
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

from dotenv import load_dotenv

from statskills.agent.llm import build_llm, resolve_llm_config
from statskills.evaluation.runs import RUN_META, TRAJECTORIES
from statskills.reporting import compose_report, render_markdown, unverified
from statskills.tasks.loader import load_tasks


def _pick(
    trajectories: list[dict[str, Any]], task_id: str | None
) -> dict[str, Any] | None:
    """Trajectory to narrate: matching task_id (or any), preferring a finished one."""
    candidates = [t for t in trajectories if not task_id or t.get("task_id") == task_id]
    answered = [t for t in candidates if t.get("final_answer") and "error" not in t]
    return (answered or candidates or [None])[0]


def main() -> int:
    parser = argparse.ArgumentParser(description="Compose a report from a saved run.")
    parser.add_argument(
        "run_dir", type=Path, help="A results run (or matrix cell) dir."
    )
    parser.add_argument(
        "--task-id", default=None, help="Which task's trajectory to narrate."
    )
    parser.add_argument(
        "--provider", default=None, help="Override the report LLM provider."
    )
    parser.add_argument("--model", default=None, help="Override the report LLM model.")
    parser.add_argument(
        "--out", type=Path, default=None, help="Write Markdown here (else stdout)."
    )
    args = parser.parse_args()
    load_dotenv()

    traj_path, meta_path = args.run_dir / TRAJECTORIES, args.run_dir / RUN_META
    if not traj_path.exists() or not meta_path.exists():
        print(f"Need {TRAJECTORIES} and {RUN_META} in {args.run_dir}", file=sys.stderr)
        return 1
    trajectories = [
        json.loads(line) for line in traj_path.read_text().splitlines() if line.strip()
    ]
    meta = json.loads(meta_path.read_text())

    traj = _pick(trajectories, args.task_id)
    if traj is None:
        print(
            f"No trajectory for task {args.task_id!r} in {args.run_dir}",
            file=sys.stderr,
        )
        return 1
    tasks = {t.id: t for t in load_tasks(meta.get("task_set"))}
    task = tasks.get(str(traj.get("task_id")))
    if task is None:
        print(
            f"Task {traj.get('task_id')!r} not in the run's task set", file=sys.stderr
        )
        return 1

    # Preserve the run's recorded LLM settings (base_url, timeouts, ...) so the report
    # uses the same endpoint/limits; CLI flags override provider/model on top.
    cfg = meta.get("config", {})
    llm_keys = (
        "provider",
        "model",
        "base_url",
        "temperature",
        "max_tokens",
        "request_timeout",
    )
    llm_block = {key: cfg[key] for key in llm_keys if cfg.get(key) is not None}
    llm = build_llm(
        resolve_llm_config(llm_block, provider=args.provider, model=args.model)
    )
    report = compose_report(traj, task, llm)
    markdown = render_markdown(report)

    if args.out:
        args.out.write_text(markdown)
        print(f"Wrote {args.out}")
    else:
        print(markdown)
    flagged = unverified(report)
    if flagged:
        labels = ", ".join(c.label for c in flagged)
        print(
            f"\n[warning] {len(flagged)} unverified claim(s): {labels}", file=sys.stderr
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
