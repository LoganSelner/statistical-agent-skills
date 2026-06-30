"""Tests for skill routers (forced, relevant)."""

from __future__ import annotations

from pathlib import Path

from statskills.core.registry import registry
import statskills.skills as skills_pkg
from statskills.skills.library import load_library
from statskills.skills.router import get_router
from statskills.tasks.authored.regression_trap_tasks import load_regression_trap_tasks
from statskills.tasks.authored.trap_tasks import load_trap_tasks
from statskills.tasks.schema import Task

FIXTURES = Path(__file__).parent / "fixtures" / "skills"
STATS_LIBRARY = Path(skills_pkg.__file__).parent / "library" / "statistics"


def test_forced_router_is_registered():
    assert registry.is_registered("router", "forced")


def test_forced_router_selects_whole_library():
    selected = get_router("forced").select(
        Task(id="t", prompt="p"), load_library(FIXTURES)
    )
    assert {s.name for s in selected} == {"another-skill", "sample-skill"}


def test_relevant_router_is_registered():
    assert registry.is_registered("router", "relevant")


def _all_authored_traps() -> list[Task]:
    return [*load_trap_tasks(), *load_regression_trap_tasks()]


def test_relevant_selects_the_oracle_skill_per_trap():
    lib = load_library(STATS_LIBRARY)
    relevant = get_router("relevant")
    by_id = {t.id: t for t in _all_authored_traps()}

    def names(task_id: str) -> set[str]:
        return {s.name for s in relevant.select(by_id[task_id], lib)}

    # Every regression trap maps to exactly the regression skill.
    for tid in (
        "reg-confounding",
        "reg-heteroskedasticity",
        "reg-influence",
        "reg-nonlinearity",
    ):
        assert names(tid) == {"regression-diagnostics"}
    assert names("trap-multiple-comparisons") == {"multiple-comparison-correction"}
    assert names("trap-welch") == {
        "hypothesis-test-selection",
        "parametric-assumption-checks",
    }
    assert names("trap-paired") == {"hypothesis-test-selection"}


def test_relevant_is_a_nonempty_subset_of_forced_for_every_trap():
    lib = load_library(STATS_LIBRARY)
    forced, relevant = get_router("forced"), get_router("relevant")
    full = {s.name for s in forced.select(Task(id="t", prompt="p"), lib)}
    for task in _all_authored_traps():
        rel = {s.name for s in relevant.select(task, lib)}
        assert rel, f"{task.id} maps to no relevant skill (unmapped concept?)"
        assert rel < full  # strict subset — relevant always sheds some distractors


def test_relevant_never_selects_the_general_skills():
    # The two non-trap-specific skills are distractors for every trap.
    lib = load_library(STATS_LIBRARY)
    relevant = get_router("relevant")
    for task in _all_authored_traps():
        names = {s.name for s in relevant.select(task, lib)}
        assert "effect-sizes-and-intervals" not in names
        assert "compute-dont-fabricate" not in names
