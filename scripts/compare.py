#!/usr/bin/env python3
"""Compare two graded runs (baseline vs treatment): pass-rate + efficiency deltas.

Reads ``<run>/scores.jsonl`` from each run directory (grade them first) and reports the
ABQ/PASQ and step/token deltas over the tasks they share, plus which tasks flipped.
Condition labels come from each run's ``run.json`` (skills mode + model).

Usage:
    python scripts/compare.py results/run-OFF results/run-CURATED
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from statskills.evaluation.compare import compare_runs
from statskills.evaluation.metrics import Metrics
from statskills.evaluation.results import ScoreRecord


def _load_scores(run_dir: Path) -> list[ScoreRecord]:
    path = run_dir / "scores.jsonl"
    if not path.exists():
        raise SystemExit(f"No scores.jsonl in {run_dir} — grade the run first.")
    return [
        ScoreRecord(**json.loads(line))
        for line in path.read_text().splitlines()
        if line.strip()
    ]


def _label(run_dir: Path) -> str:
    meta_path = run_dir / "run.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    skills = (meta.get("skills") or {}).get("mode", "?")
    model = (meta.get("config") or {}).get("model", "?")
    return f"{run_dir.name} (skills={skills}, model={model})"


def _row(
    name: str, baseline: Metrics, treatment: Metrics, key: str, *, pct: bool
) -> str:
    base, treat = getattr(baseline, key), getattr(treatment, key)
    delta = treat - base
    if pct:
        cells = (f"{base:.0%}", f"{treat:.0%}", f"{delta:+.0%}")
    else:
        cells = (f"{base:.1f}", f"{treat:.1f}", f"{delta:+.1f}")
    return f"  {name:<16}{cells[0]:>9}{cells[1]:>11}{cells[2]:>10}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare two graded runs.")
    parser.add_argument("baseline", type=Path, help="results/run-* (e.g. skills off)")
    parser.add_argument(
        "treatment", type=Path, help="results/run-* (e.g. skills curated)"
    )
    args = parser.parse_args()

    comparison = compare_runs(_load_scores(args.baseline), _load_scores(args.treatment))
    base, treat = comparison.baseline, comparison.treatment

    print(f"\nbaseline : {_label(args.baseline)}")
    print(f"treatment: {_label(args.treatment)}")
    print(f"\n{comparison.n_common} shared task(s)\n")
    print(f"  {'metric':<16}{'baseline':>9}{'treatment':>11}{'delta':>10}")
    print(_row("ABQ pass rate", base, treat, "pass_rate", pct=True))
    print(_row("PASQ", base, treat, "mean_score", pct=True))
    print(_row("mean steps", base, treat, "mean_steps", pct=False))
    print(_row("mean prompt tok", base, treat, "mean_prompt_tokens", pct=False))
    print(_row("mean compl tok", base, treat, "mean_completion_tokens", pct=False))

    if comparison.gained:
        print(f"\n  gained ({len(comparison.gained)}): {', '.join(comparison.gained)}")
    if comparison.lost:
        print(f"  lost   ({len(comparison.lost)}): {', '.join(comparison.lost)}")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
