"""EdenAI LLM client — the OpenAI-compatible ``/v3`` endpoint via the ``openai`` SDK.

Provider-agnostic above this module: the rest of the harness imports
:class:`LLMClient` and the neutral :class:`~statskills.core.types.Message` /
:class:`~statskills.core.types.LLMResponse` types, never ``openai``. ``model`` is
the EdenAI-routed ``provider/model`` string (e.g. ``"openai/gpt-4o"``), which
doubles as the provenance identifier (ROADMAP §6.1, §9). The action protocol is
harness-parsed code (CodeAct), so this client never depends on native
tool-calling or structured-output support across EdenAI's sub-providers.
"""

from __future__ import annotations

import os
from typing import Any, cast

from pydantic import BaseModel

from statskills.core.retry import retry_transient
from statskills.core.types import LLMResponse, Message

EDENAI_BASE_URL = "https://api.edenai.run/v3"


class LLMConfig(BaseModel):
    """Configuration for the EdenAI-routed LLM."""

    model: str = "openai/gpt-4o-mini"  # provider/model — set to one your key enables
    temperature: float = 0.0
    max_tokens: int = 2048


class LLMClient:
    """Calls EdenAI's chat completions and returns a neutral ``LLMResponse``.

    ``client`` may be injected for testing; otherwise an ``openai.OpenAI`` is
    constructed against the EdenAI base URL using ``EDENAI_API_KEY``.
    """

    def __init__(
        self,
        config: LLMConfig | None = None,
        *,
        api_key: str | None = None,
        client: Any | None = None,
    ) -> None:
        self._config = config or LLMConfig()
        if client is not None:
            self._client = client
            return
        key = api_key or os.environ.get("EDENAI_API_KEY", "")
        if not key:
            raise ValueError(
                "EDENAI_API_KEY is required. Set it in .env or your environment."
            )
        from openai import OpenAI

        self._client = OpenAI(api_key=key, base_url=EDENAI_BASE_URL)

    @property
    def model(self) -> str:
        return self._config.model

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
                f"EdenAI call failed for model '{self._config.model}': {e}"
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
