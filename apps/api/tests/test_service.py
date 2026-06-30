"""run_analysis drives the agent → a verified, figure-bearing report (hermetic)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from statskills_api.service import run_analysis, skills_config
from statskills_api.stream import RunTap

# The agent "runs" a Breusch-Pagan check; the fake executor returns its printed p-value
# (so the cited number verifies) and the het_breuschpagan identifier gates a figure in.
_CODE = (
    "from statsmodels.stats.diagnostic import het_breuschpagan\n"
    "print(het_breuschpagan(resid, exog))"
)
_OBSERVATION = "Breusch-Pagan p = 0.0001"
_SCRIPT = (
    f"Let me test for heteroskedasticity.\n```python\n{_CODE}\n```",
    "FINAL ANSWER: No",
    json.dumps(
        {
            "question": "Is the effect of x on y significant?",
            "data_summary": "12 rows; columns x, y.",
            "method": "OLS with a Breusch-Pagan heteroskedasticity check.",
            "assumption_checks": "Breusch-Pagan p = 0.0001 → heteroskedastic.",
            "interpretation": "Use heteroskedasticity-robust standard errors.",
            "caveats": "Small sample.",
            "results": [{"label": "Breusch-Pagan p", "value": "0.0001", "step": 0}],
        }
    ),
)


def _regression_csv(tmp_path: Path) -> Path:
    csv = tmp_path / "data.csv"
    rows = "\n".join(f"{i},{2 * i + (i % 3)}" for i in range(1, 13))
    csv.write_text(f"x,y\n{rows}\n")
    return csv


def test_run_analysis_composes_verified_report_with_figure(
    tmp_path: Path, fake_llm, fake_executor
) -> None:
    out_dir = tmp_path / "job1"
    out_dir.mkdir()

    report = run_analysis(
        prompt="Is the effect of x on y significant?",
        dataset_path=_regression_csv(tmp_path),
        delivery="off",
        out_dir=out_dir,
        tap=RunTap(),
        llm=fake_llm(*_SCRIPT),
        executor=fake_executor(outputs={_CODE: _OBSERVATION}),
    )

    assert report.task_id == "job1"
    # The cited p-value is grounded in the (fake) observation, so it verifies.
    assert report.results[0].value == "0.0001" and report.results[0].verified is True
    # The het_breuschpagan diagnostic gated a residuals-vs-fitted figure (cited step 0).
    assert len(report.figures) == 1
    figure = report.figures[0]
    assert figure.path == "figures/job1__residuals_vs_fitted.png" and figure.step == 0
    assert (out_dir / figure.path).stat().st_size > 0


def test_skills_config_maps_the_delivery_toggle() -> None:
    assert skills_config("off") is None
    assert skills_config("agentic") == {
        "mode": "curated",
        "delivery": "agentic",
        "router": "forced",
        "resolution": "L1",
    }
    injected = skills_config("injected")
    assert injected is not None and injected["delivery"] == "injected"
    with pytest.raises(ValueError, match="Unknown delivery"):
        skills_config("nonsense")
