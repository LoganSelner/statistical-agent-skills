"""CodeAct action protocol — parse one model turn into the next action.

The agent's action space is executable Python (CodeAct, arXiv 2402.01030): each
turn the model either runs a fenced ``python`` code block or declares a final
answer with a ``FINAL ANSWER:`` marker. This module is the harness-side parser —
deliberately independent of any provider's tool-calling so the loop is robust
behind the EdenAI gateway regardless of sub-provider (ROADMAP §6).

Precedence: a ``FINAL ANSWER:`` marker wins (the model is signalling it is done,
even if it sloppily also included code); otherwise the first code block is the
action; otherwise there is nothing to act on (``None``) and the loop re-prompts.
"""

from __future__ import annotations

from dataclasses import dataclass
import re

# A fenced code block: ```python\n ... \n```  (language tag optional).
_CODE_BLOCK = re.compile(
    r"```[ \t]*(?:python|py)?[ \t]*\r?\n(.*?)```",
    re.DOTALL | re.IGNORECASE,
)
# A final-answer marker through the end of the message (answers may be multiline).
_FINAL_ANSWER = re.compile(r"FINAL ANSWER:\s*(.*)", re.DOTALL | re.IGNORECASE)


@dataclass(frozen=True)
class CodeAction:
    """Run ``code`` in the sandbox kernel, then feed the observation back."""

    code: str


@dataclass(frozen=True)
class FinalAnswer:
    """The agent's closed-form answer; ends the loop."""

    answer: str


Action = CodeAction | FinalAnswer | None


def parse_action(text: str) -> Action:
    """Parse one assistant turn into a :data:`Action`.

    Returns a :class:`FinalAnswer` if the turn declares one, else a
    :class:`CodeAction` for the first code block, else ``None``.
    """
    final = _FINAL_ANSWER.search(text)
    if final:
        return FinalAnswer(answer=final.group(1).strip())

    for block in _CODE_BLOCK.findall(text):
        code = block.strip()
        if code:
            return CodeAction(code=code)

    return None
