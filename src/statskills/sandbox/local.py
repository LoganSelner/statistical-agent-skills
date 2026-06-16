"""Local-subprocess executor — runs the sandbox driver in-process for tests/dev.

**Not isolated:** code runs in a subprocess of the harness venv with full
filesystem and network access. Use only for trusted code (the test suite, local
debugging). Real experiments use :class:`~statskills.sandbox.docker.DockerExecutor`;
this executor is never selected as an automatic fallback.
"""

from __future__ import annotations

from pathlib import Path
import shutil
import sys
import tempfile

from statskills.sandbox import driver as _driver
from statskills.sandbox.base import Session
from statskills.sandbox.session import SubprocessSession

_DRIVER_PATH = str(Path(_driver.__file__).resolve())


class LocalExecutor:
    """Spawns the driver as a local subprocess (trusted code only)."""

    def __init__(self, *, timeout: float = 30.0) -> None:
        self._timeout = timeout

    def start(self, datasets: tuple[Path, ...] = ()) -> Session:
        workdir = tempfile.mkdtemp(prefix="statskills-local-")
        for ds in datasets:
            shutil.copy(ds, Path(workdir) / ds.name)
        command = [sys.executable, "-u", _DRIVER_PATH]
        return SubprocessSession(
            command, timeout=self._timeout, cwd=workdir, cleanup_dir=workdir
        )
