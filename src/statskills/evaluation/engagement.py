"""Skill engagement from saved trajectories — readxpass, no agent re-run (ROADMAP §9).

Under ``agentic`` delivery the skill bodies are sandbox files the agent may read on
demand (``open("skills/<name>.md")``); whether it *does* is the mechanism behind the
headline result (selective engagement — read a skill only for the task whose procedure
is genuinely missing). This module turns that signal — which lived only in raw
trajectories and was recovered by hand — into a deterministic measurement: per-(task,
trial) skill-read records, and a join against scores into the **readxpass** contingency.

In the agent-evaluation literature this is the skill *invocation / use-rate* plus its
conditional pass-rate; we keep the project's "engagement" naming. It is a pure
trajectory consumer (like :mod:`.grading`); **stdlib only**, no agent re-run.

Scope: a read is a skill *file* read, which only happens under ``agentic`` delivery
(``off`` has no skills, ``injected`` puts bodies in context with no files), so read-rate
is structurally 0 for the other arms — correct and uniform. "Engaged" means the trial
read **≥1** skill (assumption-free); *which* skill is recorded so selection-accuracy
("the right skill") stays computable post-hoc without baking a relevance verdict here.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import re
from typing import Any

from statskills.evaluation.results import ScoreRecord

# A skill read is any reference to a staged ``skills/<name>.md`` path in executed
# code, matched on the path rather than the ``open(`` call — so ``open(...)``,
# ``Path(...).read_text()``, and ``!cat skills/x.md`` all count. The staging path is
# fixed by the sandbox (skills mount at /work/skills/) and the discovery prompt asks
# for exactly this form.
_SKILL_READ = re.compile(r"skills/([A-Za-z0-9_.-]+)\.md")


@dataclass(frozen=True)
class EngagementRecord:
    """Which skills one (task, trial) read — empty when the agent engaged none."""

    task_id: str
    trial: int
    skills_read: tuple[str, ...]  # distinct skill names, first-seen order

    @property
    def engaged(self) -> bool:
        """True if the agent read at least one skill file this trial."""
        return bool(self.skills_read)


@dataclass(frozen=True)
class ReadPass:
    """The readxpass 2x2 contingency over (task, trial) cells.

    Conditional pass rates are ``None`` when their conditioning cell is empty (no
    reads, or no non-reads) — guarding against dividing by zero or reporting a rate
    over nothing.
    """

    read_pass: int
    read_fail: int
    noread_pass: int
    noread_fail: int

    @property
    def pass_rate_given_read(self) -> float | None:
        n = self.read_pass + self.read_fail
        return self.read_pass / n if n else None

    @property
    def pass_rate_given_no_read(self) -> float | None:
        n = self.noread_pass + self.noread_fail
        return self.noread_pass / n if n else None


@dataclass(frozen=True)
class EngagementSummary:
    """One condition's engagement, summarised over its (task, trial) cells.

    ``read_rate`` and ``per_task_read_freq`` are computed over the engagement records
    alone; ``read_pass`` over the cells that also have a score (normally all of them).
    The cell-level ``read_pass`` aggregates every task, so no-reads pile up on tasks
    the model already solves; ``per_task_read_freq`` is what isolates *selective*
    engagement.
    """

    n_tasks: int
    n_trials: int
    read_rate: float  # fraction of (task, trial) cells that read >=1 skill (use-rate)
    per_task_read_freq: dict[str, float]  # task_id -> fraction of trials that read
    skill_read_counts: dict[str, int]  # skill name -> number of cells that read it
    read_pass: ReadPass


def extract_engagement(
    trajectories: Sequence[Mapping[str, Any]],
) -> list[EngagementRecord]:
    """Scan saved trajectories into per-(task, trial) skill-read records.

    One record per trajectory (an errored one simply read nothing), so the set aligns
    with the graded :class:`ScoreRecord` set on ``(task_id, trial)``. Each step's
    ``code`` (``None`` on ``final``/``no_action`` steps) is scanned for skill-file
    references; the names are de-duplicated, keeping first-seen order.
    """
    records: list[EngagementRecord] = []
    for traj in trajectories:
        seen: dict[str, None] = {}  # ordered set
        for step in traj.get("steps", ()):
            code = step.get("code")
            if not code:
                continue
            for name in _SKILL_READ.findall(code):
                seen.setdefault(name, None)
        records.append(
            EngagementRecord(
                task_id=str(traj.get("task_id", "")),
                trial=int(traj.get("trial", 0)),
                skills_read=tuple(seen),
            )
        )
    return records


def summarize_engagement(
    engagement: Sequence[EngagementRecord],
    scores: Sequence[ScoreRecord],
) -> EngagementSummary:
    """Read-rate, per-task read freq, skill counts, and the readxpass contingency."""
    if not engagement:
        return EngagementSummary(0, 0, 0.0, {}, {}, ReadPass(0, 0, 0, 0))

    passed_by: dict[tuple[str, int], bool] = {
        (s.task_id, s.trial): s.passed for s in scores
    }
    by_task: dict[str, list[EngagementRecord]] = defaultdict(list)
    skill_counts: dict[str, int] = defaultdict(int)
    rp = {"read_pass": 0, "read_fail": 0, "noread_pass": 0, "noread_fail": 0}
    for rec in engagement:
        by_task[rec.task_id].append(rec)
        for name in rec.skills_read:
            skill_counts[name] += 1
        passed = passed_by.get((rec.task_id, rec.trial))
        if passed is None:
            continue  # no score to classify against (coverage mismatch) — skip the cell
        prefix = "read" if rec.engaged else "noread"
        rp[f"{prefix}_{'pass' if passed else 'fail'}"] += 1

    read = sum(1 for r in engagement if r.engaged)
    return EngagementSummary(
        n_tasks=len(by_task),
        n_trials=len({r.trial for r in engagement}),
        read_rate=read / len(engagement),
        per_task_read_freq={
            t: sum(r.engaged for r in recs) / len(recs)
            for t, recs in sorted(by_task.items())
        },
        skill_read_counts=dict(sorted(skill_counts.items())),
        read_pass=ReadPass(**rp),
    )
