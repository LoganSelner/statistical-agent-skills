"""Report-time regression diagnostic figures, gated + cited (ROADMAP §10).

Renders the standard diagnostics — residuals-vs-fitted, normal Q-Q, Cook's distance —
from the *same dataset and OLS fit the agent analysed*, but **only** for the checks the
agent actually performed (per its trajectory), captioned with the citing step. So a
figure visualises the agent's analysis with provenance; it never re-invokes the agent or
introduces an ungrounded finding. The scientific stack + matplotlib are imported lazily
(the optional ``reporting`` extra), keeping the research harness light.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import io
from pathlib import Path
import re
import tokenize
from typing import Any

from statskills.reporting.evidence import ObservedStep, observed_steps
from statskills.reporting.schema import Figure
from statskills.tasks.schema import Task


class FiguresUnavailable(RuntimeError):
    """The optional ``reporting`` extra (matplotlib + sci stack) is not installed."""


# A diagnostic the agent may have run -> (figure key, code signals, caption).
_DIAGNOSTICS: tuple[tuple[str, tuple[str, ...], str], ...] = (
    (
        "residuals_vs_fitted",
        ("het_breuschpagan", "breusch", "resid"),
        "Residuals vs fitted — non-constant spread signals heteroskedasticity.",
    ),
    (
        "qq",
        ("qqplot", "probplot", "shapiro", "normaltest"),
        "Normal Q-Q of residuals — departures from the line signal non-normality.",
    ),
    (
        "influence",
        ("cooks_distance", "get_influence", "olsinfluence", "hat_matrix_diag"),
        "Cook's distance per observation — points above ~4/n drive the fit.",
    ),
)


def generate_figures(
    trajectory: Mapping[str, Any], task: Task, out_dir: Path
) -> tuple[Figure, ...]:
    """Diagnostic figures for the checks the agent performed; ``()`` if none apply.

    Empty when no recognised regression diagnostic ran, or the data isn't a fittable
    ``y ~ predictors`` table. Raises :class:`FiguresUnavailable` if the plotting stack
    is missing.
    """
    steps = observed_steps(trajectory)
    wanted = [
        (key, caption, step)
        for key, signals, caption in _DIAGNOSTICS
        if (step := _first_step_with(steps, signals)) is not None
    ]
    if not wanted:
        return ()
    fit = _fit_dataset(task)
    if fit is None:
        return ()

    figures_dir = out_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    plotters = {
        "residuals_vs_fitted": _plot_residuals_vs_fitted,
        "qq": _plot_qq,
        "influence": _plot_influence,
    }
    figures: list[Figure] = []
    for key, caption, step in wanted:
        rel = f"figures/{task.id}__{key}.png"
        _render(plotters[key], fit, out_dir / rel)
        figures.append(Figure(path=rel, caption=caption, step=step))
    return tuple(figures)


def _first_step_with(
    steps: Sequence[ObservedStep], signals: tuple[str, ...]
) -> int | None:
    """First step whose *code identifiers* contain a signal — citing a diagnostic the
    agent actually ran. Matching ignores string literals and comments, so a dataset
    filename (e.g. ``reg_influence.csv``) or a comment cannot fake a gate."""
    for step in steps:
        identifiers = _code_identifiers(step.code)
        if any(signal in identifiers for signal in signals):
            return step.index
    return None


def _code_identifiers(code: str) -> str:
    """The lowercased identifier tokens in ``code`` (string + comment tokens dropped).

    Tokenising keeps real calls like ``get_influence`` / ``het_breuschpagan`` while
    excluding quoted filenames/paths and comments. Falls back to the raw code minus
    quoted strings if the cell does not tokenise (rare — executed cells are valid).
    """
    names: list[str] = []
    try:
        for token in tokenize.generate_tokens(io.StringIO(code).readline):
            if token.type == tokenize.NAME:
                names.append(token.string.lower())
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return re.sub(r"\"[^\"]*\"|'[^']*'", " ", code).lower()
    return " ".join(names)


def _fit_dataset(task: Task) -> Any | None:
    """OLS of ``y`` on the other numeric columns; ``None`` if not fittable."""
    try:
        import pandas as pd
        import statsmodels.api as sm
    except ImportError as exc:  # pragma: no cover - exercised only without the extra
        raise FiguresUnavailable(
            "report figures need the 'reporting' extra: uv sync --extra reporting"
        ) from exc
    if not task.datasets:
        return None
    numeric = pd.read_csv(task.datasets[0].path).select_dtypes("number")
    if "y" not in numeric.columns or numeric.shape[1] < 2:
        return None
    predictors = sm.add_constant(numeric.drop(columns=["y"]))
    return sm.OLS(numeric["y"], predictors).fit()


def _render(plotter: Any, fit: Any, path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(5, 3.5))
    try:
        plotter(fit, ax)
        fig.tight_layout()
        fig.savefig(path, dpi=110)
    finally:
        plt.close(fig)


def _plot_residuals_vs_fitted(fit: Any, ax: Any) -> None:
    ax.scatter(fit.fittedvalues, fit.resid, s=18, alpha=0.7)
    ax.axhline(0, color="0.4", lw=1, ls="--")
    ax.set(xlabel="Fitted", ylabel="Residual", title="Residuals vs fitted")


def _plot_qq(fit: Any, ax: Any) -> None:
    from scipy import stats

    stats.probplot(fit.resid, dist="norm", plot=ax)
    ax.set_title("Normal Q-Q (residuals)")


def _plot_influence(fit: Any, ax: Any) -> None:
    cooks = fit.get_influence().cooks_distance[0]
    ax.stem(range(len(cooks)), cooks, markerfmt=".")
    ax.axhline(4 / len(cooks), color="crimson", lw=1, ls="--", label="4/n")
    ax.set(xlabel="Observation", ylabel="Cook's distance", title="Influence")
    ax.legend(loc="upper right", fontsize=8)
