"""Tests for the reporting backbone — evidence, schema, and anti-fabrication checks."""

from __future__ import annotations

from typing import Any

import pytest

from statskills.core.types import LLMResponse, Message
from statskills.reporting import (
    Report,
    ReportComposeError,
    ReportSchemaError,
    compose_report,
    generate_figures,
    observed_steps,
    parse_report,
    render_markdown,
    unverified,
    verify,
)
from statskills.tasks.schema import Dataset, ExpectedAnswer, Task


def _traj(*steps: dict[str, Any]) -> dict[str, Any]:
    return {"task_id": "t", "steps": list(steps)}


def _code_step(index: int, code: str, observation: str) -> dict[str, Any]:
    return {"index": index, "kind": "code", "code": code, "observation": observation}


def _payload(**over: Any) -> dict[str, Any]:
    base = {
        "question": "q",
        "data_summary": "d",
        "method": "m",
        "assumption_checks": "a",
        "interpretation": "i",
        "caveats": "c",
        "results": [{"label": "p-value", "value": "0.155", "step": 1}],
    }
    base.update(over)
    return base


# --- evidence -------------------------------------------------------------------


def test_observed_steps_keeps_code_steps_and_their_indices() -> None:
    traj = _traj(
        _code_step(0, "print(df.head())", "   x  y"),
        {"index": 1, "kind": "final", "thought": "done", "code": None},
        _code_step(2, "print(stats.ttest_ind(a, b))", "p = 0.1550"),
    )
    steps = observed_steps(traj)
    assert [(s.index, s.observation) for s in steps] == [
        (0, "   x  y"),
        (2, "p = 0.1550"),
    ]


# --- schema ---------------------------------------------------------------------


def test_parse_report_builds_a_validated_report() -> None:
    report = parse_report("t", _payload())
    assert report.task_id == "t" and report.question == "q"
    assert [(c.label, c.value, c.step) for c in report.results] == [
        ("p-value", "0.155", 1)
    ]
    assert report.to_dict()["results"][0]["value"] == "0.155"


def test_parse_report_rejects_missing_field() -> None:
    payload = _payload()
    del payload["method"]
    with pytest.raises(ReportSchemaError, match="method"):
        parse_report("t", payload)


def test_parse_report_rejects_malformed_claim() -> None:
    with pytest.raises(ReportSchemaError, match=r"results\[0\]"):
        parse_report("t", _payload(results=[{"label": "p", "value": "0.1"}]))  # no step


# --- verify (the anti-fabrication teeth) ----------------------------------------


def test_verify_marks_a_grounded_claim() -> None:
    traj = _traj(_code_step(1, "print(p)", "Welch p = 0.1550"))
    report = verify(
        parse_report("t", _payload()), traj
    )  # claims p-value 0.155 @ step 1
    assert report.results[0].verified is True
    assert unverified(report) == ()


def test_verify_flags_a_fabricated_number() -> None:
    traj = _traj(_code_step(1, "print(p)", "Welch p = 0.1550"))
    report = verify(
        parse_report(
            "t",
            _payload(
                results=[
                    {
                        "label": "p-value",
                        "value": "0.999",
                        "step": 1,
                    },  # not in the observation
                ]
            ),
        ),
        traj,
    )
    assert report.results[0].verified is False
    assert len(unverified(report)) == 1


def test_verify_tolerates_rounding_and_flags_wrong_step() -> None:
    traj = _traj(
        _code_step(1, "print(p)", "coef p = 0.1551, R2 = 0.90"),
        _code_step(2, "print(slope)", "slope = -0.96"),
    )
    report = verify(
        parse_report(
            "t",
            _payload(
                results=[
                    {
                        "label": "p (rounded)",
                        "value": "0.16",
                        "step": 1,
                    },  # rounds to 0.1551 -> ok
                    {
                        "label": "slope",
                        "value": "-0.96",
                        "step": 1,
                    },  # right value, WRONG step
                ]
            ),
        ),
        traj,
    )
    assert report.results[0].verified is True
    assert (
        report.results[1].verified is False
    )  # -0.96 is in step 2, not the cited step 1


def test_verify_does_not_loosely_match_integer_claims() -> None:
    # An integer-looking claim must NOT verify by rounding an unrelated observation
    # (0 must not "match" a printed 0.49, nor 2 a printed 1.6).
    traj = _traj(_code_step(1, "print(p)", "p = 0.49 and slope = 1.6"))
    report = verify(
        parse_report(
            "t",
            _payload(
                results=[
                    {"label": "count", "value": "0", "step": 1},
                    {"label": "pairs", "value": "2", "step": 1},
                ]
            ),
        ),
        traj,
    )
    assert [c.verified for c in report.results] == [False, False]


def test_verify_matches_a_true_integer_exactly() -> None:
    traj = _traj(_code_step(1, "print(n)", "significant pairs = 2"))
    report = verify(
        parse_report(
            "t", _payload(results=[{"label": "pairs", "value": "2", "step": 1}])
        ),
        traj,
    )
    assert report.results[0].verified is True


def test_verify_flags_non_numeric_claim() -> None:
    traj = _traj(_code_step(1, "print(x)", "the effect is negative"))
    report = verify(
        parse_report(
            "t",
            _payload(
                results=[
                    {
                        "label": "direction",
                        "value": "negative",
                        "step": 1,
                    },  # not a number
                ]
            ),
        ),
        traj,
    )
    assert report.results[0].verified is False


def test_report_json_round_trips() -> None:
    report: Report = parse_report("t", _payload())
    assert report.to_dict()["task_id"] == "t"
    assert report.to_dict()["results"][0]["step"] == 1


# --- compose (mock LLM, no API) -------------------------------------------------


class _FakeLLM:
    """An ``LLM`` that replays canned responses (last one repeats)."""

    def __init__(self, *responses: str) -> None:
        self._responses = list(responses)
        self.calls = 0

    @property
    def model(self) -> str:
        return "fake"

    def complete(self, messages: list[Message]) -> LLMResponse:
        text = self._responses[min(self.calls, len(self._responses) - 1)]
        self.calls += 1
        return LLMResponse(text=text, model="fake", finish_reason="stop")


_TASK = Task(
    id="welch",
    prompt="Do A and B differ?",
    expected=ExpectedAnswer.single("No", "categorical"),
)
_TRAJ = _traj(
    _code_step(1, "print(stats.ttest_ind(a, b, equal_var=False))", "Welch p = 0.1551")
)


def _report_json(value: str = "0.155") -> str:
    import json as _json

    return _json.dumps(
        _payload(results=[{"label": "Welch p-value", "value": value, "step": 1}])
    )


def test_compose_report_parses_and_verifies() -> None:
    report = compose_report(_TRAJ, _TASK, _FakeLLM(_report_json()))
    assert report.task_id == "t" and report.method == "m"  # task_id from the trajectory
    assert report.results[0].label == "Welch p-value"
    assert report.results[0].verified is True  # 0.155 grounded in step 1's "0.1551"


def test_compose_report_tolerates_markdown_fence() -> None:
    fenced = f"Here is the report:\n```json\n{_report_json()}\n```"
    report = compose_report(_TRAJ, _TASK, _FakeLLM(fenced))
    assert report.results[0].verified is True


def test_compose_report_retries_then_succeeds() -> None:
    llm = _FakeLLM("not json at all", _report_json())  # malformed, then valid
    report = compose_report(_TRAJ, _TASK, llm)
    assert llm.calls == 2 and report.results[0].verified is True


def test_compose_report_raises_after_retry_budget() -> None:
    llm = _FakeLLM("nope")  # always malformed
    with pytest.raises(ReportComposeError, match="schema-valid"):
        compose_report(_TRAJ, _TASK, llm, max_retries=1)
    assert llm.calls == 2  # initial + 1 retry


# --- render ---------------------------------------------------------------------


def test_render_markdown_has_sections_and_citations() -> None:
    traj = _traj(_code_step(1, "print(p)", "Welch p = 0.1550"))
    md = render_markdown(verify(parse_report("t", _payload()), traj))
    assert "## Method" in md and "## Results" in md and "## Caveats" in md
    assert "**p-value:** 0.155 _[step 1]_" in md
    assert "unverified" not in md  # the claim is grounded


def test_render_markdown_includes_figures_section() -> None:
    from dataclasses import replace

    from statskills.reporting import Figure

    report = replace(
        parse_report("t", _payload()),
        figures=(Figure("figures/x.png", "Residuals vs fitted", 1),),
    )
    md = render_markdown(report)
    assert "## Figures" in md
    assert "![Residuals vs fitted](figures/x.png)" in md
    assert "step 1" in md


# --- figures (deterministic; matplotlib via the reporting extra) ----------------


def _reg_task(tmp_path: Any, columns: str = "x,y") -> Task:
    csv = tmp_path / "reg.csv"
    rows = "\n".join(f"{i},{2 * i + (i % 3)}" for i in range(1, 13))
    csv.write_text(f"{columns}\n{rows}\n")
    return Task(
        id="reg-het",
        prompt="Is the effect significant?",
        datasets=(Dataset(csv),),
        expected=ExpectedAnswer.single("No", "categorical"),
    )


def test_generate_figures_gated_and_cited(tmp_path: Any) -> None:
    task = _reg_task(tmp_path)
    traj = _traj(
        _code_step(
            1,
            "from statsmodels.stats.diagnostic import het_breuschpagan; bp()",
            "p=0.0001",
        ),
        _code_step(2, "m.get_influence().cooks_distance[0]", "cooks ..."),
    )
    figures = generate_figures(traj, task, tmp_path)
    by_key = {f.path.rsplit("__", 1)[1]: f for f in figures}
    assert set(by_key) == {"residuals_vs_fitted.png", "influence.png"}  # the two it ran
    assert by_key["residuals_vs_fitted.png"].step == 1  # cited to the BP step
    assert by_key["influence.png"].step == 2
    for fig in figures:  # the PNGs were actually written
        assert (tmp_path / fig.path).stat().st_size > 0


def test_generate_figures_empty_without_a_diagnostic(tmp_path: Any) -> None:
    task = _reg_task(tmp_path)
    traj = _traj(_code_step(1, "print(df.corr())", "x  y"))  # no regression diagnostic
    assert generate_figures(traj, task, tmp_path) == ()


def test_generate_figures_ignores_filename_lookalikes(tmp_path: Any) -> None:
    # Loading 'reg_influence.csv' must NOT count as performing an influence diagnostic —
    # the filename is a string literal, not an executed get_influence/cooks_distance.
    task = _reg_task(tmp_path)
    traj = _traj(
        _code_step(
            1, "df = pd.read_csv('reg_influence.csv')  # influence dataset", "x y"
        )
    )
    assert generate_figures(traj, task, tmp_path) == ()


def test_generate_figures_empty_for_non_regression_data(tmp_path: Any) -> None:
    csv = tmp_path / "g.csv"
    csv.write_text("group,value\nA,1\nA,2\nB,3\nB,4\n")  # no y ~ predictors fit
    task = Task(
        id="trap-welch",
        prompt="p",
        datasets=(Dataset(csv),),
        expected=ExpectedAnswer.single("No", "categorical"),
    )
    traj = _traj(_code_step(1, "het_breuschpagan(resid, exog)", "p=0.5"))
    assert generate_figures(traj, task, tmp_path) == ()


def test_render_markdown_flags_unverified_claims() -> None:
    traj = _traj(_code_step(1, "print(p)", "Welch p = 0.1550"))
    report = verify(
        parse_report(
            "t",
            _payload(
                results=[
                    {"label": "p-value", "value": "0.999", "step": 1},  # fabricated
                ]
            ),
        ),
        traj,
    )
    md = render_markdown(report)
    assert "unverified" in md and "Warning:" in md
