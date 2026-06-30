"""Tests for the condition-matrix runner (pure; fake I/O, no Docker/LLM)."""

from __future__ import annotations

from pathlib import Path

import pytest

from statskills.evaluation.engagement import EngagementRecord
from statskills.evaluation.results import ScoreRecord
from statskills.experiments import (
    Cell,
    Manifest,
    MatrixIO,
    compose_cell_config,
    parse_manifest,
    run_matrix,
)


def _no_engagement(run_dir: Path) -> list[EngagementRecord]:
    """A fake engagement source for delta-focused tests (nothing read)."""
    return []


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

    def run_cell(cell: Cell, trials: int, out_dir: Path) -> Path:
        runs.append(out_dir.name)
        return out_dir

    io = MatrixIO(
        run_cell=run_cell,
        grade=lambda run_dir: _CANNED[run_dir.name],
        load_scores=lambda run_dir: (_ for _ in ()).throw(FileNotFoundError()),
        engagement=_no_engagement,
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

    def run_cell(cell: Cell, trials: int, out_dir: Path) -> Path:
        runs.append(out_dir.name)
        return out_dir

    def load_scores(run_dir: Path) -> list[ScoreRecord]:
        if run_dir.name == "m1__off":  # pretend this cell is already graded on disk
            return _CANNED["m1__off"]
        raise FileNotFoundError

    io = MatrixIO(
        run_cell=run_cell,
        grade=lambda d: _CANNED[d.name],
        load_scores=load_scores,
        engagement=_no_engagement,
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

    def run_cell(cell: Cell, trials: int, out_dir: Path) -> Path:
        runs.append(out_dir.name)
        return out_dir

    def load_scores(run_dir: Path) -> list[ScoreRecord]:
        # A stale 1-trial cell left over from a smoke run; the grid wants N=2.
        if run_dir.name == "m1__off":
            return [_rec("a", True, 0)]
        raise FileNotFoundError

    io = MatrixIO(
        run_cell=run_cell,
        grade=lambda d: _CANNED[d.name],
        load_scores=load_scores,
        engagement=_no_engagement,
    )
    cells = (Cell("m1", "off", Path("a")), Cell("m1", "L1", Path("a")))
    result = run_matrix(
        Manifest(trials=2, baseline_arm="off", cells=cells), tmp_path, io, resume=True
    )

    # The stale baseline is re-run (not reused), so the grid never mixes N=1 and N=2.
    assert "m1__off" in runs
    cached = {cr.cell.arm: cr.cached for cr in result.cells}
    assert cached == {"off": False, "L1": False}


def test_run_matrix_folds_engagement_into_cell_result(tmp_path: Path) -> None:
    def run_cell(cell: Cell, trials: int, out_dir: Path) -> Path:
        return out_dir

    # Per-cell skill reads: the L1 cell reads a skill on trial 0 only.
    eng: dict[str, list[EngagementRecord]] = {
        "m1__off": [EngagementRecord("a", 0, ()), EngagementRecord("a", 1, ())],
        "m1__L1": [EngagementRecord("a", 0, ("s",)), EngagementRecord("a", 1, ())],
    }
    io = MatrixIO(
        run_cell=run_cell,
        grade=lambda d: _CANNED[d.name],
        load_scores=lambda d: (_ for _ in ()).throw(FileNotFoundError()),
        engagement=lambda d: eng[d.name],
    )
    cells = (Cell("m1", "off", Path("a")), Cell("m1", "L1", Path("a")))
    result = run_matrix(
        Manifest(trials=2, baseline_arm="off", cells=cells), tmp_path, io
    )

    by_arm = {cr.cell.arm: cr.engagement for cr in result.cells}
    assert by_arm["off"].read_rate == 0.0
    assert by_arm["L1"].read_rate == 0.5  # 1 of 2 cells read a skill
    assert by_arm["L1"].skill_read_counts == {"s": 1}
    assert by_arm["L1"].per_task_read_freq == {"a": 0.5}


def test_parse_manifest_resolves_configs_arms_and_label(tmp_path: Path) -> None:
    data = {
        "trials": 5,
        "baseline_arm": "off",
        "arms": {"off": {}, "L1": {"mode": "curated", "resolution": "L1"}},
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
    # The arm's overlay from the shared `arms` map is attached to the cell.
    assert manifest.cells[0].skills == {}
    assert manifest.cells[1].skills == {"mode": "curated", "resolution": "L1"}


def test_parse_manifest_rejects_unknown_arm(tmp_path: Path) -> None:
    data = {
        "baseline_arm": "off",
        "arms": {"off": {}},
        "cells": [{"model": "m", "arm": "L9", "config": "b"}],
    }
    with pytest.raises(ValueError, match="not defined in manifest 'arms'"):
        parse_manifest(data, base_dir=tmp_path)


def test_parse_manifest_rejects_yaml_bool_arms_key(tmp_path: Path) -> None:
    # An unquoted `off:` key in the arms map is a YAML 1.1 bool — caught with the hint.
    data = {
        "baseline_arm": "off",
        "arms": {False: {}},
        "cells": [{"model": "m", "arm": "off", "config": "a"}],
    }
    with pytest.raises(ValueError, match="arms key"):
        parse_manifest(data, base_dir=tmp_path)


def test_parse_manifest_rejects_yaml_bool_arm(tmp_path: Path) -> None:
    # YAML 1.1 parses a bare `off` as False; require it quoted.
    data = {"cells": [{"model": "m", "arm": False, "config": "a"}]}
    with pytest.raises(ValueError, match="quoted string"):
        parse_manifest(data, base_dir=tmp_path)


def test_parse_manifest_requires_baseline_arm_per_model(tmp_path: Path) -> None:
    data = {
        "baseline_arm": "off",
        "arms": {"L1": {}},
        "cells": [{"model": "m", "arm": "L1", "config": "a"}],
    }
    with pytest.raises(ValueError, match="no baseline arm"):
        parse_manifest(data, base_dir=tmp_path)


def test_parse_manifest_rejects_duplicate_arm(tmp_path: Path) -> None:
    data = {
        "baseline_arm": "off",
        "arms": {"off": {}},
        "cells": [
            {"model": "m", "arm": "off", "config": "a"},
            {"model": "m", "arm": "off", "config": "b"},
        ],
    }
    with pytest.raises(ValueError, match="duplicate arm"):
        parse_manifest(data, base_dir=tmp_path)


def test_parse_manifest_rejects_non_mapping_arm(tmp_path: Path) -> None:
    # A falsy non-mapping arm value (`L1:` -> None, `L1: []`) must fail, not silently
    # become a no-skills arm (which would report a spurious zero effect).
    data = {
        "baseline_arm": "off",
        "arms": {"off": {}, "L1": []},
        "cells": [{"model": "m", "arm": "L1", "config": "a"}],
    }
    with pytest.raises(ValueError, match="must map to a skills block"):
        parse_manifest(data, base_dir=tmp_path)


def test_compose_cell_config_applies_arm_overlay(tmp_path: Path) -> None:
    base = tmp_path / "base.yaml"
    base.write_text("llm:\n  provider: ollama\n  model: x\ntasks:\n  set: authored\n")

    # Baseline arm: the overlay is empty → skills resolve to off (empty mapping).
    assert compose_cell_config(Cell("m", "off", base, skills={}))["skills"] == {}

    # Skill arm: the overlay becomes the skills block; base keys are preserved.
    overlay = {"mode": "curated", "delivery": "injected", "resolution": "L1"}
    cfg = compose_cell_config(Cell("m", "L1", base, skills=overlay))
    assert cfg["skills"] == overlay
    assert cfg["llm"] == {"provider": "ollama", "model": "x"}


def test_compose_cell_config_empty_arm_clears_inherited_skills(tmp_path: Path) -> None:
    # The arm map is authoritative: an empty (baseline) arm must clear a skills block
    # the base config carries, so the baseline is genuinely off.
    base = tmp_path / "skills_base.yaml"
    base.write_text("llm:\n  provider: ollama\n  model: x\nskills:\n  mode: curated\n")
    cfg = compose_cell_config(Cell("m", "off", base, skills={}))
    assert cfg["skills"] == {}  # not the base's curated block
