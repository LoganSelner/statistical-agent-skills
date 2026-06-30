"""Endpoint tests via TestClient with a fake LLM + executor (no Docker, no API key)."""

from __future__ import annotations

import json
import time

from fastapi.testclient import TestClient
import pytest
from statskills_api.app import RunDeps, create_app, get_run_deps

# The scripted run: the agent runs a Breusch-Pagan check (gating a figure), finals, then
# the composer cites the printed p-value (which the fake executor returns).
_CODE = (
    "from statsmodels.stats.diagnostic import het_breuschpagan\n"
    "print(het_breuschpagan(resid, exog))"
)
_OBSERVATION = "Breusch-Pagan p = 0.0001"
_SCRIPT = (
    f"Testing for heteroskedasticity.\n```python\n{_CODE}\n```",
    "FINAL ANSWER: No",
    json.dumps(
        {
            "question": "Is the effect of x on y significant?",
            "data_summary": "12 rows; columns x, y.",
            "method": "OLS with a Breusch-Pagan check.",
            "assumption_checks": "Breusch-Pagan p = 0.0001 → heteroskedastic.",
            "interpretation": "Use robust standard errors.",
            "caveats": "Small sample.",
            "results": [{"label": "Breusch-Pagan p", "value": "0.0001", "step": 0}],
        }
    ),
)
_CSV = "x,y\n" + "\n".join(f"{i},{2 * i + (i % 3)}" for i in range(1, 13)) + "\n"


@pytest.fixture
def app(tmp_path, fake_llm, fake_executor):
    application = create_app(
        runs_dir=tmp_path / "runs", max_concurrent=2, max_upload_bytes=10_000
    )
    application.dependency_overrides[get_run_deps] = lambda: RunDeps(
        make_llm=lambda: fake_llm(*_SCRIPT),
        make_executor=lambda: fake_executor(outputs={_CODE: _OBSERVATION}),
    )
    return application


@pytest.fixture
def client(app):
    with TestClient(app) as test_client:
        yield test_client


def _submit(client, delivery: str = "off") -> str:
    resp = client.post(
        "/runs",
        data={"prompt": "Is x related to y?", "delivery": delivery},
        files={"file": ("data.csv", _CSV, "text/csv")},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["job_id"]


def _wait(client, job_id: str, timeout: float = 10.0) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        body = client.get(f"/runs/{job_id}").json()
        if body["status"] in ("done", "error"):
            return body
        time.sleep(0.02)
    raise AssertionError(f"run {job_id} did not finish in {timeout}s")


def test_healthz(client) -> None:
    assert client.get("/healthz").json() == {"status": "ok"}


def test_submit_then_fetch_returns_a_verified_figure_report(client) -> None:
    body = _wait(client, _submit(client))
    assert body["status"] == "done"
    report = body["report"]
    # The §10 sections are present, the cited p-value verified, and a figure attached.
    assert report["method"] and report["assumption_checks"]
    assert report["results"][0] == {
        "label": "Breusch-Pagan p",
        "value": "0.0001",
        "step": 0,
        "verified": True,
    }
    assert report["figures"][0]["path"].endswith("residuals_vs_fitted.png")


def test_events_stream_the_agent_steps_then_done(client) -> None:
    job_id = _submit(client)
    seen: list[tuple[str | None, str]] = []
    with client.stream("GET", f"/runs/{job_id}/events") as resp:
        assert resp.status_code == 200
        event: str | None = None
        for line in resp.iter_lines():
            if line.startswith("event:"):
                event = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                seen.append((event, line.split(":", 1)[1].strip()))
                if event == "done":
                    break

    step_kinds = [json.loads(data)["kind"] for ev, data in seen if ev == "step"]
    assert "code" in step_kinds and "observation" in step_kinds
    assert "final" in step_kinds and "status" in step_kinds  # composing status
    assert seen[-1][0] == "done"


def test_figure_endpoint_serves_the_png(client) -> None:
    job_id = _submit(client)
    report = _wait(client, job_id)["report"]
    name = report["figures"][0]["path"].split("/")[-1]
    resp = client.get(f"/runs/{job_id}/figures/{name}")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/png" and resp.content


def test_figure_endpoint_rejects_path_traversal(client) -> None:
    job_id = _submit(client)
    _wait(client, job_id)
    assert client.get(f"/runs/{job_id}/figures/..%2Frun.json").status_code in (400, 404)


def test_unknown_job_is_404(client) -> None:
    assert client.get("/runs/nope").status_code == 404
    assert client.get("/runs/nope/events").status_code == 404


def test_rejects_non_csv_and_bad_delivery(client) -> None:
    bad_type = client.post(
        "/runs",
        data={"prompt": "p", "delivery": "off"},
        files={"file": ("data.txt", "x,y\n1,2\n", "text/plain")},
    )
    assert bad_type.status_code == 415
    bad_delivery = client.post(
        "/runs",
        data={"prompt": "p", "delivery": "sideways"},
        files={"file": ("data.csv", _CSV, "text/csv")},
    )
    assert bad_delivery.status_code == 422


def test_rejects_oversize_upload(client) -> None:
    big = "x,y\n" + ("1,2\n" * 5000)  # > the 10_000-byte test cap
    resp = client.post(
        "/runs",
        data={"prompt": "p", "delivery": "off"},
        files={"file": ("data.csv", big, "text/csv")},
    )
    assert resp.status_code == 413


def test_concurrency_cap_returns_429(app, client) -> None:
    # Fill both slots so the next submit is rejected without starting a run.
    assert app.state.registry.try_acquire_slot()
    assert app.state.registry.try_acquire_slot()
    resp = client.post(
        "/runs",
        data={"prompt": "p", "delivery": "off"},
        files={"file": ("data.csv", _CSV, "text/csv")},
    )
    assert resp.status_code == 429
