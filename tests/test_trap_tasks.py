"""The authored trap arm is self-checking (ROADMAP §4).

For each committed dataset, the *correct* method must reproduce the task's ground truth
and the *naive* method must yield something else — otherwise the trap isn't a trap. This
guards both the ground truths and the engineered divergence against data/seed drift.
"""

from __future__ import annotations

from itertools import combinations
from typing import Any

import pandas as pd
from scipy import stats
from statsmodels.stats.multitest import multipletests

from statskills.tasks.authored.trap_tasks import load_trap_tasks
from statskills.tasks.loader import load_tasks


def _by_id() -> dict[str, object]:
    return {t.id: t for t in load_trap_tasks()}


def _expected(task) -> Any:
    assert task.expected is not None
    (key,) = task.expected.keys
    return key.value


def _df(task) -> pd.DataFrame:
    return pd.read_csv(task.datasets[0].path)


def test_loader_dispatches_authored_trap():
    ids = {t.id for t in load_tasks({"set": "authored_trap"})}
    assert ids == {
        "trap-correlation",
        "trap-welch",
        "trap-paired",
        "trap-multiple-comparisons",
        "trap-chi2",
    }


def test_trap_correlation_spearman_right_pearson_wrong():
    task = _by_id()["trap-correlation"]
    df = _df(task)
    correct = round(float(stats.spearmanr(df.x, df.y).statistic), 2)
    naive = round(float(stats.pearsonr(df.x, df.y).statistic), 2)
    assert abs(correct - float(_expected(task))) < 5e-3
    assert abs(naive - float(_expected(task))) > 0.1  # naive clearly diverges


def test_trap_welch_right_pooled_wrong():
    task = _by_id()["trap-welch"]
    df = _df(task)
    a, b = df.value[df.group == "A"], df.value[df.group == "B"]
    correct = "Yes" if stats.ttest_ind(a, b, equal_var=False).pvalue < 0.05 else "No"
    naive = "Yes" if stats.ttest_ind(a, b, equal_var=True).pvalue < 0.05 else "No"
    assert correct == _expected(task) and naive != _expected(task)


def test_trap_paired_right_independent_wrong():
    task = _by_id()["trap-paired"]
    df = _df(task)
    correct = "Yes" if stats.ttest_rel(df.before, df.after).pvalue < 0.05 else "No"
    naive = "Yes" if stats.ttest_ind(df.before, df.after).pvalue < 0.05 else "No"
    assert correct == _expected(task) and naive != _expected(task)


def test_trap_multiple_comparisons_correction_matters():
    task = _by_id()["trap-multiple-comparisons"]
    df = _df(task)
    groups = {k: v.value.to_numpy() for k, v in df.groupby("group")}
    pvals = [
        stats.ttest_ind(groups[a], groups[b]).pvalue
        for a, b in combinations(sorted(groups), 2)
    ]
    correct = int(multipletests(pvals, method="holm")[0].sum())
    naive = sum(p < 0.05 for p in pvals)
    assert correct == _expected(task) and naive != _expected(task)


def test_trap_chi2_fisher_right_chisquare_wrong():
    task = _by_id()["trap-chi2"]
    df = _df(task)
    table = pd.crosstab(df.treatment, df.outcome)
    correct = "Yes" if stats.fisher_exact(table).pvalue < 0.05 else "No"
    naive = (
        "Yes" if stats.chi2_contingency(table, correction=False).pvalue < 0.05 else "No"
    )
    assert correct == _expected(task) and naive != _expected(task)
    # the small expected counts are what make Fisher the appropriate test
    assert stats.chi2_contingency(table).expected_freq.min() < 5
