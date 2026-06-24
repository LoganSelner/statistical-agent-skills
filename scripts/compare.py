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

from statskills.evaluation.compare import compare_runs, compare_trials
from statskills.evaluation.metrics import Metrics
from statskills.evaluation.results import ScoreRecord
from statskills.evaluation.runs import load_scores


def _load_scores(run_dir: Path) -> list[ScoreRecord]:
    try:
        return load_scores(run_dir)
    except FileNotFoundError as exc:
        raise SystemExit(str(exc)) from exc


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


def _print_trials(
    baseline: list[ScoreRecord],
    treatment: list[ScoreRecord],
    base_label: str,
    treat_label: str,
) -> None:
    comparison = compare_trials(baseline, treatment)
    base, treat = comparison.baseline, comparison.treatment
    print(f"\nbaseline : {base_label}")
    print(f"treatment: {treat_label}")
    print(
        f"\n{base.n_trials} vs {treat.n_trials} trials · "
        f"{base.n_tasks} shared task(s) · per-task pass frequency\n"
    )
    print(f"  {'task':<26}{'baseline':>9}{'treatment':>11}{'delta':>9}")
    for task_id, delta in comparison.per_task_freq_delta.items():
        bf = base.per_task_pass_freq.get(task_id, 0.0)
        tf = treat.per_task_pass_freq.get(task_id, 0.0)
        print(f"  {task_id:<26}{bf:>8.0%}{tf:>11.0%}{delta:>+9.0%}")
    rate, pasq = comparison.pass_rate_delta, treat.mean_score
    rb, rt = base.pass_rate, treat.pass_rate
    print(
        f"\nABQ pass rate: baseline {rb.point:.0%} (CI [{rb.low:.0%}, {rb.high:.0%}])"
        f"  vs  treatment {rt.point:.0%} (CI [{rt.low:.0%}, {rt.high:.0%}])"
    )
    print(f"delta: {rate.point:+.0%}  (95% CI [{rate.low:+.0%}, {rate.high:+.0%}])")
    print(f"(treatment PASQ {pasq.point:.0%}, CI [{pasq.low:.0%}, {pasq.high:.0%}])\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare two graded runs.")
    parser.add_argument("baseline", type=Path, help="results/run-* (e.g. skills off)")
    parser.add_argument(
        "treatment", type=Path, help="results/run-* (e.g. skills curated)"
    )
    args = parser.parse_args()

    base_records = _load_scores(args.baseline)
    treat_records = _load_scores(args.treatment)
    multi = (
        len({r.trial for r in base_records}) > 1
        or len({r.trial for r in treat_records}) > 1
    )
    if multi:
        _print_trials(
            base_records, treat_records, _label(args.baseline), _label(args.treatment)
        )
        return 0

    comparison = compare_runs(base_records, treat_records)
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
