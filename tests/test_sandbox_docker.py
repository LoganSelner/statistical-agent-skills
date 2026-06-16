"""Docker-sandbox integration test — skipped unless the image is built.

Runs only when the pinned sandbox image is available locally (e.g. after
`make sandbox-image`). Marked ``slow`` so the default ``make test`` skips it.
"""

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess

import pytest

from statskills.sandbox.docker import DEFAULT_IMAGE, DockerExecutor


def _image_available() -> bool:
    if shutil.which("docker") is None:
        return False
    return (
        subprocess.run(
            ["docker", "image", "inspect", DEFAULT_IMAGE], capture_output=True
        ).returncode
        == 0
    )


pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(not _image_available(), reason="sandbox image not built"),
]


def test_docker_executor_stateful_isolated_and_reads_data(tmp_path: Path):
    csv = tmp_path / "data.csv"
    csv.write_text("a\n1\n2\n3\n")
    sess = DockerExecutor(timeout=60).start(datasets=(csv,))
    try:
        r = sess.run("import pandas as pd; print(pd.read_csv('data.csv')['a'].sum())")
        assert r.ok, r.stderr
        assert "6" in r.stdout

        sess.run("y = 10")
        r2 = sess.run("print(y + 5)")
        assert "15" in r2.stdout  # stateful namespace persists across cells

        # Network is disabled (--network none): an outbound connection must fail.
        r3 = sess.run(
            "import socket; socket.create_connection(('1.1.1.1', 53), timeout=3)"
        )
        assert not r3.ok
    finally:
        sess.close()
