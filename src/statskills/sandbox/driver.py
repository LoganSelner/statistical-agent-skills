"""In-kernel execution driver — runs inside the sandbox (container or subprocess).

A line-oriented JSON protocol over stdin/stdout: read ``{"code": "..."}`` per
line, execute it in a persistent IPython ``InteractiveShell`` (so the namespace
is retained between cells, like a notebook), and write
``{"stdout": ..., "stderr": ..., "ok": bool}`` back as one JSON line. Captured
cell output is redirected to buffers so it never pollutes the protocol channel.

This module is intentionally self-contained — it imports only the stdlib and
IPython, so the same file runs both as a local subprocess (tests) and as the
entrypoint baked into the sandbox image. It must not import ``statskills``.
"""

from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import io
import json
import os
import re
import sys
import tempfile
import traceback

# Keep IPython's profile/history off any read-only or shared location.
os.environ.setdefault("IPYTHONDIR", tempfile.mkdtemp(prefix="ipython-"))

_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def main() -> None:
    from IPython.core.interactiveshell import InteractiveShell

    proto_out = sys.stdout  # the protocol channel — bound *before* any redirect
    shell = InteractiveShell.instance()
    if shell.history_manager is not None:
        shell.history_manager.enabled = False  # no sqlite writes

    # Warm up so first-call init noise doesn't land in a cell's captured output.
    with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
        shell.run_cell("pass", store_history=False)

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue
        code = req.get("code", "")

        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            result = shell.run_cell(code, store_history=False)

        stderr = err.getvalue()
        if not result.success and result.error_in_exec is not None and not stderr:
            stderr = "".join(traceback.format_exception(result.error_in_exec))

        resp = {
            "stdout": _ANSI.sub("", out.getvalue()),
            "stderr": _ANSI.sub("", stderr),
            "ok": bool(result.success),
        }
        proto_out.write(json.dumps(resp) + "\n")
        proto_out.flush()


if __name__ == "__main__":
    main()
