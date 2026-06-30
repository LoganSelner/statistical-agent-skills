"""Tests for skill-engagement extraction + the readxpass contingency."""

from __future__ import annotations

from typing import Any

from statskills.evaluation.engagement import (
    EngagementRecord,
    extract_engagement,
    summarize_engagement,
)
from statskills.evaluation.results import ScoreRecord


def _traj(task_id: str, trial: int, *codes: str | None) -> dict[str, Any]:
    """A trajectory record (as in trajectories.jsonl) with the given code steps."""
    return {
        "task_id": task_id,
        "trial": trial,
        "steps": [{"kind": "code", "code": c} for c in codes],
    }


def _score(task_id: str, trial: int, passed: bool) -> ScoreRecord:
    return ScoreRecord(
        task_id, passed, float(passed), "x", "", "final", 2, 10, 5, trial=trial
    )


# --- extraction -----------------------------------------------------------------


def test_extracts_canonical_read() -> None:
    traj = _traj(
        "t",
        0,
        'print(open("skills/multiple-comparison-correction.md").read())',
    )
    (rec,) = extract_engagement([traj])
    assert rec.skills_read == ("multiple-comparison-correction",)
    assert rec.engaged is True


def test_no_skill_code_is_not_engaged() -> None:
    code = "import pandas as pd; print(df.head())"
    (rec,) = extract_engagement([_traj("t", 0, code)])
    assert rec.skills_read == ()
    assert rec.engaged is False


def test_distinct_reads_deduped_first_seen_order() -> None:
    traj = _traj(
        "t",
        0,
        'open("skills/parametric-assumption-checks.md").read()',
        'open("skills/multiple-comparison-correction.md").read()',
        'open("skills/parametric-assumption-checks.md").read()',  # repeat
    )
    (rec,) = extract_engagement([traj])
    assert rec.skills_read == (
        "parametric-assumption-checks",
        "multiple-comparison-correction",
    )


def test_matches_path_not_open_call() -> None:
    # Robust to any read idiom — we match the staged path, not ``open(``.
    (rec,) = extract_engagement(
        [_traj("t", 0, 'from pathlib import Path; Path("skills/x.md").read_text()')]
    )
    assert rec.skills_read == ("x",)


def test_codeless_steps_and_errored_trajectories_read_nothing() -> None:
    final_step = _traj("t", 0, None)  # e.g. a final/no_action step carries no code
    errored = {"task_id": "t", "trial": 1, "error": "boom"}  # no steps at all
    recs = extract_engagement([final_step, errored])
    assert [r.skills_read for r in recs] == [(), ()]
    assert [r.trial for r in recs] == [0, 1]


# --- summary + readxpass --------------------------------------------------------

# The exact Haiku agentic trial pattern on trap-multiple-comparisons (the headline
# mechanism, locked as a regression): 4/5 trials read a skill — one read the
# *assumption-checks* skill (not MC) yet still passed, and one read MC yet failed.
_MC = [
    ("parametric-assumption-checks", True),  # t0: read, pass (wrong skill)
    ("multiple-comparison-correction", False),  # t1: read, fail
    (None, False),  # t2: no read, fail
    ("multiple-comparison-correction", True),  # t3: read, pass
    ("multiple-comparison-correction", True),  # t4: read, pass
]


def _mc_records() -> tuple[list[dict[str, Any]], list[ScoreRecord]]:
    trajs, scores = [], []
    for trial, (skill, passed) in enumerate(_MC):
        code = f'open("skills/{skill}.md").read()' if skill else "print(1)"
        trajs.append(_traj("mc", trial, code))
        scores.append(_score("mc", trial, passed))
    return trajs, scores


def test_per_task_read_freq_isolates_selective_engagement() -> None:
    trajs, scores = _mc_records()
    # An easy task the model aces without reading anything.
    for trial in range(5):
        trajs.append(_traj("welch", trial, "print(stats.ttest_ind(a, b))"))
        scores.append(_score("welch", trial, True))

    summary = summarize_engagement(extract_engagement(trajs), scores)

    assert summary.n_tasks == 2 and summary.n_trials == 5
    assert summary.per_task_read_freq == {"mc": 0.8, "welch": 0.0}
    assert summary.read_rate == 0.4  # 4 of 10 cells
    assert summary.skill_read_counts == {
        "multiple-comparison-correction": 3,
        "parametric-assumption-checks": 1,
    }


def test_read_pass_contingency_on_the_mc_task() -> None:
    trajs, scores = _mc_records()
    rp = summarize_engagement(extract_engagement(trajs), scores).read_pass
    assert (rp.read_pass, rp.read_fail, rp.noread_pass, rp.noread_fail) == (3, 1, 0, 1)
    assert rp.pass_rate_given_read == 3 / 4
    assert rp.pass_rate_given_no_read == 0.0  # the lone no-read trial failed


def test_conditional_rate_is_none_when_no_reads() -> None:
    trajs = [_traj("t", trial, "print(1)") for trial in range(3)]
    scores = [_score("t", trial, trial == 0) for trial in range(3)]
    rp = summarize_engagement(extract_engagement(trajs), scores).read_pass
    assert rp.pass_rate_given_read is None  # nothing was read
    assert rp.pass_rate_given_no_read == 1 / 3


def test_empty_engagement_summarises_to_zeros() -> None:
    summary = summarize_engagement([], [])
    assert summary.n_tasks == 0 and summary.read_rate == 0.0
    assert summary.read_pass == summary.read_pass.__class__(0, 0, 0, 0)


def test_record_engaged_property() -> None:
    assert EngagementRecord("t", 0, ("s",)).engaged
    assert not EngagementRecord("t", 0, ()).engaged
