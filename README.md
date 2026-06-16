# statistical-agent-skills

An experiment harness investigating one question: **do curated agent skills improve an
LLM's performance on inferential-statistics data-analysis tasks?**

It drives a ReAct-style agent (model access via the **EdenAI** gateway) over data-analysis
tasks inside a sandboxed Python kernel, under toggleable conditions — skills
on / off / self-generated, skill disclosure level, task arm — and scores closed-form
answers with deterministic verifiers. See **[ROADMAP.md](ROADMAP.md)** for the research
framing, the layered architecture, and the phased build plan.

> **Status: Phase 1 — vertical slice.** The harness runs end-to-end: a single-agent
> ReAct loop with a CodeAct action protocol (harness-parsed Python, not provider
> tool-calling) drives the EdenAI client over a stateful sandbox kernel (Docker default,
> network-isolated), validated on five authored tasks. Skills and deterministic scoring
> land in later phases; the project-agnostic `core/` (registry, `extends:` config
> loading, provenance, retry) underpins it all.

## Prerequisites

- **Python 3.13** — pinned via `.python-version`. (3.11 reaches EOL Oct 2026 and the
  scientific stack has no 3.14 wheels yet, so 3.13 is the supported sweet spot.)
- **[uv](https://github.com/astral-sh/uv)** for dependency and environment management.

## Quickstart

```bash
make bootstrap     # install Python (if needed), sync deps, install git hooks
make qa            # fmt-check + typecheck + lint + tests
```

Run `make help` for all targets. Common ones:

| Target | What it does |
| --- | --- |
| `make bootstrap` | Install Python, sync deps, install git hooks |
| `make test` | Run tests |
| `make typecheck` | Mypy (strict) |
| `make lint` / `make fmt` | Ruff check / autofix + format |
| `make qa` | Full quality gate (fmt-check + types + lint + tests) |

## Configuration

Model access goes through an OpenAI-compatible client with two providers:

- **EdenAI** (default) — a hosted gateway. Copy the example env file and add your key:
  ```bash
  cp .env.example .env     # then set EDENAI_API_KEY=...
  ```
- **Ollama** — a local, keyless server. Use `--provider ollama` (defaults to
  `qwen2.5-coder:7b`) or the ready-made `configs/slice_ollama.yaml`; override the
  endpoint with `OLLAMA_BASE_URL` if the default `http://localhost:11434/v1` can't
  reach it.

## Run the vertical slice

```bash
make sandbox-image       # build the pinned execution image (one time, needs Docker)
make slice               # run the agent over the 5 authored tasks
```

Code executes in a fresh, **network-isolated** Docker container per task; if Docker is
unavailable the run fails rather than silently executing locally. Trajectories and a
`run.json` with provenance (git SHA, provider, model id, sandbox image digest) are
written under `results/`. `--executor local` opts into an unsandboxed local kernel for
trusted debugging only.

To run fully locally with Ollama (no credits needed):

```bash
ollama pull qwen2.5-coder:7b
uv run python scripts/run_slice.py --config configs/slice_ollama.yaml
```

## Project layout

```
src/statskills/
  core/              # project-agnostic harness: registry, config, provenance, retry
  agent/             # EdenAI client, CodeAct action parser, ReAct loop, trajectory
  sandbox/           # Executor interface + Docker (default) & local backends + image
  tasks/             # Task schema + authored slice tasks
configs/             # YAML configs (extends: inheritance)
data/authored/       # small bundled datasets for the authored tasks
scripts/run_slice.py # end-to-end Phase 1 runner
tests/               # pytest suite
ROADMAP.md           # research framing + architecture + phased plan
```

## Development

`uv` + `ruff` (lint + format) + `mypy` (strict) + `pytest` + `pre-commit`. CI runs the
same quality gate on every push and pull request.
