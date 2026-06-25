"""Experiment orchestration — the condition-matrix runner (ROADMAP §11, Phase 5).

Runs a grid of configs (model x skills-disclosure cells) over N trials and reports each
skill arm's delta against its own model's baseline. The runner is pure: the
side-effecting operations (running a cell, grading, loading scores) are injected via
:class:`MatrixIO`, so it depends only on the evaluation library — never on the run/grade
CLIs — and is testable with fakes. The thin CLI ``scripts/run_matrix.py`` wires in the
real operations.
"""

from statskills.experiments.matrix import (
    Cell,
    CellResult,
    DeltaResult,
    Manifest,
    MatrixIO,
    MatrixResult,
    compose_cell_config,
    default_matrix_io,
    parse_manifest,
    run_matrix,
)

__all__ = [
    "Cell",
    "CellResult",
    "DeltaResult",
    "Manifest",
    "MatrixIO",
    "MatrixResult",
    "compose_cell_config",
    "default_matrix_io",
    "parse_manifest",
    "run_matrix",
]
