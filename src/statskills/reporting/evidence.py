"""The deterministic evidence base a report must cite (ROADMAP §10).

A report's claims point at trajectory *steps*; this extracts the citable steps — the
ones that ran code and printed an observation. ``final``/``no_action`` steps carry no
computed value, so they are not citable. Pure and stdlib-only: it reads the saved
trajectory dict, never the agent.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ObservedStep:
    """One executed code step and the output it printed — a citable observation."""

    index: int  # the step's own trajectory index (so a report's citations line up)
    code: str
    observation: str


def observed_steps(trajectory: Mapping[str, Any]) -> list[ObservedStep]:
    """The code steps (with their printed observations) — the citable evidence base."""
    steps: list[ObservedStep] = []
    for position, step in enumerate(trajectory.get("steps", ())):
        code = step.get("code")
        if not code:  # final / no_action steps ran no code
            continue
        steps.append(
            ObservedStep(
                index=int(step.get("index", position)),
                code=str(code),
                observation=str(step.get("observation") or ""),
            )
        )
    return steps
