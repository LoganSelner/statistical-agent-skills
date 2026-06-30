"""Live step streaming via a tap over the injected LLM + sandbox (ROADMAP §11).

The agent (``statskills.agent``) is the system under test and stays **untouched** — its
loop builds a trajectory internally and exposes no per-step hook. But the loop takes its
:class:`~statskills.agent.llm.LLM` and :class:`~statskills.sandbox.base.Executor` by
*injection*, so we observe progress from the outside: a :class:`RunTap` plus thin
pass-through wrappers that emit a :class:`StepEvent` on each ``llm.complete()`` /
``session.run()`` and otherwise return the inner result unchanged. The wrapped run
therefore produces a **byte-for-byte identical** trajectory (verified in the tests); the
web layer is a pure consumer riding the existing dependency-injection seam.

Turn classification reuses the harness's own ``parse_action`` (code vs final answer vs
neither), so the stream mirrors exactly what the loop does with each turn. The queue is
thread-safe: the agent runs on a worker thread that emits, while the SSE endpoint drains
from the event loop (see :mod:`statskills_api.app`).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
import queue
from typing import Any

from statskills.agent.action import CodeAction, FinalAnswer, parse_action
from statskills.agent.context import render_observation
from statskills.agent.llm import LLM
from statskills.core.types import LLMResponse, Message
from statskills.sandbox.base import ExecResult, Executor, Session


@dataclass(frozen=True)
class StepEvent:
    """One streamed event from a run — a model turn or its sandbox observation.

    ``kind`` is ``"code"`` (the turn ran code), ``"final"`` (declared the answer),
    ``"thought"`` (a turn with neither — the loop re-prompts), ``"observation"`` (a code
    cell's output), ``"status"`` (a lifecycle note, e.g. composing the report), or
    ``"error"``. ``index`` is the loop turn (aligned with the trajectory step index)
    when known. Optional fields are populated per kind.
    """

    kind: str
    index: int | None = None
    text: str | None = None
    code: str | None = None
    observation: str | None = None
    ok: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        """JSON-serialisable payload for SSE; omits unset fields."""
        data: dict[str, Any] = {"kind": self.kind}
        for field in ("index", "text", "code", "observation", "ok"):
            value = getattr(self, field)
            if value is not None:
                data[field] = value
        return data


# Sentinel placed on the queue when the run is finished (success or failure).
_DONE = None


class RunTap:
    """A thread-safe sink the wrappers emit to and the SSE endpoint drains.

    The producer (the worker thread running the agent) calls :meth:`emit` per step and
    :meth:`close` once; the consumer calls :meth:`get` until it returns ``None`` (the
    end sentinel), treating a :class:`queue.Empty` timeout as "still running" (send a
    keep-alive).
    """

    def __init__(self) -> None:
        self._queue: queue.Queue[StepEvent | None] = queue.Queue()

    def emit(self, event: StepEvent) -> None:
        self._queue.put(event)

    def close(self) -> None:
        """Signal end-of-stream exactly once."""
        self._queue.put(_DONE)

    def get(self, timeout: float) -> StepEvent | None:
        """Next event, or ``None`` at end of stream. Raises :class:`queue.Empty` on
        timeout so the caller can emit a keep-alive without blocking the event loop."""
        return self._queue.get(timeout=timeout)


class TappingLLM:
    """Wraps an :class:`LLM`, emitting a step event per completion (pass-through).

    Behaviour is identical to ``inner`` — it returns ``inner``'s response unchanged; it
    only classifies the turn (the same way the loop will) and emits an event. The turn
    counter mirrors the loop's per-iteration step index.
    """

    def __init__(self, inner: LLM, tap: RunTap) -> None:
        self._inner = inner
        self._tap = tap
        self._index = 0

    @property
    def model(self) -> str:
        return self._inner.model

    def complete(self, messages: list[Message]) -> LLMResponse:
        resp = self._inner.complete(messages)
        index = self._index
        self._index += 1
        action = parse_action(resp.text)
        if isinstance(action, CodeAction):
            self._tap.emit(
                StepEvent(kind="code", index=index, text=resp.text, code=action.code)
            )
        elif isinstance(action, FinalAnswer):
            self._tap.emit(StepEvent(kind="final", index=index, text=action.answer))
        else:
            self._tap.emit(StepEvent(kind="thought", index=index, text=resp.text))
        return resp


class TappingSession:
    """Wraps a :class:`Session`, emitting an observation per run (pass-through)."""

    def __init__(self, inner: Session, tap: RunTap) -> None:
        self._inner = inner
        self._tap = tap

    def run(self, code: str) -> ExecResult:
        result = self._inner.run(code)
        self._tap.emit(
            StepEvent(
                kind="observation",
                observation=render_observation(result),
                ok=result.ok,
            )
        )
        return result

    def close(self) -> None:
        self._inner.close()


class TappingExecutor:
    """Wraps an :class:`Executor` so its sessions emit observations (pass-through)."""

    def __init__(self, inner: Executor, tap: RunTap) -> None:
        self._inner = inner
        self._tap = tap

    def start(
        self,
        datasets: tuple[Path, ...] = (),
        *,
        skills: Mapping[str, str] | None = None,
    ) -> Session:
        return TappingSession(self._inner.start(datasets, skills=skills), self._tap)
