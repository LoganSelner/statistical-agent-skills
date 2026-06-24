"""Condition-matrix runner: run a grid of cells over N trials and report deltas.

A *cell* is one ``(model, arm)`` condition backed by a config file; an *arm* is a skills
condition (``off``, ``L1``, ``L2``, ...). The runner executes each cell once over N
trials, then — per model — compares each skill arm against that model's single baseline
arm with a bootstrapped pass-rate-delta CI (ROADMAP §5, §8). Running each baseline once
and reusing it for every arm of the same model is the point: it keeps the deltas honest
(re-running the baseline per arm would compare against a different draw).

Pure orchestration: the side-effecting operations are injected via :class:`MatrixIO`, so
this module depends only on the evaluation library and is testable with fakes.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from statskills.evaluation.compare import TrialComparison, compare_trials
from statskills.evaluation.results import ScoreRecord
from statskills.evaluation.trials import TrialSummary, summarize_trials


@dataclass(frozen=True)
class Cell:
    """One grid cell: a ``(model, arm)`` condition backed by a config file."""

    model: str
    arm: str
    config: Path

    @property
    def label(self) -> str:
        """Filesystem-safe per-cell directory name, e.g. ``qwen2.5-coder-7b__L1``."""
        safe_model = self.model.replace("/", "-").replace(":", "-")
        return f"{safe_model}__{self.arm}"


@dataclass(frozen=True)
class Manifest:
    """A parsed grid: the cells, the per-model baseline arm, and the trial count."""

    trials: int
    baseline_arm: str
    cells: tuple[Cell, ...]


@dataclass(frozen=True)
class CellResult:
    """One executed cell: where it ran and its over-trials summary."""

    cell: Cell
    run_dir: Path
    summary: TrialSummary
    cached: bool  # loaded from an existing graded run (resume) rather than re-run


@dataclass(frozen=True)
class DeltaResult:
    """One skill arm compared against its model's baseline arm."""

    model: str
    arm: str
    comparison: TrialComparison


@dataclass(frozen=True)
class MatrixResult:
    """The full grid outcome: every cell's summary plus the per-arm deltas."""

    cells: tuple[CellResult, ...]
    deltas: tuple[DeltaResult, ...]


@dataclass(frozen=True)
class MatrixIO:
    """The side-effecting operations the runner depends on (injected for testing).

    ``run_cell`` executes one config over N trials into the given directory and returns
    the run directory; ``grade`` scores a run directory; ``load_scores`` reads an
    already-graded one (for resume). In production these are ``execute_run`` (wrapped to
    pass ``out_dir``), :func:`statskills.evaluation.runs.grade_run`, and
    :func:`statskills.evaluation.runs.load_scores`.
    """

    run_cell: Callable[[Path, int, Path], Path]
    grade: Callable[[Path], list[ScoreRecord]]
    load_scores: Callable[[Path], list[ScoreRecord]]


def _require_str(value: object, field: str) -> str:
    """Coerce a manifest field to ``str``, rejecting YAML's off/on/yes/no booleans.

    YAML 1.1 parses bare ``off``/``on``/``yes``/``no`` as booleans, which would silently
    break arm matching; require the value to be a quoted string with a clear message.
    """
    if isinstance(value, bool) or not isinstance(value, str):
        raise ValueError(
            f"{field} must be a quoted string (got {value!r}); "
            "quote YAML tokens like 'off'/'on'."
        )
    return value


def parse_manifest(data: Mapping[str, Any], *, base_dir: Path) -> Manifest:
    """Parse a grid manifest mapping into a validated :class:`Manifest`.

    ``config`` paths are resolved relative to ``base_dir`` (the manifest's directory).
    Validates that every model has exactly one baseline-arm cell and no duplicate arms.
    """
    raw_cells = data.get("cells")
    if not raw_cells:
        raise ValueError("Manifest has no 'cells'.")
    baseline_arm = _require_str(data.get("baseline_arm", "off"), "baseline_arm")
    trials = int(data.get("trials", 1))

    cells: list[Cell] = []
    for i, entry in enumerate(raw_cells):
        model = _require_str(entry.get("model"), f"cells[{i}].model")
        arm = _require_str(entry.get("arm"), f"cells[{i}].arm")
        config = entry.get("config")
        if not config:
            raise ValueError(f"cells[{i}] has no 'config'.")
        cells.append(Cell(model=model, arm=arm, config=(base_dir / config).resolve()))

    manifest = Manifest(trials=trials, baseline_arm=baseline_arm, cells=tuple(cells))
    _validate(manifest)
    return manifest


def _validate(manifest: Manifest) -> None:
    arms_by_model: dict[str, list[str]] = defaultdict(list)
    for cell in manifest.cells:
        arms_by_model[cell.model].append(cell.arm)
    for model, arms in arms_by_model.items():
        dupes = sorted(a for a in set(arms) if arms.count(a) > 1)
        if dupes:
            raise ValueError(f"Model {model!r} has duplicate arm(s): {dupes}.")
        if manifest.baseline_arm not in arms:
            raise ValueError(
                f"Model {model!r} has no baseline arm {manifest.baseline_arm!r} "
                f"(arms present: {sorted(arms)})."
            )


def run_matrix(
    manifest: Manifest,
    out_dir: Path,
    io: MatrixIO,
    *,
    resume: bool = False,
) -> MatrixResult:
    """Run every cell once into ``out_dir/<cell.label>`` and compute per-arm deltas.

    With ``resume=True`` a cell whose directory is already graded is loaded instead of
    re-run, so an interrupted grid can be continued without repeating completed cells.
    """
    out_dir.mkdir(parents=True, exist_ok=True)

    records_by_cell: dict[tuple[str, str], list[ScoreRecord]] = {}
    cell_results: list[CellResult] = []
    for cell in manifest.cells:
        cell_dir = out_dir / cell.label
        cached_records = _resume_cell(io, cell_dir) if resume else None
        if cached_records is not None:
            records, run_dir, cached = cached_records, cell_dir, True
        else:
            run_dir = io.run_cell(cell.config, manifest.trials, cell_dir)
            records, cached = io.grade(run_dir), False
        records_by_cell[(cell.model, cell.arm)] = records
        cell_results.append(
            CellResult(
                cell=cell,
                run_dir=run_dir,
                summary=summarize_trials(records),
                cached=cached,
            )
        )

    deltas: list[DeltaResult] = []
    for cell in manifest.cells:
        if cell.arm == manifest.baseline_arm:
            continue
        baseline = records_by_cell[(cell.model, manifest.baseline_arm)]
        treatment = records_by_cell[(cell.model, cell.arm)]
        deltas.append(
            DeltaResult(
                model=cell.model,
                arm=cell.arm,
                comparison=compare_trials(baseline, treatment),
            )
        )

    return MatrixResult(cells=tuple(cell_results), deltas=tuple(deltas))


def _resume_cell(io: MatrixIO, cell_dir: Path) -> list[ScoreRecord] | None:
    """Return an already-graded cell's records, or ``None`` if it must be run."""
    try:
        return io.load_scores(cell_dir)
    except FileNotFoundError:
        return None
