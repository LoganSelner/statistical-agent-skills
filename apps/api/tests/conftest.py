"""Shared test fakes — a canned LLM and an in-memory executor (no Docker, no API key).

These let the api tests drive the real agent loop + report composer hermetically: the
``FakeLLM`` replays scripted turns and the ``FakeExecutor`` returns canned observations,
so a test exercises streaming, the job lifecycle, and report composition without any
network or container. Exposed as fixtures returning the classes, so a test constructs
fresh instances (e.g. two identical LLMs for the tap pass-through comparison).
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import pytest

from statskills.core.types import LLMResponse, Message
from statskills.sandbox.base import ExecResult, Session


class FakeLLM:
    """Replays canned response strings (the last repeats once exhausted)."""

    def __init__(self, *responses: str) -> None:
        self._responses = list(responses)
        self.calls = 0

    @property
    def model(self) -> str:
        return "fake-model"

    def complete(self, messages: list[Message]) -> LLMResponse:
        text = self._responses[min(self.calls, len(self._responses) - 1)]
        self.calls += 1
        return LLMResponse(text=text, model="fake-model", finish_reason="stop")


class FakeSession:
    """An in-memory session: a canned stdout per code string (default ``ok``)."""

    def __init__(self, outputs: Mapping[str, str] | None = None) -> None:
        self._outputs = dict(outputs or {})

    def run(self, code: str) -> ExecResult:
        return ExecResult(stdout=self._outputs.get(code, "ok"), stderr="", ok=True)

    def close(self) -> None:
        pass


class FakeExecutor:
    """Hands out :class:`FakeSession`s; records how many were started."""

    def __init__(self, outputs: Mapping[str, str] | None = None) -> None:
        self._outputs = dict(outputs or {})
        self.started = 0

    def start(
        self,
        datasets: tuple[Path, ...] = (),
        *,
        skills: Mapping[str, str] | None = None,
    ) -> Session:
        self.started += 1
        return FakeSession(self._outputs)


@pytest.fixture
def fake_llm() -> type[FakeLLM]:
    return FakeLLM


@pytest.fixture
def fake_executor() -> type[FakeExecutor]:
    return FakeExecutor
