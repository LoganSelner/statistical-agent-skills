"""Tests for run orchestration (execute_run_config), offline via injected fakes."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from statskills.core.types import LLMResponse, Message
from statskills.experiments import runner
from statskills.sandbox.local import LocalExecutor
from statskills.tasks.schema import Task


class _ConstantLLM:
    """Always finalizes immediately — exercises the loop without code execution."""

    @property
    def model(self) -> str:
        return "fake/model"

    def complete(self, messages: list[Message]) -> LLMResponse:
        return LLMResponse(
            text="FINAL ANSWER: 1",
            model=self.model,
            finish_reason="stop",
            prompt_tokens=1,
            completion_tokens=1,
        )


def test_execute_run_config_writes_trajectories_and_provenance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tasks = [Task(id="a", prompt="p"), Task(id="b", prompt="p")]
    monkeypatch.setattr(runner, "load_tasks", lambda spec: tasks)

    out = tmp_path / "run"
    cfg = {
        "llm": {"provider": "ollama", "model": "x"},
        "tasks": {"set": "demo"},
        "executor": "local",
    }
    result = runner.execute_run_config(
        cfg, out_dir=out, trials=2, llm=_ConstantLLM(), sandbox=LocalExecutor()
    )

    assert result == out
    lines = (out / "trajectories.jsonl").read_text().splitlines()
    records = [json.loads(line) for line in lines if line.strip()]
    assert len(records) == 4  # 2 tasks x 2 trials
    assert {r["task_id"] for r in records} == {"a", "b"}
    assert {r["trial"] for r in records} == {0, 1}
    assert all(r["final_answer"] == "1" for r in records)

    meta = json.loads((out / "run.json").read_text())
    assert meta["trials"] == 2
    assert meta["task_set"] == {"set": "demo"}
    assert meta["config"]["provider"] == "ollama"
    assert meta["config"]["model"] == "fake/model"  # the injected llm's model id
    assert meta["config"]["executor"] == "local"
    assert sorted(meta["tasks"]) == ["a", "b"]
    assert "provenance" in meta
