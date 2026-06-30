"""The authored regression-trap arm is self-checking (ROADMAP §5).

For each committed dataset, the *correct* diagnostic must reproduce the task's ground
truth and the *naive* OLS fit must yield something else — otherwise the trap isn't a
trap. This guards the ground truths and the engineered divergence against data/seed
drift, mirroring ``test_trap_tasks.py`` for the original five traps.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.stats.diagnostic import het_breuschpagan

from statskills.tasks.authored.regression_trap_tasks import load_regression_trap_tasks
from statskills.tasks.loader import load_tasks


def _by_id() -> dict[str, Any]:
    return {t.id: t for t in load_regression_trap_tasks()}


def _expected(task: Any) -> Any:
    assert task.expected is not None
    (key,) = task.expected.keys
    return key.value


def _df(task: Any) -> pd.DataFrame:
    return pd.read_csv(task.datasets[0].path)


def _ols(y: Any, *predictors: Any) -> Any:
    x = sm.add_constant(np.column_stack([np.asarray(p, float) for p in predictors]))
    return sm.OLS(np.asarray(y, float), x).fit()


def test_loader_dispatches_authored_regression() -> None:
    ids = {t.id for t in load_tasks({"set": "authored_regression"})}
    assert ids == {
        "reg-confounding",
        "reg-heteroskedasticity",
        "reg-influence",
        "reg-nonlinearity",
    }


def test_reg_confounding_sign_flips_after_adjusting() -> None:
    task = _by_id()["reg-confounding"]
    df = _df(task)
    simple = _ols(df.y, df.x)  # naive: y ~ x alone
    full = _ols(df.y, df.x, df.z)  # correct: adjust for the confounder z
    naive = "positive" if simple.params[1] > 0 else "negative"
    correct = "negative" if full.params[1] < 0 else "positive"
    assert correct == _expected(task) and naive != _expected(task)
    # both directions are clearly significant — the flip isn't noise
    assert simple.pvalues[1] < 0.05 and full.pvalues[1] < 0.05


def test_reg_heteroskedasticity_robust_se_overturns_default() -> None:
    task = _by_id()["reg-heteroskedasticity"]
    df = _df(task)
    m = _ols(df.y, df.x)
    naive = "Yes" if m.pvalues[1] < 0.05 else "No"
    robust_p = m.get_robustcov_results(cov_type="HC3").pvalues[1]
    correct = "Yes" if robust_p < 0.05 else "No"
    assert correct == _expected(task) and naive != _expected(task)
    # the heteroskedasticity is real and detectable (so robust SEs are the right call)
    assert het_breuschpagan(m.resid, m.model.exog)[1] < 0.05


def test_reg_influence_one_point_drives_the_slope() -> None:
    task = _by_id()["reg-influence"]
    df = _df(task)
    m = _ols(df.y, df.x)
    cooks = m.get_influence().cooks_distance[0]
    keep = cooks <= 4 / len(df)
    refit = _ols(df.y[keep], df.x[keep])
    naive = "Yes" if m.pvalues[1] < 0.05 else "No"
    correct = "Yes" if refit.pvalues[1] < 0.05 else "No"
    assert correct == _expected(task) and naive != _expected(task)
    # at least one point is genuinely influential, and dropping the flagged point(s)
    # removes some data (so the conclusion really rests on them)
    assert (~keep).any() and cooks.max() > 4 / len(df)


def test_reg_nonlinearity_quadratic_term_significant() -> None:
    task = _by_id()["reg-nonlinearity"]
    df = _df(task)
    p_linear = _ols(df.y, df.x).pvalues[1]
    p_quad = _ols(df.y, df.x, df.x**2).pvalues[2]
    naive = "Yes" if p_linear < 0.05 else "No"
    correct = "Yes" if p_quad < 0.05 else "No"
    assert correct == _expected(task) and naive != _expected(task)
