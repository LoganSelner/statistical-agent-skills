"""Shared data types — the contracts between harness layers.

The message schema is the neutral, OpenAI-style shape the LLM client speaks.
Because the agent acts by emitting **code** (CodeAct, ROADMAP §6) rather than
provider tool-calls, there are no tool-call types here — a turn is plain text.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypedDict

Role = Literal["system", "user", "assistant"]


class Message(TypedDict):
    """A single chat message in the neutral OpenAI-style schema."""

    role: Role
    content: str


@dataclass(frozen=True)
class LLMResponse:
    """One completion from the LLM client.

    ``model`` is the exact EdenAI-routed ``provider/model`` identifier echoed by
    the gateway — recorded for provenance (ROADMAP §9). Token counts are
    best-effort (``None`` when the sub-provider omits them).
    """

    text: str
    model: str
    finish_reason: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
