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
