"""Tests for the ReAct CodeAct loop (scripted fake LLM + local executor)."""

from __future__ import annotations

import json
from pathlib import Path

from statskills.agent.loop import ReActAgent
from statskills.core.types import LLMResponse, Message
from statskills.sandbox.local import LocalExecutor
from statskills.tasks.schema import Dataset, Task


class FakeLLM:
    """Returns scripted completion texts in order; satisfies the LLM protocol."""

    def __init__(self, responses: list[str], model: str = "fake/model") -> None:
        self._responses = responses
        self._i = 0
        self._model = model
        self.seen: list[list[Message]] = []

    @property
    def model(self) -> str:
        return self._model

    def complete(self, messages: list[Message]) -> LLMResponse:
        self.seen.append(list(messages))
        text = self._responses[self._i]
        self._i += 1
        return LLMResponse(
            text=text,
            model=self._model,
            finish_reason="stop",
            prompt_tokens=3,
            completion_tokens=5,
        )


def _csv(tmp_path: Path) -> Dataset:
    p = tmp_path / "data.csv"
    p.write_text("a\n1\n2\n3\n")
    return Dataset(p)


def test_runs_code_then_finalizes(tmp_path: Path):
    task = Task(id="t1", prompt="Mean of a?", datasets=(_csv(tmp_path),))
    llm = FakeLLM(
        [
            "```python\nimport pandas as pd\n"
            "print(pd.read_csv('data.csv')['a'].mean())\n```",
            "FINAL ANSWER: 2.0",
        ]
    )
    traj = ReActAgent(llm, LocalExecutor(), max_steps=5).run(task)
    assert traj.stop_reason == "final"
    assert traj.final_answer == "2.0"
    assert [s.kind for s in traj.steps] == ["code", "final"]
    assert traj.steps[0].ok
    assert "2.0" in (traj.steps[0].observation or "")
    assert traj.prompt_tokens == 6 and traj.completion_tokens == 10


def test_stops_at_max_steps_without_final(tmp_path: Path):
    task = Task(id="t2", prompt="loop", datasets=(_csv(tmp_path),))
    code = "```python\nprint(1)\n```"
    traj = ReActAgent(FakeLLM([code, code, code]), LocalExecutor(), max_steps=2).run(
        task
    )
    assert traj.stop_reason == "max_steps"
    assert traj.final_answer is None
    assert len(traj.steps) == 2


def test_nudges_on_no_action_then_finalizes():
    task = Task(id="t3", prompt="x")
    traj = ReActAgent(
        FakeLLM(["Let me think about it.", "FINAL ANSWER: 42"]),
        LocalExecutor(),
        max_steps=5,
    ).run(task)
    assert [s.kind for s in traj.steps] == ["no_action", "final"]
    assert traj.final_answer == "42"


def test_failed_code_is_observed_and_recoverable(tmp_path: Path):
    task = Task(id="t5", prompt="x", datasets=(_csv(tmp_path),))
    traj = ReActAgent(
        FakeLLM(["```python\nprint(undefined_var)\n```", "FINAL ANSWER: recovered"]),
        LocalExecutor(),
        max_steps=5,
    ).run(task)
    assert traj.steps[0].ok is False
    assert "NameError" in (traj.steps[0].observation or "")
    assert traj.final_answer == "recovered"


def test_trajectory_to_dict_is_json_serializable():
    task = Task(id="t4", prompt="x")
    traj = ReActAgent(FakeLLM(["FINAL ANSWER: ok"]), LocalExecutor()).run(task)
    json.dumps(traj.to_dict())  # must not raise
