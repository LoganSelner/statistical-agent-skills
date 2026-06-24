"""Tests for the condition-matrix runner (pure; fake I/O, no Docker/LLM)."""

from __future__ import annotations

from pathlib import Path

import pytest

from statskills.evaluation.results import ScoreRecord
from statskills.experiments import (
    Cell,
    Manifest,
    MatrixIO,
    parse_manifest,
    run_matrix,
)


def _rec(task_id: str, passed: bool, trial: int) -> ScoreRecord:
    return ScoreRecord(
        task_id=task_id,
        passed=passed,
        score=1.0 if passed else 0.0,
        submitted=None,
        detail="",
        stop_reason="final",
        num_steps=1,
        prompt_tokens=0,
        completion_tokens=0,
        trial=trial,
    )


# Canned per-cell records keyed by cell label (model__arm). Task "a", 2 trials each;
# m1 off fails / L1+L2 pass (delta +1.0); m2 off+L1 both pass (delta 0.0).
_CANNED: dict[str, list[ScoreRecord]] = {
    "m1__off": [_rec("a", False, 0), _rec("a", False, 1)],
    "m1__L1": [_rec("a", True, 0), _rec("a", True, 1)],
    "m1__L2": [_rec("a", True, 0), _rec("a", True, 1)],
    "m2__off": [_rec("a", True, 0), _rec("a", True, 1)],
    "m2__L1": [_rec("a", True, 0), _rec("a", True, 1)],
}


def test_cell_label_is_filesystem_safe() -> None:
    cell = Cell(model="qwen2.5-coder:7b", arm="L2", config=Path("x"))
    assert cell.label == "qwen2.5-coder-7b__L2"


def test_run_matrix_runs_each_cell_once_and_deltas_vs_model_baseline(
    tmp_path: Path,
) -> None:
    runs: list[str] = []

    def run_cell(config: Path, trials: int, out_dir: Path) -> Path:
        runs.append(out_dir.name)
        return out_dir

    io = MatrixIO(
        run_cell=run_cell,
        grade=lambda run_dir: _CANNED[run_dir.name],
        load_scores=lambda run_dir: (_ for _ in ()).throw(FileNotFoundError()),
    )
    cells = (
        Cell("m1", "off", Path("a")),
        Cell("m1", "L1", Path("a")),
        Cell("m1", "L2", Path("a")),
        Cell("m2", "off", Path("a")),
        Cell("m2", "L1", Path("a")),
    )
    manifest = Manifest(trials=2, baseline_arm="off", cells=cells)
    result = run_matrix(manifest, tmp_path, io)

    # Every cell ran exactly once — the m1 baseline is shared by L1 and L2, not re-run.
    assert sorted(runs) == ["m1__L1", "m1__L2", "m1__off", "m2__L1", "m2__off"]
    assert runs.count("m1__off") == 1
    assert all(not cr.cached for cr in result.cells)

    deltas = {
        (d.model, d.arm): d.comparison.pass_rate_delta.point for d in result.deltas
    }
    assert deltas == {("m1", "L1"): 1.0, ("m1", "L2"): 1.0, ("m2", "L1"): 0.0}


def test_run_matrix_resume_skips_already_graded_cells(tmp_path: Path) -> None:
    runs: list[str] = []

    def run_cell(config: Path, trials: int, out_dir: Path) -> Path:
        runs.append(out_dir.name)
        return out_dir

    def load_scores(run_dir: Path) -> list[ScoreRecord]:
        if run_dir.name == "m1__off":  # pretend this cell is already graded on disk
            return _CANNED["m1__off"]
        raise FileNotFoundError

    io = MatrixIO(
        run_cell=run_cell, grade=lambda d: _CANNED[d.name], load_scores=load_scores
    )
    cells = (Cell("m1", "off", Path("a")), Cell("m1", "L1", Path("a")))
    result = run_matrix(
        Manifest(trials=2, baseline_arm="off", cells=cells), tmp_path, io, resume=True
    )

    assert "m1__off" not in runs and "m1__L1" in runs
    assert {cr.cell.arm: cr.cached for cr in result.cells} == {"off": True, "L1": False}
    # The cached baseline still feeds the delta correctly.
    assert result.deltas[0].comparison.pass_rate_delta.point == 1.0


def test_run_matrix_resume_reruns_cell_with_mismatched_trial_count(
    tmp_path: Path,
) -> None:
    runs: list[str] = []

    def run_cell(config: Path, trials: int, out_dir: Path) -> Path:
        runs.append(out_dir.name)
        return out_dir

    def load_scores(run_dir: Path) -> list[ScoreRecord]:
        # A stale 1-trial cell left over from a smoke run; the grid wants N=2.
        if run_dir.name == "m1__off":
            return [_rec("a", True, 0)]
        raise FileNotFoundError

    io = MatrixIO(
        run_cell=run_cell, grade=lambda d: _CANNED[d.name], load_scores=load_scores
    )
    cells = (Cell("m1", "off", Path("a")), Cell("m1", "L1", Path("a")))
    result = run_matrix(
        Manifest(trials=2, baseline_arm="off", cells=cells), tmp_path, io, resume=True
    )

    # The stale baseline is re-run (not reused), so the grid never mixes N=1 and N=2.
    assert "m1__off" in runs
    cached = {cr.cell.arm: cr.cached for cr in result.cells}
    assert cached == {"off": False, "L1": False}


def test_parse_manifest_resolves_configs_and_label(tmp_path: Path) -> None:
    data = {
        "trials": 5,
        "baseline_arm": "off",
        "cells": [
            {"model": "m", "arm": "off", "config": "a.yaml"},
            {"model": "m", "arm": "L1", "config": "sub/b.yaml"},
        ],
    }
    manifest = parse_manifest(data, base_dir=tmp_path)
    assert manifest.trials == 5 and manifest.baseline_arm == "off"
    assert manifest.cells[0].config == (tmp_path / "a.yaml").resolve()
    assert manifest.cells[1].config == (tmp_path / "sub" / "b.yaml").resolve()
    assert manifest.cells[0].label == "m__off"


def test_parse_manifest_rejects_yaml_bool_arm(tmp_path: Path) -> None:
    # YAML 1.1 parses a bare `off` as False; require it quoted.
    data = {"cells": [{"model": "m", "arm": False, "config": "a"}]}
    with pytest.raises(ValueError, match="quoted string"):
        parse_manifest(data, base_dir=tmp_path)


def test_parse_manifest_requires_baseline_arm_per_model(tmp_path: Path) -> None:
    data = {
        "baseline_arm": "off",
        "cells": [{"model": "m", "arm": "L1", "config": "a"}],
    }
    with pytest.raises(ValueError, match="no baseline arm"):
        parse_manifest(data, base_dir=tmp_path)


def test_parse_manifest_rejects_duplicate_arm(tmp_path: Path) -> None:
    data = {
        "baseline_arm": "off",
        "cells": [
            {"model": "m", "arm": "off", "config": "a"},
            {"model": "m", "arm": "off", "config": "b"},
        ],
    }
    with pytest.raises(ValueError, match="duplicate arm"):
        parse_manifest(data, base_dir=tmp_path)
