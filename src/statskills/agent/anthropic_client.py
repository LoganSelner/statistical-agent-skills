"""Native Anthropic (Claude) LLM client — the frontier provider.

The OpenAI-compatible ``LLMClient`` covers EdenAI and Ollama, but Claude is used
through the **official Anthropic SDK** (not an OpenAI-compatible shim) so its
behaviour is faithful — the point of adding it is to test agent skills on a model
that can actually exhibit the phenomenon. This is a second implementation of the
same narrow :class:`~statskills.agent.llm.LLM` protocol (``model`` + ``complete``);
``build_llm`` dispatches here for ``provider="anthropic"``.

The Messages API differs from chat-completions in two ways this adapter bridges:
the system prompt is a top-level ``system=`` parameter (not a role in ``messages``),
and the response is a list of content blocks (the text blocks are flattened).
"""

from __future__ import annotations

from typing import Any

from statskills.agent.llm import LLMConfig
from statskills.core.retry import retry_transient
from statskills.core.types import LLMResponse, Message


class AnthropicClient:
    """Calls Claude via the Anthropic Messages API; returns a neutral ``LLMResponse``.

    Construct via :func:`~statskills.agent.llm.build_llm`. ``client`` may be injected
    for testing; otherwise an ``anthropic.Anthropic`` is built. ``max_retries=0`` keeps
    :func:`retry_transient` as the only retry controller, and ``timeout`` bounds a
    stalled call — the same policy as the OpenAI client.
    """

    def __init__(
        self,
        config: LLMConfig,
        *,
        api_key: str | None = None,
        client: Any | None = None,
    ) -> None:
        self._config = config
        self._client: Any
        if client is not None:
            self._client = client
            return
        from anthropic import Anthropic

        self._client = Anthropic(
            api_key=api_key,
            timeout=config.request_timeout,
            max_retries=0,
        )

    @property
    def model(self) -> str:
        return self._config.model or ""

    @retry_transient(attempts=2)
    def _create(self, system: str | None, messages: list[Message]) -> Any:
        kwargs: dict[str, Any] = {
            "model": self._config.model,
            "messages": messages,
            "max_tokens": self._config.max_tokens,
            "temperature": self._config.temperature,
        }
        if system is not None:
            kwargs["system"] = system
        return self._client.messages.create(**kwargs)

    def complete(self, messages: list[Message]) -> LLMResponse:
        """Run one completion. Wraps transient retries; raises on hard failure."""
        system, conversation = _split_system(messages)
        try:
            resp = self._create(system, conversation)
        except Exception as e:
            raise RuntimeError(
                f"anthropic call failed for model '{self._config.model}': {e}"
            ) from e

        text = "".join(
            getattr(block, "text", "")
            for block in resp.content
            if getattr(block, "type", None) == "text"
        )
        usage = getattr(resp, "usage", None)
        return LLMResponse(
            text=text,
            model=getattr(resp, "model", None) or self.model,
            finish_reason=getattr(resp, "stop_reason", None) or "",
            prompt_tokens=getattr(usage, "input_tokens", None),
            completion_tokens=getattr(usage, "output_tokens", None),
        )


def _split_system(messages: list[Message]) -> tuple[str | None, list[Message]]:
    """Lift system-role messages into a single ``system`` string; return (system, rest).

    The Messages API takes the system prompt as a top-level parameter, not as a role
    in the ``messages`` array. Our harness emits exactly one leading system message; we
    join any system messages defensively and return ``None`` when there are none (so
    the kwarg is omitted rather than sent empty).
    """
    system_parts = [m["content"] for m in messages if m["role"] == "system"]
    conversation = [m for m in messages if m["role"] != "system"]
    system = "\n\n".join(system_parts) if system_parts else None
    return system, conversation
