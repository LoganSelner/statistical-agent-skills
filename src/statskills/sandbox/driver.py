"""In-kernel execution driver — runs inside the sandbox (container or subprocess).

A line-oriented JSON protocol: read ``{"code": "..."}`` per line on stdin, execute
it in a persistent IPython ``InteractiveShell`` (so the namespace is retained
between cells, like a notebook), and write ``{"stdout", "stderr", "ok"}`` back as
one JSON line on a **private** protocol channel.

Output is captured at the **OS file-descriptor level**, not just Python's
``sys.stdout``: a dup of the original stdout is taken first (the protocol
channel), then the real fds 1/2 are redirected into temp files. So anything a cell
writes — ``print``, IPython tracebacks, ``os.write(1, ...)``, ``os.system``, or a
subprocess inheriting stdout — is captured and can never corrupt the protocol
stream.

This module is intentionally self-contained — it imports only the stdlib and
IPython, so the same file runs both as a local subprocess (tests) and as the
entrypoint baked into the sandbox image. It must not import ``statskills``.
"""

from __future__ import annotations

import json
import os
import re
import sys
import tempfile
import traceback
from typing import BinaryIO

# Keep IPython's profile/history off any read-only or shared location.
os.environ.setdefault("IPYTHONDIR", tempfile.mkdtemp(prefix="ipython-"))

_ANSI = re.compile(r"\x1b\[[0-9;]*m")
_MAX_CAPTURE_BYTES = 1_000_000  # per-cell cap; the container is memory-limited


def _drain(capture: BinaryIO) -> str:
    """Return a capture file's contents (ANSI-stripped), then reset it."""
    capture.seek(0)
    data = capture.read(_MAX_CAPTURE_BYTES + 1)
    capture.seek(0)
    capture.truncate()
    text = _ANSI.sub("", data[:_MAX_CAPTURE_BYTES].decode("utf-8", "replace"))
    if len(data) > _MAX_CAPTURE_BYTES:
        text += "\n... [output truncated]"
    return text


def main() -> None:
    from IPython.core.interactiveshell import InteractiveShell

    # Private protocol channel: a dup of the original stdout, taken *before* we
    # redirect fd 1, so cell output can never reach it.
    proto = os.fdopen(os.dup(1), "w", buffering=1, encoding="utf-8")

    # Redirect the real fds 1/2 into temp files so every write — Python-level or
    # raw (subprocess, os.write, os.system) — is captured, not sent to the host.
    cap_out: BinaryIO = tempfile.TemporaryFile()
    cap_err: BinaryIO = tempfile.TemporaryFile()
    os.dup2(cap_out.fileno(), 1)
    os.dup2(cap_err.fileno(), 2)

    shell = InteractiveShell.instance()
    if shell.history_manager is not None:
        shell.history_manager.enabled = False  # no sqlite writes

    shell.run_cell("pass", store_history=False)  # warm up; drain its init noise
    sys.stdout.flush()
    sys.stderr.flush()
    _drain(cap_out)
    _drain(cap_err)

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            continue

        result = shell.run_cell(request.get("code", ""), store_history=False)
        sys.stdout.flush()
        sys.stderr.flush()

        stdout = _drain(cap_out)
        stderr = _drain(cap_err)
        if not result.success and result.error_in_exec is not None and not stderr:
            stderr = "".join(traceback.format_exception(result.error_in_exec))

        proto.write(
            json.dumps({"stdout": stdout, "stderr": stderr, "ok": bool(result.success)})
            + "\n"
        )
        proto.flush()


if __name__ == "__main__":
    main()
