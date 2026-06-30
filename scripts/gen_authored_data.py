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
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.api as sm
from statsmodels.stats.multitest import multipletests

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "authored"


def _write(df: pd.DataFrame, name: str) -> None:
    df.to_csv(DATA_DIR / name, index=False)


def _ols(y: pd.Series, *predictors: pd.Series) -> Any:
    """Fit OLS of ``y`` on a constant + the given predictor columns."""
    x = sm.add_constant(np.column_stack([np.asarray(p, float) for p in predictors]))
    return sm.OLS(np.asarray(y, float), x).fit()


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


def mann_whitney() -> tuple[str, str]:
    """Heavy-tailed (contaminated) data: the t-test's inflated variance misses a real
    location shift that the rank-based Mann-Whitney test detects."""
    rng = np.random.default_rng(1)

    def group(mu: float) -> np.ndarray:
        main = rng.normal(mu, 1.0, 28)
        heavy = rng.normal(mu, 8.0, 6)  # symmetric contamination -> heavy tails
        return np.round(np.concatenate([main, heavy]), 3)

    a, b = group(0.0), group(1.2)
    df = pd.DataFrame(
        {"group": ["A"] * 34 + ["B"] * 34, "value": np.concatenate([a, b])}
    )
    _write(df, "trap_mwu.csv")
    p_t = stats.ttest_ind(a, b).pvalue
    p_mwu = stats.mannwhitneyu(a, b, alternative="two-sided").pvalue
    naive = "Yes" if p_t < 0.05 else "No"
    correct = "Yes" if p_mwu < 0.05 else "No"
    return (
        f"t-test p = {p_t:.4f} -> {naive}",
        f"Mann-Whitney p = {p_mwu:.4f} -> ground truth {correct}",
    )


def reg_confounding() -> tuple[str, str]:
    """Omitted-variable bias: y~x alone is positive, but the true effect of x (adjusting
    for the confounder z) is negative — a Simpson's-paradox sign flip."""
    rng = np.random.default_rng(1)
    n = 60
    z = rng.normal(0, 1, n)
    x = z + rng.normal(0, 0.5, n)  # x is driven by the confounder z
    y = -1.0 * x + 2.0 * z + rng.normal(0, 0.5, n)  # true x-effect is negative
    df = pd.DataFrame({"x": np.round(x, 4), "z": np.round(z, 4), "y": np.round(y, 4)})
    _write(df, "reg_confounding.csv")
    simple, full = _ols(df.y, df.x), _ols(df.y, df.x, df.z)
    naive = "positive" if simple.params[1] > 0 else "negative"
    correct = "negative" if full.params[1] < 0 else "positive"
    return (
        f"y~x slope = {simple.params[1]:+.2f} (p={simple.pvalues[1]:.3f}) -> {naive}",
        f"y~x+z x-coef = {full.params[1]:+.2f} (p={full.pvalues[1]:.3f}) "
        f"-> ground truth {correct}",
    )


def reg_heteroskedasticity() -> tuple[str, str]:
    """Heteroskedastic noise: default OLS standard errors call the slope significant,
    but heteroskedasticity-robust (HC3) standard errors do not."""
    rng = np.random.default_rng(11)
    n = 80
    x = rng.uniform(0.5, 10, n)
    y = 0.4 * x + rng.normal(0, 0.5 + 0.9 * x)  # noise spread grows with x
    df = pd.DataFrame({"x": np.round(x, 4), "y": np.round(y, 4)})
    _write(df, "reg_heteroskedasticity.csv")
    m = _ols(df.y, df.x)
    p_default = m.pvalues[1]
    p_hc3 = m.get_robustcov_results(cov_type="HC3").pvalues[1]
    naive = "Yes" if p_default < 0.05 else "No"
    correct = "Yes" if p_hc3 < 0.05 else "No"
    return (
        f"default-SE p = {p_default:.4f} -> {naive}",
        f"HC3 robust-SE p = {p_hc3:.4f} -> ground truth {correct}",
    )


def reg_influence() -> tuple[str, str]:
    """One high-leverage point drives the slope: the full-data fit is significant, but
    dropping the influential point(s) (Cook's distance > 4/n) it is not."""
    rng = np.random.default_rng(1)
    n = 40
    x = np.append(rng.normal(0, 1, n), 10.0)  # bulk has no slope; one far outlier
    y = np.append(rng.normal(0, 1, n), 10.0)
    df = pd.DataFrame({"x": np.round(x, 4), "y": np.round(y, 4)})
    _write(df, "reg_influence.csv")
    m = _ols(df.y, df.x)
    keep = m.get_influence().cooks_distance[0] <= 4 / len(df)
    refit = _ols(df.y[keep], df.x[keep])
    naive = "Yes" if m.pvalues[1] < 0.05 else "No"
    correct = "Yes" if refit.pvalues[1] < 0.05 else "No"
    return (
        f"full-data p = {m.pvalues[1]:.4f} -> {naive}",
        f"drop-influential p = {refit.pvalues[1]:.4f} -> ground truth {correct}",
    )


def reg_nonlinearity() -> tuple[str, str]:
    """A symmetric U-shape: the linear slope is ~0 and non-significant, but a quadratic
    term is highly significant — 'no linear effect' misses a strong relationship."""
    rng = np.random.default_rng(1)
    n = 60
    x = rng.uniform(-3, 3, n)
    y = x**2 + rng.normal(0, 1.0, n)
    df = pd.DataFrame({"x": np.round(x, 4), "y": np.round(y, 4)})
    _write(df, "reg_nonlinearity.csv")
    p_linear = _ols(df.y, df.x).pvalues[1]
    p_quad = _ols(df.y, df.x, df.x**2).pvalues[2]
    naive = "Yes" if p_linear < 0.05 else "No"
    correct = "Yes" if p_quad < 0.05 else "No"
    return (
        f"linear slope p = {p_linear:.4f} -> {naive}",
        f"quadratic term p = {p_quad:.2e} -> ground truth {correct}",
    )


def main() -> int:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for fn in (
        correlation,
        welch,
        paired,
        multiple_comparisons,
        mann_whitney,
        reg_confounding,
        reg_heteroskedasticity,
        reg_influence,
        reg_nonlinearity,
    ):
        naive, correct = fn()
        print(f"\n[{fn.__name__}]")
        print(f"    naive   : {naive}")
        print(f"    correct : {correct}")
    print(f"\nWrote trap_*.csv to {DATA_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
