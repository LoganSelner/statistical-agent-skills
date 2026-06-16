"""Sandbox execution interfaces — the seam between the agent and code execution.

An :class:`Executor` makes :class:`Session` objects; a session runs code in a
stateful kernel (namespace retained between calls, like notebook cells) and
returns an :class:`ExecResult`. The default executor is Docker-backed
(:mod:`statskills.sandbox.docker`); a local-subprocess executor
(:mod:`statskills.sandbox.local`) exists for tests and is **never** an automatic
fallback. A managed backend (e.g. E2B) can implement these protocols without the
agent changing. See ROADMAP §7.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class ExecResult:
    """The result of running one code cell in a session.

    ``stdout``/``stderr`` are the cell's captured streams (``stderr`` carries the
    traceback when a cell raises). ``ok`` is ``False`` if the cell raised;
    ``timed_out`` is ``True`` when the wall-clock budget was exceeded.
    """

    stdout: str
    stderr: str
    ok: bool
    timed_out: bool = False


@runtime_checkable
class Session(Protocol):
    """A live, stateful execution session (one kernel)."""

    def run(self, code: str) -> ExecResult: ...

    def close(self) -> None: ...


@runtime_checkable
class Executor(Protocol):
    """Creates fresh sessions. A fresh session per task gives isolation (§7)."""

    def start(self, datasets: tuple[Path, ...] = ()) -> Session: ...
