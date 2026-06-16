"""OpenAI-compatible LLM client + provider factory.

The harness talks to LLMs through OpenAI's chat-completions API. Two providers are
supported today and both speak that API, so they share **one** client and differ
only in base URL and key policy:

- ``edenai`` — the EdenAI gateway (``/v3``); ``model`` is the routed ``provider/model``
  string (e.g. ``"openai/gpt-4o"``), which doubles as the provenance id. Needs
  ``EDENAI_API_KEY``.
- ``ollama`` — a local Ollama server's OpenAI-compatible endpoint; ``model`` is the
  Ollama tag (e.g. ``"qwen2.5-coder:7b"``). Keyless.

Provider-agnostic above this module: the rest of the harness imports the :class:`LLM`
protocol, :func:`build_llm`, and the neutral message/response types — never ``openai``.
The action protocol is harness-parsed code (CodeAct), so the client never depends on
native tool-calling or structured-output support (ROADMAP §6, §6.1, §9).
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Any, Protocol, cast, runtime_checkable

from pydantic import BaseModel

from statskills.core.retry import retry_transient
from statskills.core.types import LLMResponse, Message


class LLMConfig(BaseModel):
    """Configuration for an OpenAI-compatible LLM."""

    provider: str = "edenai"  # "edenai" | "ollama"
    model: str = "openai/gpt-4o-mini"  # provider/model (edenai) or tag (ollama)
    temperature: float = 0.0
    max_tokens: int = 2048
    base_url: str | None = None  # override the provider's default base URL


@dataclass(frozen=True)
class _Provider:
    """A provider preset: where to reach it and how it authenticates."""

    base_url: str
    api_key_env: str | None  # None → keyless (a placeholder key is sent)
    base_url_env: str | None = None  # optional env var that overrides base_url


PROVIDERS: dict[str, _Provider] = {
    "edenai": _Provider("https://api.edenai.run/v3", "EDENAI_API_KEY"),
    "ollama": _Provider(
        "http://localhost:11434/v1", None, base_url_env="OLLAMA_BASE_URL"
    ),
}


@runtime_checkable
class LLM(Protocol):
    """The narrow LLM interface the agent loop depends on (LLMClient satisfies it)."""

    @property
    def model(self) -> str: ...

    def complete(self, messages: list[Message]) -> LLMResponse: ...


class LLMClient:
    """Calls an OpenAI-compatible chat API and returns a neutral ``LLMResponse``.

    Construct via :func:`build_llm`, which resolves ``base_url`` and the key per
    provider. ``client`` may be injected for testing; otherwise an ``openai.OpenAI``
    is built against ``base_url``.
    """

    def __init__(
        self,
        config: LLMConfig | None = None,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        client: Any | None = None,
    ) -> None:
        self._config = config or LLMConfig()
        self._base_url = base_url
        if client is not None:
            self._client = client
            return
        if not base_url:
            raise ValueError("base_url is required; construct via build_llm().")
        from openai import OpenAI

        # Keyless backends (Ollama) ignore the key, but the SDK requires a value.
        self._client = OpenAI(api_key=api_key or "ollama", base_url=base_url)

    @property
    def model(self) -> str:
        return self._config.model

    @property
    def base_url(self) -> str | None:
        """The resolved endpoint — recorded in provenance (ROADMAP §9)."""
        return self._base_url

    @retry_transient
    def _create(self, messages: list[Message]) -> Any:
        return self._client.chat.completions.create(
            model=self._config.model,
            messages=cast("Any", messages),
            temperature=self._config.temperature,
            max_tokens=self._config.max_tokens,
        )

    def complete(self, messages: list[Message]) -> LLMResponse:
        """Run one completion. Wraps transient retries; raises on hard failure."""
        try:
            resp = self._create(messages)
        except Exception as e:
            raise RuntimeError(
                f"{self._config.provider} call failed for model "
                f"'{self._config.model}': {e}"
            ) from e

        choice = resp.choices[0]
        usage = getattr(resp, "usage", None)
        return LLMResponse(
            text=choice.message.content or "",
            model=getattr(resp, "model", None) or self._config.model,
            finish_reason=choice.finish_reason or "",
            prompt_tokens=getattr(usage, "prompt_tokens", None),
            completion_tokens=getattr(usage, "completion_tokens", None),
        )


def build_llm(config: LLMConfig) -> LLM:
    """Construct the LLM client for ``config.provider`` — the single build path.

    Resolves the base URL (config override > provider env override > preset default)
    and the API key (from the provider's env var, or a placeholder for keyless
    providers). Raises ``ValueError`` for an unknown provider or a missing required key.
    """
    preset = PROVIDERS.get(config.provider)
    if preset is None:
        raise ValueError(
            f"Unknown LLM provider '{config.provider}'. Known: {sorted(PROVIDERS)}."
        )
    base_url = (
        config.base_url
        or (os.environ.get(preset.base_url_env) if preset.base_url_env else None)
        or preset.base_url
    )
    if preset.api_key_env:
        api_key = os.environ.get(preset.api_key_env, "")
        if not api_key:
            raise ValueError(
                f"{preset.api_key_env} is required for provider "
                f"'{config.provider}'. Set it in .env or your environment."
            )
    else:
        api_key = "ollama"  # placeholder; keyless providers ignore it
    return LLMClient(config, base_url=base_url, api_key=api_key)
