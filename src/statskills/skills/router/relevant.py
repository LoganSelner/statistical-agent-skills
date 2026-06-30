"""Relevant router — inject only a task's relevant skill(s) (ROADMAP §4 dose-response).

The oracle "relevant skills only" condition: it maps a task's ``concepts`` to the
skill(s) that address them and returns just those, so an injected payload carries no
irrelevant skills. The contrast with
:class:`~statskills.skills.router.forced.ForcedRouter` (all skills) is the injection
**dose-response** — does irrelevant-skill payload distract? The map is the
experimenter's relevance judgement (the traps were authored knowing the target
procedure), so it is deterministic and reproducible — no semantic matching.
``description_match`` (learned relevance) remains a later drop-in.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from statskills.core.registry import registry
from statskills.skills.schema import Skill

if TYPE_CHECKING:
    from statskills.skills.library import SkillLibrary
    from statskills.tasks.schema import Task

# Concept (task vocabulary) -> the skill(s) that address it (library vocabulary),
# grounded in each skill's own description. The two general skills
# (effect-sizes-and-intervals, compute-dont-fabricate) intentionally map to nothing:
# they flip no authored trap, so "relevant only" correctly sheds them along with the
# non-matching specific skills — that shed payload is the distractor dose.
_CONCEPT_SKILLS: dict[str, frozenset[str]] = {
    "correlation": frozenset(
        {"hypothesis-test-selection", "parametric-assumption-checks"}
    ),
    "two_sample_test": frozenset({"hypothesis-test-selection"}),
    "equal_variance": frozenset({"parametric-assumption-checks"}),
    "paired": frozenset({"hypothesis-test-selection"}),
    "normality": frozenset({"parametric-assumption-checks"}),
    "multiple_comparisons": frozenset({"multiple-comparison-correction"}),
    "regression": frozenset({"regression-diagnostics"}),
    "confounding": frozenset({"regression-diagnostics"}),
    "heteroskedasticity": frozenset({"regression-diagnostics"}),
    "influence": frozenset({"regression-diagnostics"}),
    "nonlinearity": frozenset({"regression-diagnostics"}),
}


@registry.register("router", "relevant")
class RelevantRouter:
    """Selects only the skills a task's concepts map to (oracle relevance)."""

    def select(self, task: Task, library: SkillLibrary) -> list[Skill]:
        wanted = {
            name
            for concept in task.concepts
            for name in _CONCEPT_SKILLS.get(concept, ())
        }
        return [skill for skill in library if skill.name in wanted]
