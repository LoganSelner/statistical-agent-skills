"""Run provenance — best-effort environment capture for reproducibility (ROADMAP §9).

Records the git state, an ISO-8601 UTC timestamp, and the Python version behind a
run. The richer provenance the design calls for — the EdenAI-routed model id,
the sandbox image digest, dataset hashes, the seed, and the fully resolved config
— is layered on by the agent / sandbox / experiment modules as those land; this
module owns only the project-agnostic basics. The git helpers are best-effort:
they return safe defaults when git is unavailable rather than failing a run.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import platform
import subprocess


def get_git_sha() -> str:
    """Return the short current git SHA, or ``'unknown'`` when unavailable."""
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return "unknown"


def get_git_dirty() -> bool:
    """Return ``True`` if the working tree has uncommitted changes."""
    try:
        output = subprocess.check_output(
            ["git", "status", "--porcelain"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        return bool(output)
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


@dataclass(frozen=True)
class RunProvenance:
    """Project-agnostic provenance for a single run.

    Domain layers extend the picture (model id, sandbox digest, dataset hashes,
    seed, resolved config) at their own boundaries; see ROADMAP §9.
    """

    git_sha: str
    git_dirty: bool
    python_version: str
    timestamp: str

    @classmethod
    def capture(cls) -> RunProvenance:
        """Snapshot the current environment (best-effort)."""
        return cls(
            git_sha=get_git_sha(),
            git_dirty=get_git_dirty(),
            python_version=platform.python_version(),
            timestamp=_utc_now_iso(),
        )
