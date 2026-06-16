"""Subprocess-backed execution session shared by the local and Docker executors.

Both executors spawn the same self-contained driver (``sandbox/driver.py``) and
speak the same JSON-lines protocol over its stdin/stdout; they differ only in the
command that launches it (a local ``python`` vs ``docker run -i ...``). This class
owns the protocol, the per-call wall-clock timeout, and teardown.
"""

from __future__ import annotations

from collections.abc import Callable
import json
import select
import shutil
import subprocess
import time

from statskills.sandbox.base import ExecResult


class SubprocessSession:
    """Drives the sandbox driver over a subprocess's stdin/stdout pipes."""

    def __init__(
        self,
        command: list[str],
        *,
        timeout: float,
        cwd: str | None = None,
        terminate: Callable[[], None] | None = None,
        cleanup_dir: str | None = None,
    ) -> None:
        self._timeout = timeout
        self._terminate = terminate
        self._cleanup_dir = cleanup_dir
        self._closed = False
        self._proc = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            cwd=cwd,
            bufsize=1,
        )

    def run(self, code: str) -> ExecResult:
        if self._closed or self._proc.poll() is not None:
            return ExecResult("", "sandbox session is closed.", ok=False)
        assert self._proc.stdin is not None and self._proc.stdout is not None

        try:
            self._proc.stdin.write(json.dumps({"code": code}) + "\n")
            self._proc.stdin.flush()
        except (BrokenPipeError, OSError):
            self._closed = True
            return ExecResult("", "sandbox process is not accepting input.", ok=False)

        # Read until a well-formed protocol response, re-selecting against the
        # remaining budget. The driver isolates cell output on a private channel,
        # so stray lines here are rare — but tolerate them rather than crash the
        # task on a JSONDecodeError.
        deadline = time.monotonic() + self._timeout
        while True:
            remaining = deadline - time.monotonic()
            if (
                remaining <= 0
                or not select.select([self._proc.stdout], [], [], remaining)[0]
            ):
                self._kill()
                return ExecResult(
                    "",
                    f"execution timed out after {self._timeout:.0f}s.",
                    ok=False,
                    timed_out=True,
                )
            line = self._proc.stdout.readline()
            if not line:
                self._closed = True
                return ExecResult(
                    "", "sandbox produced no output (process died).", ok=False
                )
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(data, dict) and "ok" in data:
                return ExecResult(
                    stdout=data.get("stdout", ""),
                    stderr=data.get("stderr", ""),
                    ok=bool(data.get("ok", False)),
                )

    def close(self) -> None:
        if not self._closed:
            self._closed = True
            self._kill()
        self._cleanup()

    def _kill(self) -> None:
        if self._terminate is not None:
            try:
                self._terminate()
            except Exception:
                pass
        for step in (self._proc.terminate, self._proc.kill):
            if self._proc.poll() is not None:
                break
            try:
                step()
                self._proc.wait(timeout=5)
            except Exception:
                pass

    def _cleanup(self) -> None:
        if self._cleanup_dir is not None:
            shutil.rmtree(self._cleanup_dir, ignore_errors=True)
            self._cleanup_dir = None
