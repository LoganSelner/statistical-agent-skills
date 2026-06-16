"""Tests for the EdenAI LLM client (with an injected fake SDK client)."""

from __future__ import annotations

from typing import Any

import pytest

from statskills.agent.llm import LLMClient, LLMConfig
from statskills.core.types import Message


class _FakeMessage:
    def __init__(self, content: str | None) -> None:
        self.content = content


class _FakeChoice:
    def __init__(self, content: str | None, finish_reason: str) -> None:
        self.message = _FakeMessage(content)
        self.finish_reason = finish_reason


class _FakeUsage:
    def __init__(self, prompt: int, completion: int) -> None:
        self.prompt_tokens = prompt
        self.completion_tokens = completion


class _FakeCompletion:
    def __init__(
        self,
        content: str | None,
        *,
        model: str = "openai/gpt-4o-mini",
        usage: _FakeUsage | None = None,
        finish_reason: str = "stop",
    ) -> None:
        self.choices = [_FakeChoice(content, finish_reason)]
        self.model = model
        self.usage = usage


class _FakeCompletions:
    def __init__(self, response: _FakeCompletion) -> None:
        self._response = response
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> _FakeCompletion:
        self.calls.append(kwargs)
        return self._response


class _FakeOpenAI:
    def __init__(self, response: _FakeCompletion) -> None:
        self.chat = type("_Chat", (), {"completions": _FakeCompletions(response)})()


def test_complete_extracts_text_usage_and_forwards_params():
    fake = _FakeOpenAI(
        _FakeCompletion("hello", model="openai/gpt-4o", usage=_FakeUsage(10, 5))
    )
    client = LLMClient(
        LLMConfig(model="openai/gpt-4o", temperature=0.0, max_tokens=128),
        client=fake,
    )
    msgs: list[Message] = [{"role": "user", "content": "hi"}]

    resp = client.complete(msgs)

    assert resp.text == "hello"
    assert resp.model == "openai/gpt-4o"  # routed id echoed by the gateway
    assert resp.prompt_tokens == 10
    assert resp.completion_tokens == 5

    call = fake.chat.completions.calls[0]
    assert call["model"] == "openai/gpt-4o"
    assert call["temperature"] == 0.0
    assert call["max_tokens"] == 128
    assert call["messages"] == msgs


def test_complete_handles_missing_usage_and_content():
    fake = _FakeOpenAI(_FakeCompletion(None, usage=None))
    client = LLMClient(client=fake)
    resp = client.complete([{"role": "user", "content": "hi"}])
    assert resp.text == ""  # None content normalized to ""
    assert resp.prompt_tokens is None
    assert resp.completion_tokens is None


def test_missing_api_key_raises(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("EDENAI_API_KEY", raising=False)
    with pytest.raises(ValueError, match="EDENAI_API_KEY"):
        LLMClient()
