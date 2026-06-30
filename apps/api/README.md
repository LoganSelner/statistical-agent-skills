# statskills-api

The FastAPI backend for the statskills web demo (ROADMAP §11). It exposes the
research harness as a service: submit an analysis run (a prompt + an uploaded dataset
+ a skills/delivery toggle), stream the agent's steps live over SSE, and fetch the
composed, traceable [`Report`](../../src/statskills/reporting/). The skills toggle is
the demo — run the same regression with delivery `off` vs `agentic` and watch the
assumption check appear and the conclusion change.

It is a **consumer** of `statskills`: the dependency points inward (`api → statskills`),
the agent is never modified, and live streaming rides the harness's existing
LLM/sandbox dependency-injection seam — a *tap* wraps the injected `LLM` + sandbox
`Session` and emits a step event per turn, leaving the agent byte-for-byte unchanged.

## Run it

```bash
uv sync --all-packages                     # installs the core + this member
ANTHROPIC_API_KEY=… uv run uvicorn statskills_api.app:app --reload
```

Real runs need `ANTHROPIC_API_KEY` (the Claude provider) and Docker (the sandbox). The
test suite needs neither — it injects a fake LLM and the local executor.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/runs` | Submit a run (multipart: `prompt`, `file` CSV, `delivery`) → `{job_id}` |
| `GET` | `/runs/{id}/events` | SSE stream of the agent's steps until completion |
| `GET` | `/runs/{id}` | Job status + the composed `Report` (when done) |
| `GET` | `/runs/{id}/figures/{name}` | A report figure PNG |
| `GET` | `/healthz` | Liveness |
