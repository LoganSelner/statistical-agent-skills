"""Tests for the OpenAI-compatible LLM client and the provider factory."""

from __future__ import annotations

from typing import Any

import pytest

from statskills.agent.llm import LLMClient, LLMConfig, build_llm, resolve_llm_config
from statskills.core.types import Message

# --- fakes for the injected SDK client ------------------------------------------


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


# --- complete() is provider-agnostic --------------------------------------------


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
    assert resp.model == "openai/gpt-4o"
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
    assert resp.text == ""
    assert resp.prompt_tokens is None
    assert resp.completion_tokens is None


# --- build_llm factory (no network: openai.OpenAI() does not connect) ------------


def test_build_llm_edenai_resolves_base_url(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("EDENAI_API_KEY", "test-key")
    llm = build_llm(LLMConfig(provider="edenai"))
    assert isinstance(llm, LLMClient)
    assert llm.base_url == "https://api.edenai.run/v3"


def test_build_llm_edenai_missing_key_raises(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("EDENAI_API_KEY", raising=False)
    with pytest.raises(ValueError, match="EDENAI_API_KEY"):
        build_llm(LLMConfig(provider="edenai"))


def test_build_llm_ollama_is_keyless_with_default_base_url(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    monkeypatch.delenv("EDENAI_API_KEY", raising=False)  # not needed for ollama
    llm = build_llm(LLMConfig(provider="ollama", model="qwen2.5-coder:7b"))
    assert isinstance(llm, LLMClient)
    assert llm.base_url == "http://localhost:11434/v1"
    assert llm.model == "qwen2.5-coder:7b"


def test_build_llm_base_url_precedence(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://env-host:11434/v1")
    # config base_url wins over the env override...
    llm = build_llm(LLMConfig(provider="ollama", base_url="http://cfg-host:11434/v1"))
    assert isinstance(llm, LLMClient)
    assert llm.base_url == "http://cfg-host:11434/v1"
    # ...and the env override wins over the preset default.
    llm2 = build_llm(LLMConfig(provider="ollama"))
    assert isinstance(llm2, LLMClient)
    assert llm2.base_url == "http://env-host:11434/v1"


def test_build_llm_unknown_provider_raises():
    with pytest.raises(ValueError, match="Unknown LLM provider"):
        build_llm(LLMConfig(provider="nope"))


# --- provider default model + CLI override semantics ----------------------------


def test_build_llm_resolves_provider_default_model(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    llm = build_llm(LLMConfig(provider="ollama"))  # model omitted
    assert isinstance(llm, LLMClient)
    assert llm.model == "qwen2.5-coder:7b"


def test_build_llm_edenai_default_model(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("EDENAI_API_KEY", "k")
    llm = build_llm(LLMConfig(provider="edenai"))
    assert isinstance(llm, LLMClient)
    assert llm.model == "openai/gpt-4o-mini"


def test_resolve_llm_config_no_override_keeps_block():
    lc = resolve_llm_config(
        {"provider": "edenai", "model": "openai/gpt-4o", "temperature": 0.3}
    )
    assert lc.provider == "edenai"
    assert lc.model == "openai/gpt-4o"
    assert lc.temperature == 0.3


def test_resolve_llm_config_provider_switch_drops_old_model():
    # The documented footgun: `--provider ollama` over the EdenAI default config.
    lc = resolve_llm_config(
        {"provider": "edenai", "model": "openai/gpt-4o-mini", "temperature": 0.0},
        provider="ollama",
    )
    assert lc.provider == "ollama"
    assert lc.model is None  # old provider's model dropped → build_llm defaults it
    assert lc.temperature == 0.0  # shared knob kept


def test_resolve_llm_config_provider_switch_honors_explicit_model():
    lc = resolve_llm_config(
        {"provider": "edenai", "model": "openai/gpt-4o-mini"},
        provider="ollama",
        model="llama3.1:8b",
    )
    assert lc.provider == "ollama"
    assert lc.model == "llama3.1:8b"


def test_resolve_llm_config_model_only_override_same_provider():
    lc = resolve_llm_config({"provider": "edenai", "model": "a"}, model="b")
    assert lc.provider == "edenai"
    assert lc.model == "b"


# --- request timeout (bounds a stalled call) ------------------------------------


def test_request_timeout_default_and_resolved_from_config():
    assert LLMConfig().request_timeout == 240.0
    resolved = resolve_llm_config({"provider": "ollama", "request_timeout": 30})
    assert resolved.request_timeout == 30.0


def test_request_timeout_and_no_sdk_retries_passed_to_client(
    monkeypatch: pytest.MonkeyPatch,
):
    captured: dict[str, Any] = {}

    class _CapturingOpenAI:
        def __init__(self, **kwargs: Any) -> None:
            captured.update(kwargs)

    monkeypatch.setattr("openai.OpenAI", _CapturingOpenAI)
    LLMClient(LLMConfig(request_timeout=42.0), base_url="http://x/v1")
    assert captured["timeout"] == 42.0
    # retry_transient is the sole retry controller; the SDK must not also retry.
    assert captured["max_retries"] == 0


def test_provider_switch_then_build_uses_ollama_default(
    monkeypatch: pytest.MonkeyPatch,
):
    # End-to-end: the documented `--provider ollama` path no longer sends the EdenAI id.
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    lc = resolve_llm_config(
        {"provider": "edenai", "model": "openai/gpt-4o-mini"}, provider="ollama"
    )
    llm = build_llm(lc)
    assert llm.model == "qwen2.5-coder:7b"
