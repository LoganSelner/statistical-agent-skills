"""The tap must observe the run without changing it (the core §2.2 invariant)."""

from __future__ import annotations

from statskills_api.stream import (
    RunTap,
    StepEvent,
    TappingExecutor,
    TappingLLM,
)

from statskills.agent.loop import ReActAgent
from statskills.tasks.schema import Task

_RESPONSES = ('Let me check.\n```python\nprint("hi")\n```', "FINAL ANSWER: 42")


def _drain(tap: RunTap) -> list[StepEvent]:
    events: list[StepEvent] = []
    while (event := tap.get(timeout=2.0)) is not None:
        events.append(event)
    return events


def test_tapping_does_not_change_the_trajectory(fake_llm, fake_executor) -> None:
    task = Task(id="t", prompt="p")

    plain = ReActAgent(fake_llm(*_RESPONSES), fake_executor()).run(task)

    tap = RunTap()
    tapped = ReActAgent(
        TappingLLM(fake_llm(*_RESPONSES), tap),
        TappingExecutor(fake_executor(), tap),
    ).run(task)

    # Identical scripts + deterministic executor → byte-for-byte identical trajectory.
    assert tapped == plain


def test_tap_emits_code_then_observation_then_final(fake_llm, fake_executor) -> None:
    tap = RunTap()
    ReActAgent(
        TappingLLM(fake_llm(*_RESPONSES), tap),
        TappingExecutor(fake_executor(), tap),
    ).run(Task(id="t", prompt="p"))
    tap.close()

    events = _drain(tap)
    assert [e.kind for e in events] == ["code", "observation", "final"]

    code, observation, final = events
    assert code.index == 0 and code.code == 'print("hi")'
    assert observation.observation == "ok" and observation.ok is True
    assert final.index == 1 and final.text == "42"


def test_step_event_to_dict_omits_unset_fields() -> None:
    assert StepEvent(kind="final", index=1, text="42").to_dict() == {
        "kind": "final",
        "index": 1,
        "text": "42",
    }
