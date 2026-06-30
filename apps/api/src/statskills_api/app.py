"""The FastAPI surface — submit a run, stream its steps, fetch the report (ROADMAP §11).

A thin HTTP layer over :mod:`statskills_api.service`. An agent run is many sandboxed
steps over seconds to minutes, so ``POST /runs`` does not block: it validates the
upload, creates a job, launches a **worker thread**, and returns a job id. The client
then streams the agent's steps from ``GET /runs/{id}/events`` (SSE) and fetches the
composed report from ``GET /runs/{id}``. Concurrency, size, and CSV-only checks are
enforced here; the Docker sandbox (in the service) contains the RCE risk.

The app is built by :func:`create_app` so tests can inject a fake LLM + in-memory
executor via :func:`get_run_deps` (no Docker, no API key); ``app`` at module scope is
the production instance for ``uvicorn statskills_api.app:app``.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
import json
import os
from pathlib import Path
import queue
import tempfile
import threading
from typing import Any

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sse_starlette.sse import EventSourceResponse

from statskills.agent.llm import LLM
from statskills.sandbox.base import Executor
from statskills_api import __version__
from statskills_api.jobs import Job, JobRegistry, JobStatus
from statskills_api.service import run_analysis
from statskills_api.stream import StepEvent

MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MiB — generous for a tabular analysis dataset
KEEPALIVE_SECONDS = 15.0  # SSE: emit a ping if no step arrives within this window
DEFAULT_MAX_CONCURRENT = 4
_DELIVERIES = ("off", "injected", "agentic")


@dataclass(frozen=True)
class RunDeps:
    """How a run gets its LLM + sandbox. ``None`` factories → the service builds the
    production defaults (Claude + Docker); tests override with fakes."""

    make_llm: Callable[[], LLM] | None = None
    make_executor: Callable[[], Executor] | None = None
    provider: str = "anthropic"
    model: str | None = None


def get_run_deps() -> RunDeps:
    """Default run dependencies (production). Overridden in tests via
    ``app.dependency_overrides[get_run_deps]`` to inject a fake LLM + executor."""
    return RunDeps()


def _execute(
    job: Job,
    registry: JobRegistry,
    *,
    prompt: str,
    dataset_path: Path,
    delivery: str,
    deps: RunDeps,
) -> None:
    """Worker body (runs on its own thread): drive the run, then settle the job."""
    try:
        report = run_analysis(
            prompt=prompt,
            dataset_path=dataset_path,
            delivery=delivery,
            out_dir=job.out_dir,
            tap=job.tap,
            llm=deps.make_llm() if deps.make_llm else None,
            executor=deps.make_executor() if deps.make_executor else None,
            provider=deps.provider,
            model=deps.model,
        )
        job.report = report
        job.status = JobStatus.DONE
    except Exception as exc:
        job.error = str(exc)
        job.status = JobStatus.ERROR
        job.tap.emit(StepEvent(kind="error", text=str(exc)))
    finally:
        job.tap.close()
        registry.release_slot()


def create_app(
    *,
    runs_dir: Path | None = None,
    max_concurrent: int = DEFAULT_MAX_CONCURRENT,
    max_upload_bytes: int = MAX_UPLOAD_BYTES,
) -> FastAPI:
    """Build the API. ``runs_dir`` holds per-job uploads + figures (a temp dir by
    default); ``max_concurrent`` bounds simultaneous runs; ``max_upload_bytes`` caps the
    dataset size."""
    app = FastAPI(title="statskills-api", version=__version__)
    registry = JobRegistry(max_concurrent=max_concurrent)
    base_dir = runs_dir or Path(tempfile.mkdtemp(prefix="statskills-api-"))
    app.state.registry = registry
    app.state.runs_dir = base_dir

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/runs")
    async def submit_run(
        prompt: str = Form(...),
        delivery: str = Form("agentic"),
        file: UploadFile = File(...),
        deps: RunDeps = Depends(get_run_deps),
    ) -> dict[str, str]:
        if delivery not in _DELIVERIES:
            raise HTTPException(422, f"delivery must be one of {_DELIVERIES}")
        if not (file.filename or "").endswith(".csv"):
            raise HTTPException(415, "a .csv dataset is required")
        contents = await file.read(max_upload_bytes + 1)
        if len(contents) > max_upload_bytes:
            raise HTTPException(413, "dataset exceeds the size limit")
        if not registry.try_acquire_slot():
            raise HTTPException(429, "too many concurrent runs; retry shortly")
        try:
            job = registry.create(base_dir)
            dataset_path = job.out_dir / Path(file.filename or "data.csv").name
            dataset_path.write_bytes(contents)
            threading.Thread(
                target=_execute,
                args=(job, registry),
                kwargs={
                    "prompt": prompt,
                    "dataset_path": dataset_path,
                    "delivery": delivery,
                    "deps": deps,
                },
                daemon=True,
            ).start()
        except Exception:
            registry.release_slot()
            raise
        return {"job_id": job.id}

    @app.get("/runs/{job_id}")
    async def get_run(job_id: str) -> dict[str, Any]:
        job = registry.get(job_id)
        if job is None:
            raise HTTPException(404, "no such run")
        body: dict[str, Any] = {"job_id": job.id, "status": job.status.value}
        if job.report is not None:
            body["report"] = job.report.to_dict()
        if job.error is not None:
            body["error"] = job.error
        return body

    @app.get("/runs/{job_id}/events")
    async def stream_events(job_id: str) -> EventSourceResponse:
        job = registry.get(job_id)
        if job is None:
            raise HTTPException(404, "no such run")

        async def event_source() -> AsyncIterator[dict[str, str]]:
            while True:
                try:
                    event = await run_in_threadpool(job.tap.get, KEEPALIVE_SECONDS)
                except queue.Empty:
                    if job.status in (JobStatus.DONE, JobStatus.ERROR):
                        yield _done_event(job)
                        return
                    yield {"event": "ping", "data": "{}"}
                    continue
                if event is None:  # end-of-stream sentinel
                    yield _done_event(job)
                    return
                yield {"event": "step", "data": json.dumps(event.to_dict())}

        return EventSourceResponse(event_source())

    @app.get("/runs/{job_id}/figures/{name}")
    async def get_figure(job_id: str, name: str) -> FileResponse:
        job = registry.get(job_id)
        if job is None:
            raise HTTPException(404, "no such run")
        if Path(name).name != name:  # reject path separators / traversal
            raise HTTPException(400, "invalid figure name")
        path = job.out_dir / "figures" / name
        if not path.is_file():
            raise HTTPException(404, "no such figure")
        return FileResponse(path, media_type="image/png")

    _mount_static(app)
    return app


def _mount_static(app: FastAPI) -> None:
    """Optionally serve a built single-page frontend at ``/`` — the one-command demo.

    Off by default. If ``STATSKILLS_WEB_DIST`` names an existing directory, its contents
    are served as static files (SPA-style) — mounted **last**, so the API routes above
    always win. This is a generic "serve a static dir" capability: the API never imports
    or builds ``apps/web``, and with the env var unset (tests, CI) nothing is mounted.
    """
    dist = os.environ.get("STATSKILLS_WEB_DIST")
    if not dist or not Path(dist).is_dir():
        return
    app.mount("/", StaticFiles(directory=dist, html=True), name="web")


def _done_event(job: Job) -> dict[str, str]:
    return {"event": "done", "data": json.dumps({"status": job.status.value})}


app = create_app()
