"""Tests for the InfiAgent-DABench adapter (questions/labels → Task)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from statskills.tasks.adapters.dabench import _answer_key, load_dabench_tasks


def _write_fixture(data_dir: Path) -> None:
    (data_dir / "da-dev-tables").mkdir(parents=True)
    (data_dir / "da-dev-tables" / "t.csv").write_text("a\n1\n2\n")
    (data_dir / "da-dev-questions.jsonl").write_text(
        json.dumps(
            {
                "id": 0,
                "question": "What is the mean of a?",
                "concepts": ["descriptive"],
                "constraints": "Round to two decimal places.",
                "format": "@mean[mean_value], a float",
                "file_name": "t.csv",
                "level": "easy",
            }
        )
        + "\n"
        + json.dumps(
            {
                "id": 1,
                "question": "Is a monotonic?",
                "concepts": [],
                "constraints": "",
                "format": "@is_monotonic[answer], Yes or No",
                "file_name": "t.csv",
                "level": "easy",
            }
        )
        + "\n"
    )
    (data_dir / "da-dev-labels.jsonl").write_text(
        json.dumps({"id": 0, "common_answers": [["mean", "1.50"]]})
        + "\n"
        + json.dumps({"id": 1, "common_answers": [["is_monotonic", "Yes"]]})
        + "\n"
    )


def test_load_dabench_tasks_builds_tasks(tmp_path):
    _write_fixture(tmp_path)
    tasks = load_dabench_tasks(tmp_path)
    assert len(tasks) == 2

    mean_task = tasks[0]
    assert mean_task.id == "dabench-0"
    assert mean_task.source == "dabench"
    assert mean_task.datasets[0].name == "t.csv"
    assert "Round to two decimal places." in mean_task.prompt
    assert "@mean[mean_value]" in mean_task.prompt
    assert mean_task.concepts == ("descriptive",)

    assert mean_task.expected is not None
    (key,) = mean_task.expected.keys
    assert key.name == "mean"
    assert key.kind == "numeric"
    assert key.tolerance == pytest.approx(5e-3)
    assert key.value == "1.50"


def test_dabench_question_without_label_is_skipped(tmp_path):
    _write_fixture(tmp_path)
    (tmp_path / "da-dev-labels.jsonl").write_text(
        json.dumps({"id": 0, "common_answers": [["mean", "1.50"]]}) + "\n"
    )
    tasks = load_dabench_tasks(tmp_path)
    assert [t.id for t in tasks] == ["dabench-0"]


def test_dabench_multi_key_label(tmp_path):
    (tmp_path / "da-dev-tables").mkdir(parents=True)
    (tmp_path / "da-dev-tables" / "t.csv").write_text("a\n1\n")
    (tmp_path / "da-dev-questions.jsonl").write_text(
        json.dumps(
            {
                "id": 7,
                "question": "Two-part?",
                "concepts": [],
                "constraints": "",
                "format": "@slope[v1] @intercept[v2]",
                "file_name": "t.csv",
                "level": "medium",
            }
        )
        + "\n"
    )
    (tmp_path / "da-dev-labels.jsonl").write_text(
        json.dumps(
            {"id": 7, "common_answers": [["slope", "2.5"], ["intercept", "0.1"]]}
        )
        + "\n"
    )
    (task,) = load_dabench_tasks(tmp_path)
    assert task.expected is not None
    assert [k.name for k in task.expected.keys] == ["slope", "intercept"]


def test_answer_key_tolerance_from_decimals():
    assert _answer_key("x", "1.50").tolerance == pytest.approx(5e-3)  # 2 decimals
    assert _answer_key("x", "0.0039").tolerance == pytest.approx(5e-5)  # 4 decimals
    assert _answer_key("x", "42").tolerance == 1e-9  # integer
    assert _answer_key("x", "42").kind == "numeric"


def test_answer_key_categorical_inference():
    key = _answer_key("x", "Yes")
    assert key.kind == "categorical"
    assert key.tolerance is None
