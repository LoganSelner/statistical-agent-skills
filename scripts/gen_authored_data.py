#!/usr/bin/env python3
"""Generate the authored TRAP datasets (seeded) into data/authored/.

Each dataset is engineered so the *naive default* method yields one answer and the
*correct* method yields the ground truth baked into the task spec (ROADMAP §4). Running
this prints, per trap, the naive vs correct answers so they can be verified by eye; the
CSVs are committed. Each trap has its own fixed seed, so the data and ground truths are
reproducible and independently tunable.

Usage:  python scripts/gen_authored_data.py
"""

from __future__ import annotations

from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.multitest import multipletests

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "authored"


def _write(df: pd.DataFrame, name: str) -> None:
    df.to_csv(DATA_DIR / name, index=False)


def correlation() -> tuple[str, str]:
    """Leverage outliers create a spurious Pearson r; robust Spearman ~ 0."""
    rng = np.random.default_rng(1)
    x = np.append(rng.normal(0, 1, 50), [8.0, 9.0, 10.0])  # 3 outliers on a line
    y = np.append(rng.normal(0, 1, 50), [8.0, 9.0, 10.0])
    df = pd.DataFrame({"x": np.round(x, 4), "y": np.round(y, 4)})
    _write(df, "trap_correlation.csv")
    pearson = stats.pearsonr(df.x, df.y).statistic
    spearman = stats.spearmanr(df.x, df.y).statistic
    return (
        f"Pearson r = {pearson:.2f}",
        f"Spearman rho = {spearman:.2f}  -> ground truth {round(spearman, 2)}",
    )


def welch() -> tuple[str, str]:
    """Unequal variance + unequal n: pooled t over-rejects, Welch does not."""
    rng = np.random.default_rng(1)
    a = rng.normal(10.0, 1.0, 30)
    b = rng.normal(12.0, 4.0, 12)
    df = pd.DataFrame(
        {"group": ["A"] * 30 + ["B"] * 12, "value": np.round(np.concatenate([a, b]), 4)}
    )
    _write(df, "trap_welch.csv")
    va, vb = df.value[df.group == "A"], df.value[df.group == "B"]
    p_pooled = stats.ttest_ind(va, vb, equal_var=True).pvalue
    p_welch = stats.ttest_ind(va, vb, equal_var=False).pvalue
    naive = "Yes" if p_pooled < 0.05 else "No"
    correct = "Yes" if p_welch < 0.05 else "No"
    return (
        f"pooled t p = {p_pooled:.4f} -> {naive}",
        f"Welch t p = {p_welch:.4f} -> ground truth {correct}",
    )


def paired() -> tuple[str, str]:
    """Repeated measures: independent t is swamped by between-subject variance."""
    rng = np.random.default_rng(1)
    baseline = rng.normal(50, 10, 25)  # large between-subject spread
    before = baseline + rng.normal(0, 1, 25)
    after = (
        baseline + 2.0 + rng.normal(0, 1, 25)
    )  # small consistent within-subject shift
    df = pd.DataFrame(
        {
            "subject": np.arange(1, 26),
            "before": np.round(before, 4),
            "after": np.round(after, 4),
        }
    )
    _write(df, "trap_paired.csv")
    p_ind = stats.ttest_ind(df.before, df.after).pvalue
    p_paired = stats.ttest_rel(df.before, df.after).pvalue
    naive = "Yes" if p_ind < 0.05 else "No"
    correct = "Yes" if p_paired < 0.05 else "No"
    return (
        f"independent t p = {p_ind:.4f} -> {naive}",
        f"paired t p = {p_paired:.4f} -> ground truth {correct}",
    )


def multiple_comparisons() -> tuple[str, str]:
    """Many pairwise tests: several raw-significant, fewer survive Holm correction."""
    rng = np.random.default_rng(11)
    means = {"g1": 10.0, "g2": 10.0, "g3": 10.0, "g4": 10.7, "g5": 11.3}
    samples = {g: rng.normal(m, 1.5, 18) for g, m in means.items()}
    rows = [
        {"group": g, "value": round(float(v), 4)} for g, s in samples.items() for v in s
    ]
    _write(pd.DataFrame(rows), "trap_mc.csv")
    pvals = [
        stats.ttest_ind(samples[a], samples[b]).pvalue
        for a, b in combinations(means, 2)
    ]
    raw = sum(p < 0.05 for p in pvals)
    holm = int(multipletests(pvals, alpha=0.05, method="holm")[0].sum())
    return (
        f"uncorrected significant pairs = {raw}",
        f"Holm-corrected significant pairs = {holm}  -> ground truth {holm}",
    )


def chi2_fisher() -> tuple[str, str]:
    """Small expected counts: chi-square's approximation over-rejects vs Fisher."""
    table = np.array([[9, 2], [4, 7]])  # 2x2; an expected cell < 5
    rows = [
        {"treatment": t, "outcome": o}
        for i, t in enumerate(["X", "Y"])
        for j, o in enumerate(["success", "fail"])
        for _ in range(int(table[i, j]))
    ]
    df = pd.DataFrame(rows).sample(frac=1.0, random_state=0).reset_index(drop=True)
    _write(df, "trap_chi2.csv")
    ct = pd.crosstab(df.treatment, df.outcome)
    chi2 = stats.chi2_contingency(ct, correction=False)
    p_fisher = stats.fisher_exact(ct).pvalue
    return (
        f"chi-square p = {chi2.pvalue:.4f} -> {'Yes' if chi2.pvalue < 0.05 else 'No'}"
        f"  (min expected {chi2.expected_freq.min():.1f})",
        f"Fisher exact p = {p_fisher:.4f} -> "
        f"ground truth {'Yes' if p_fisher < 0.05 else 'No'}",
    )


def main() -> int:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for fn in (correlation, welch, paired, multiple_comparisons, chi2_fisher):
        naive, correct = fn()
        print(f"\n[{fn.__name__}]")
        print(f"    naive   : {naive}")
        print(f"    correct : {correct}")
    print(f"\nWrote trap_*.csv to {DATA_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
