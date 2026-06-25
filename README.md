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

Model access goes through a small `LLM` interface with three providers:

- **EdenAI** (default) — a hosted OpenAI-compatible gateway. Copy the example env file
  and add your key:
  ```bash
  cp .env.example .env     # then set EDENAI_API_KEY=...
  ```
- **Ollama** — a local, keyless server. Use `--provider ollama` (defaults to
  `qwen2.5-coder:7b`) or the ready-made `configs/slice_ollama.yaml`; override the
  endpoint with `OLLAMA_BASE_URL` if the default `http://localhost:11434/v1` can't
  reach it.
- **Anthropic (Claude)** — the frontier provider, via the **native Anthropic SDK** (not
  an OpenAI-compatible shim). Set `provider: anthropic` (e.g.
  `configs/experiments/trap_haiku.yaml`, defaulting to `claude-haiku-4-5`) and
  `ANTHROPIC_API_KEY`.

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
uv run python scripts/run.py --config configs/slice_ollama.yaml
```

For long unattended runs (e.g. the multi-trial experiments), set these on the Ollama host
so the model stays resident on the GPU and doesn't reload or get evicted between calls —
the main cause of slow local runs:

```bash
export OLLAMA_KEEP_ALIVE=30m        # keep the model loaded between calls
export OLLAMA_MAX_LOADED_MODELS=1   # avoid VRAM contention from extra models
export OLLAMA_FLASH_ATTENTION=1     # optional: faster attention
```

Each request is also bounded by `llm.request_timeout` (default 240s) so a stalled
generation fails fast instead of hanging.

## Experiments

A single config runs via `scripts/run.py --config <cfg>` (writes `results/run-<ts>/`).

Experiments run through the **condition-matrix runner**: a manifest enumerates
`(model, arm)` cells, each run once over N trials, and each skill arm is compared to its
own model's single baseline with a bootstrapped pass-rate delta CI. The simplest case is
a 2-cell off-vs-curated pair; the Phase-5 diagnostic sweeps `{7B, 14B} × {off, L1, L2}`
on the authored trap arm:

```bash
uv run python scripts/gen_authored_data.py            # generate the trap CSVs first
uv run python scripts/run_matrix.py configs/experiments/disclosure_grid.yaml
uv run python scripts/run_matrix.py configs/experiments/disclosure_grid.yaml --trials 1  # smoke
```

Cells land in `results/matrix-<ts>/<model>__<arm>/`, with a `matrix.json` summary
(pass-rate CIs + per-arm deltas + per-task frequencies). Pass `--out <dir> --resume` to
continue an interrupted grid without re-running completed cells.

**Skill delivery** (`skills.delivery` in a config) controls *how* curated skills reach the
agent: `injected` (default) appends skill bodies to the system prompt; `agentic` shows only
the L0 names+descriptions and stages each skill as a file in the sandbox, so a body enters
context only when the agent chooses to read it (progressive disclosure, as in industry
skill systems). The `engagement_grid.yaml` manifest sweeps `{off, L1 injected, agentic}` to
test whether faithful delivery changes whether the agent applies a skill.

## Project layout

```
src/statskills/
  core/              # project-agnostic harness: registry, config, provenance, retry
  agent/             # EdenAI client, CodeAct action parser, ReAct loop, trajectory
  sandbox/           # Executor interface + Docker (default) & local backends + image
  tasks/             # Task schema + authored slice/trap tasks + DABench adapter
  skills/            # skill parser/loader (L0–L3), forced router, statistics library
  evaluation/        # verifiers, metrics, N-trials CIs, run-artifact I/O (runs.py)
  experiments/       # condition-matrix runner (model × disclosure grid)
configs/             # YAML configs (extends: inheritance); experiments/ = grid cells
data/authored/       # small bundled datasets for the authored tasks
scripts/             # run, run_matrix, grade, compare CLIs (thin adapters)
tests/               # pytest suite
ROADMAP.md           # research framing + architecture + phased plan
```

## Development

`uv` + `ruff` (lint + format) + `mypy` (strict) + `pytest` + `pre-commit`. CI runs the
same quality gate on every push and pull request.
