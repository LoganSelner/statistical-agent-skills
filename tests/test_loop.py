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
    codes = [
        "```python\nprint(1)\n```",
        "```python\nprint(2)\n```",
        "```python\nprint(3)\n```",
    ]
    traj = ReActAgent(FakeLLM(codes), LocalExecutor(), max_steps=2).run(task)
    assert traj.stop_reason == "max_steps"
    assert traj.final_answer is None
    assert [s.kind for s in traj.steps] == ["code", "code"]


def test_repeat_with_identical_output_is_nudged(tmp_path: Path):
    task = Task(id="t6", prompt="x", datasets=(_csv(tmp_path),))
    same = "```python\nprint(1)\n```"
    traj = ReActAgent(
        FakeLLM([same, same, "FINAL ANSWER: done"]), LocalExecutor(), max_steps=5
    ).run(task)
    assert [s.kind for s in traj.steps] == ["code", "repeat", "final"]
    assert traj.steps[1].observation is not None  # the code still ran (stateful-safe)
    assert traj.final_answer == "done"


def test_stateful_rerun_with_new_output_is_not_a_loop(tmp_path: Path):
    task = Task(id="t7", prompt="x", datasets=(_csv(tmp_path),))
    inc = "```python\nn = n + 1\nprint(n)\n```"
    traj = ReActAgent(
        FakeLLM(["```python\nn = 0\n```", inc, inc, "FINAL ANSWER: ok"]),
        LocalExecutor(),
        max_steps=6,
    ).run(task)
    # Identical `inc` source yields a new value each run (stateful), so it is NOT
    # flagged as a loop.
    assert [s.kind for s in traj.steps] == ["code", "code", "code", "final"]
    assert traj.final_answer == "ok"


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


def test_skill_payload_is_injected_into_system_message():
    task = Task(id="t8", prompt="x")
    llm = FakeLLM(["FINAL ANSWER: ok"])
    ReActAgent(llm, LocalExecutor()).run(task, skill_payload="SKILL-BODY-XYZ")
    system = llm.seen[0][0]
    assert system["role"] == "system"
    assert "# Available skills" in system["content"]
    assert "SKILL-BODY-XYZ" in system["content"]


def test_no_skill_payload_leaves_system_prompt_unchanged():
    from statskills.agent.prompts import SYSTEM_PROMPT

    llm = FakeLLM(["FINAL ANSWER: ok"])
    ReActAgent(llm, LocalExecutor()).run(Task(id="t9", prompt="x"))
    assert llm.seen[0][0]["content"] == SYSTEM_PROMPT
