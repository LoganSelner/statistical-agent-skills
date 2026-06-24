"""OpenAI-compatible LLM client + provider factory.

The harness talks to LLMs through OpenAI's chat-completions API. Two providers are
supported today and both speak that API, so they share **one** client and differ
only in base URL, key policy, and default model:

- ``edenai`` — the EdenAI gateway (``/v3``); ``model`` is the routed ``provider/model``
  string (e.g. ``"openai/gpt-4o"``), which doubles as the provenance id. Needs
  ``EDENAI_API_KEY``.
- ``ollama`` — a local Ollama server's OpenAI-compatible endpoint; ``model`` is the
  Ollama tag (e.g. ``"qwen2.5-coder:7b"``). Keyless.

A third provider, ``anthropic`` (Claude), uses the native Anthropic SDK rather than the
OpenAI-compatible path and lives in :mod:`.anthropic_client`; ``build_llm`` dispatches to
it. Adding it kept this module's OpenAI-compatible client untouched.

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

    provider: str = "edenai"  # "edenai" | "ollama" | "anthropic"
    model: str | None = None  # provider/model (edenai) or tag (ollama); None → default
    temperature: float = 0.0
    max_tokens: int = 2048
    base_url: str | None = None  # override the provider's default base URL
    request_timeout: float = 240.0  # per-request timeout (s); bounds a stalled call


@dataclass(frozen=True)
class _Provider:
    """A provider preset: where to reach it, how it authenticates, its default model."""

    base_url: str
    api_key_env: str | None  # None → keyless (a placeholder key is sent)
    default_model: str  # used when LLMConfig.model is None
    base_url_env: str | None = None  # optional env var that overrides base_url


PROVIDERS: dict[str, _Provider] = {
    "edenai": _Provider(
        "https://api.edenai.run/v3", "EDENAI_API_KEY", "openai/gpt-4o-mini"
    ),
    "ollama": _Provider(
        "http://localhost:11434/v1",
        None,
        "qwen2.5-coder:7b",
        base_url_env="OLLAMA_BASE_URL",
    ),
}

# Claude is reached through the native Anthropic SDK (not an OpenAI-compatible base
# URL), so build_llm dispatches it separately rather than via the PROVIDERS presets.
_ANTHROPIC_PROVIDER = "anthropic"
_ANTHROPIC_DEFAULT_MODEL = "claude-haiku-4-5"  # the experiment's frontier instrument


@runtime_checkable
class LLM(Protocol):
    """The narrow LLM interface the agent loop depends on (LLMClient satisfies it)."""

    @property
    def model(self) -> str: ...

    def complete(self, messages: list[Message]) -> LLMResponse: ...


class LLMClient:
    """Calls an OpenAI-compatible chat API and returns a neutral ``LLMResponse``.

    Construct via :func:`build_llm`, which resolves ``base_url``, the key, and the
    model per provider. ``client`` may be injected for testing; otherwise an
    ``openai.OpenAI`` is built against ``base_url``.
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
        # Bound a stalled call: an explicit timeout (the SDK default is 600s) and
        # max_retries=0 so `retry_transient` is the only retry controller — the SDK's
        # default of 2 retries would multiply a timed-out call past request_timeout.
        self._client = OpenAI(
            api_key=api_key or "ollama",
            base_url=base_url,
            timeout=self._config.request_timeout,
            max_retries=0,
        )

    @property
    def model(self) -> str:
        return self._config.model or ""

    @property
    def base_url(self) -> str | None:
        """The resolved endpoint — recorded in provenance (ROADMAP §9)."""
        return self._base_url

    @retry_transient(attempts=2)
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
            model=getattr(resp, "model", None) or self.model,
            finish_reason=choice.finish_reason or "",
            prompt_tokens=getattr(usage, "prompt_tokens", None),
            completion_tokens=getattr(usage, "completion_tokens", None),
        )


def build_llm(config: LLMConfig) -> LLM:
    """Construct the LLM client for ``config.provider`` — the single build path.

    Resolves the base URL (config override > provider env override > preset default),
    the model (config model > preset default), and the API key (the provider's env var,
    or a placeholder for keyless providers). Raises ``ValueError`` for an unknown
    provider or a missing required key. ``anthropic`` uses the native SDK and is built
    separately (no base URL).
    """
    if config.provider == _ANTHROPIC_PROVIDER:
        return _build_anthropic(config)

    preset = PROVIDERS.get(config.provider)
    if preset is None:
        known = sorted([*PROVIDERS, _ANTHROPIC_PROVIDER])
        raise ValueError(f"Unknown LLM provider '{config.provider}'. Known: {known}.")
    base_url = (
        config.base_url
        or (os.environ.get(preset.base_url_env) if preset.base_url_env else None)
        or preset.base_url
    )
    model = config.model or preset.default_model
    if preset.api_key_env:
        api_key = os.environ.get(preset.api_key_env, "")
        if not api_key:
            raise ValueError(
                f"{preset.api_key_env} is required for provider "
                f"'{config.provider}'. Set it in .env or your environment."
            )
    else:
        api_key = "ollama"  # placeholder; keyless providers ignore it
    resolved = config.model_copy(update={"model": model})
    return LLMClient(resolved, base_url=base_url, api_key=api_key)


def _build_anthropic(config: LLMConfig) -> LLM:
    """Construct the native Claude client (provider ``anthropic``).

    Requires ``ANTHROPIC_API_KEY``; defaults the model to the experiment's instrument
    (``claude-haiku-4-5``) when the config omits it. Imported lazily so the rest of the
    harness never depends on the ``anthropic`` SDK.
    """
    from statskills.agent.anthropic_client import AnthropicClient

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise ValueError(
            "ANTHROPIC_API_KEY is required for provider 'anthropic'. "
            "Set it in .env or your environment."
        )
    model = config.model or _ANTHROPIC_DEFAULT_MODEL
    resolved = config.model_copy(update={"model": model})
    return AnthropicClient(resolved, api_key=api_key)


def resolve_llm_config(
    block: dict[str, Any] | None,
    *,
    provider: str | None = None,
    model: str | None = None,
) -> LLMConfig:
    """Merge a config ``llm:`` block with CLI overrides into an :class:`LLMConfig`.

    Overriding the provider replaces the provider-scoped fields (``model``,
    ``base_url``): a model id is meaningless across providers, so switching providers
    does not carry the old provider's model — the new provider's default applies (or an
    explicit ``model``). This mirrors the config loader's impl-selector replacement so
    the CLI and YAML behave the same way.
    """
    data: dict[str, Any] = dict(block or {})
    if provider and provider != data.get("provider"):
        data.pop("model", None)
        data.pop("base_url", None)
    if provider:
        data["provider"] = provider
    if model:
        data["model"] = model
    return LLMConfig(**data)
