"""Tests for the local sandbox executor (the driver + subprocess session)."""

from __future__ import annotations

from pathlib import Path

from statskills.sandbox.local import LocalExecutor


def test_runs_code_and_captures_stdout():
    sess = LocalExecutor(timeout=30).start()
    try:
        r = sess.run("print(2 + 2)")
        assert r.ok, r.stderr
        assert r.stdout.strip() == "4"
    finally:
        sess.close()


def test_namespace_is_stateful_across_cells():
    sess = LocalExecutor().start()
    try:
        sess.run("x = 21")
        r = sess.run("print(x * 2)")
        assert "42" in r.stdout
    finally:
        sess.close()


def test_errors_are_captured_not_raised():
    sess = LocalExecutor().start()
    try:
        r = sess.run("raise ValueError('boom')")
        assert not r.ok
        assert "ValueError" in r.stderr
        assert "boom" in r.stderr
    finally:
        sess.close()


def test_reads_dataset_by_basename(tmp_path: Path):
    csv = tmp_path / "data.csv"
    csv.write_text("a,b\n1,2\n3,4\n")
    sess = LocalExecutor().start(datasets=(csv,))
    try:
        r = sess.run("import pandas as pd; print(pd.read_csv('data.csv')['a'].sum())")
        assert r.ok, r.stderr
        assert "4" in r.stdout
    finally:
        sess.close()


def test_reads_staged_skill_file():
    # Skills are staged read-only under skills/ for agent-activated delivery.
    sess = LocalExecutor().start(
        skills={"hypothesis-test-selection.md": "Use Welch by default."}
    )
    try:
        r = sess.run("print(open('skills/hypothesis-test-selection.md').read())")
        assert r.ok, r.stderr
        assert "Use Welch by default." in r.stdout
    finally:
        sess.close()


def test_timeout_is_reported():
    sess = LocalExecutor(timeout=1.0).start()
    try:
        r = sess.run("import time; time.sleep(5)")
        assert r.timed_out
        assert not r.ok
    finally:
        sess.close()


def test_closed_session_returns_error():
    sess = LocalExecutor().start()
    sess.close()
    r = sess.run("print(1)")
    assert not r.ok
    assert "closed" in r.stderr


def test_captures_raw_fd_and_subprocess_output():
    # print, a direct fd-1 write, and a subprocess's stdout must all be captured
    # (not leak onto the protocol channel and crash the task).
    sess = LocalExecutor().start()
    try:
        r = sess.run(
            "import os\n"
            "print('via-print')\n"
            "os.write(1, b'via-fd1\\n')\n"
            "os.system('echo via-subprocess')"
        )
        assert r.ok, r.stderr
        assert "via-print" in r.stdout
        assert "via-fd1" in r.stdout
        assert "via-subprocess" in r.stdout
        # The protocol survived the raw writes — the next cell still works.
        assert sess.run("print(6 * 7)").stdout.strip() == "42"
    finally:
        sess.close()
