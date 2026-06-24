#!/usr/bin/env python3
"""Run a condition-matrix grid (model x skills-disclosure) and report per-arm deltas.

Reads a grid manifest (cells = {model, arm, config}; a baseline arm per model), runs
each cell once over N trials into ``results/matrix-<ts>/<cell>/``, grades it, and prints
a pass-rate-CI table plus each skill arm's bootstrapped delta against its model's
baseline. Writes ``matrix.json`` for provenance and later figures. Reuses
``execute_run`` (run_slice) and ``grade_run``/``load_scores`` (evaluation.runs) via the
injected ``MatrixIO`` seam.

Usage:
    python scripts/run_matrix.py configs/experiments/disclosure_grid.yaml
    python scripts/run_matrix.py configs/experiments/disclosure_grid.yaml --trials 1
    python scripts/run_matrix.py <manifest> --out results/matrix-RESUME --resume
"""

from __future__ import annotations

import argparse
from dataclasses import replace
from datetime import UTC, datetime
import json
import logging
from pathlib import Path
import sys

from dotenv import load_dotenv
from run_slice import RESULTS_DIR, execute_run
import yaml

from statskills.evaluation.runs import grade_run, load_scores
from statskills.evaluation.trials import CI
from statskills.experiments import (
    MatrixIO,
    MatrixResult,
    parse_manifest,
    run_matrix,
)
from statskills.sandbox.docker import DockerError

logger = logging.getLogger("statskills.matrix")


def _ci(ci: CI) -> str:
    return f"{ci.point:.0%} [{ci.low:.0%}, {ci.high:.0%}]"


def _delta_ci(ci: CI) -> str:
    return f"{ci.point:+.0%} [{ci.low:+.0%}, {ci.high:+.0%}]"


def _short(model: str) -> str:
    """A compact column tag, e.g. ``qwen2.5-coder:7b`` -> ``7b``."""
    return model.rsplit(":", 1)[-1]


def _print_matrix(result: MatrixResult, out_dir: Path) -> None:
    delta_by = {(d.model, d.arm): d.comparison.pass_rate_delta for d in result.deltas}
    print(f"\n########## MATRIX ({len(result.cells)} cells) ##########")
    print(f"out: {out_dir}\n")
    print(f"  {'model':<18}{'arm':<5}{'pass-rate (95% CI)':<24}{'Δ vs baseline':<22}")
    for cr in result.cells:
        delta = delta_by.get((cr.cell.model, cr.cell.arm))
        cached = "  (cached)" if cr.cached else ""
        print(
            f"  {cr.cell.model:<18}{cr.cell.arm:<5}"
            f"{_ci(cr.summary.pass_rate):<24}"
            f"{(_delta_ci(delta) if delta else '—'):<22}{cached}"
        )

    # Per-task pass frequency, one column per cell (rows = tasks).
    cols = [(f"{_short(cr.cell.model)}:{cr.cell.arm}", cr) for cr in result.cells]
    tasks = sorted({t for cr in result.cells for t in cr.summary.per_task_pass_freq})
    print(
        f"\n  per-task pass frequency\n  {'task':<26}"
        + "".join(f"{c:>10}" for c, _ in cols)
    )
    for task in tasks:
        row = "".join(
            f"{cr.summary.per_task_pass_freq.get(task, 0.0):>9.0%} " for _, cr in cols
        )
        print(f"  {task:<26}{row}")
    print()


def _ci_dict(ci: CI) -> dict[str, float]:
    return {"point": ci.point, "low": ci.low, "high": ci.high}


def _matrix_json(
    result: MatrixResult, out_dir: Path, trials: int, baseline: str
) -> dict:
    delta_by = {(d.model, d.arm): d for d in result.deltas}
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "out_dir": str(out_dir),
        "trials": trials,
        "baseline_arm": baseline,
        "cells": [
            {
                "model": cr.cell.model,
                "arm": cr.cell.arm,
                "label": cr.cell.label,
                "run_dir": str(cr.run_dir),
                "cached": cr.cached,
                "n_trials": cr.summary.n_trials,
                "pass_rate": _ci_dict(cr.summary.pass_rate),
                "mean_score": _ci_dict(cr.summary.mean_score),
                "per_task_pass_freq": cr.summary.per_task_pass_freq,
            }
            for cr in result.cells
        ],
        "deltas": [
            {
                "model": d.model,
                "arm": d.arm,
                "pass_rate_delta": _ci_dict(d.comparison.pass_rate_delta),
                "per_task_freq_delta": d.comparison.per_task_freq_delta,
            }
            for d in delta_by.values()
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a condition-matrix grid.")
    parser.add_argument("manifest", type=Path, help="Grid manifest YAML.")
    parser.add_argument("--trials", type=int, default=None, help="Override manifest N.")
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output dir (default results/matrix-<ts>).",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help=(
            "Reuse cells already graded at this N in --out (continue an interrupted "
            "grid). Cells left from a different N (e.g. a smoke) are re-run; use a "
            "fresh --out for a different manifest."
        ),
    )
    parser.add_argument("--executor", choices=["docker", "local"], default=None)
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )
    load_dotenv()

    data = yaml.safe_load(args.manifest.read_text()) or {}
    try:
        manifest = parse_manifest(data, base_dir=args.manifest.resolve().parent)
    except (ValueError, TypeError) as exc:
        logger.error("Invalid manifest %s: %s", args.manifest, exc)
        return 1
    if args.trials is not None:
        manifest = replace(manifest, trials=args.trials)

    out_dir = args.out or RESULTS_DIR / datetime.now(UTC).strftime(
        "matrix-%Y%m%dT%H%M%SZ"
    )

    def run_cell(config: Path, trials: int, cell_dir: Path) -> Path:
        return execute_run(
            config, executor=args.executor, trials=trials, out_dir=cell_dir
        )

    io = MatrixIO(run_cell=run_cell, grade=grade_run, load_scores=load_scores)
    try:
        result = run_matrix(manifest, out_dir, io, resume=args.resume)
    except (ValueError, DockerError) as exc:
        logger.error("%s", exc)
        return 1

    _print_matrix(result, out_dir)
    report = _matrix_json(result, out_dir, manifest.trials, manifest.baseline_arm)
    (out_dir / "matrix.json").write_text(json.dumps(report, indent=2))
    print(f"Wrote {out_dir / 'matrix.json'}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
