"""Shared filesystem paths for the CLI scripts (adapter layer).

The library never hardcodes a repo-relative results location; the CLIs own that policy
and pass an explicit ``out_dir`` inward. Keeping these constants in one place lets the
run and matrix CLIs share them without importing each other.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = REPO_ROOT / "results"
DEFAULT_CONFIG = REPO_ROOT / "configs" / "slice.yaml"
