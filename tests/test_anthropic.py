"""Tests for the native Anthropic (Claude) client + the build_llm dispatch."""

from __future__ import annotations

from typing import Any

import pytest

from statskills.agent.anthropic_client import AnthropicClient
from statskills.agent.llm import LLMConfig, build_llm
from statskills.core.types import Message

# --- fakes for the injected Anthropic SDK client --------------------------------


class _FakeBlock:
    def __init__(self, text: str, kind: str = "text") -> None:
        self.type = kind
        self.text = text


class _FakeUsage:
    def __init__(self, input_tokens: int, output_tokens: int) -> None:
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens


class _FakeMessage:
    def __init__(
        self,
        content: list[_FakeBlock],
        *,
        model: str = "claude-haiku-4-5",
        usage: _FakeUsage | None = None,
        stop_reason: str = "end_turn",
    ) -> None:
        self.content = content
        self.model = model
        self.usage = usage
        self.stop_reason = stop_reason


class _FakeMessages:
    def __init__(self, response: _FakeMessage) -> None:
        self._response = response
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> _FakeMessage:
        self.calls.append(kwargs)
        return self._response


class _FakeAnthropic:
    def __init__(self, response: _FakeMessage) -> None:
        self.messages = _FakeMessages(response)


# --- complete(): system lifting + content flattening ----------------------------


def test_complete_lifts_system_and_parses_response() -> None:
    fake = _FakeAnthropic(_FakeMessage([_FakeBlock("hello")], usage=_FakeUsage(12, 7)))
    client = AnthropicClient(
        LLMConfig(provider="anthropic", model="claude-haiku-4-5", max_tokens=128),
        client=fake,
    )
    msgs: list[Message] = [
        {"role": "system", "content": "SYS"},
        {"role": "user", "content": "hi"},
    ]

    resp = client.complete(msgs)

    assert resp.text == "hello"
    assert resp.model == "claude-haiku-4-5"
    assert resp.finish_reason == "end_turn"
    assert resp.prompt_tokens == 12 and resp.completion_tokens == 7

    call = fake.messages.calls[0]
    # The system message is lifted out of `messages` into the top-level `system=`.
    assert call["system"] == "SYS"
    assert call["messages"] == [{"role": "user", "content": "hi"}]
    assert call["model"] == "claude-haiku-4-5"
    assert call["max_tokens"] == 128 and call["temperature"] == 0.0


def test_complete_flattens_text_blocks_and_omits_absent_system() -> None:
    fake = _FakeAnthropic(
        _FakeMessage(
            [_FakeBlock("a"), _FakeBlock("ignored", kind="thinking"), _FakeBlock("b")],
            usage=None,
        )
    )
    client = AnthropicClient(LLMConfig(provider="anthropic", model="m"), client=fake)

    resp = client.complete([{"role": "user", "content": "x"}])

    assert resp.text == "ab"  # text blocks joined; non-text skipped
    assert resp.prompt_tokens is None and resp.completion_tokens is None
    assert "system" not in fake.messages.calls[0]  # no system message → kwarg omitted


# --- build_llm dispatch ---------------------------------------------------------


def test_build_llm_anthropic_returns_client_and_default_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    llm = build_llm(LLMConfig(provider="anthropic"))
    assert isinstance(llm, AnthropicClient)
    assert llm.model == "claude-haiku-4-5"  # the experiment's default instrument


def test_build_llm_anthropic_honors_explicit_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    llm = build_llm(LLMConfig(provider="anthropic", model="claude-opus-4-8"))
    assert llm.model == "claude-opus-4-8"


def test_build_llm_anthropic_missing_key_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
        build_llm(LLMConfig(provider="anthropic"))
