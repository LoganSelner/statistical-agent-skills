# CLAUDE.md — orientation for AI agents working in this repo

This file is for coding agents (Claude Code, Codex, …). Read it first, then dive into the doc it
points to for the task at hand.

## What this is

A reproducible research harness answering: **do curated agent skills improve an LLM's performance on
inferential-statistics tasks?** It runs a CodeAct agent over data-analysis tasks in a sandbox, under
toggleable skill conditions, and scores closed-form answers — then aggregates trials into bootstrapped
condition deltas.

**Status:** research spine complete across two frontier models (Haiku + Sonnet) — on Claude Haiku 4.5,
*agent-activated* skill delivery beats no-skills **+12pp [+4, +20]** and beats injection (the lever is
*relevance routing*; local models can't engage at all). The deliverable track (reporting layer + web
app) is built. Active: the validity decomposition and a higher-N / ≥3-model campaign.

## The map (and which doc to read)

- **[ARCHITECTURE.md](ARCHITECTURE.md)** — the system as built, layer by layer, design decisions,
  extension points. Read before changing code.
- **[FINDINGS.md](FINDINGS.md)** — every experimental result + the reproduction commands. Read before
  proposing experiments (so you don't repeat one).
- **[ROADMAP.md](ROADMAP.md)** — research framing, phase status, and the prioritised next steps.
- **[README.md](README.md)** — setup + how to run.

Code lives in `src/statskills/{core,agent,skills,sandbox,tasks,evaluation,experiments}`; YAML in
`configs/` (`configs/experiments/` = grid manifests); thin CLIs in `scripts/`; tests in `tests/`.

## Conventions (follow these)

- **Tooling:** `uv` for everything; `make qa` is the gate (ruff lint+format, **mypy strict**, pytest).
  Run it before you call anything done. Line length **88**.
- **Workflow:** non-trivial changes get a **plan + a new branch first** (`type/short-desc`, e.g.
  `feat/…`, `fix/…`, `refactor/…`, `docs/…`). Open a PR off `main`; **expect a Codex review** and
  reconcile it before merge (it can be wrong — analyse, don't rubber-stamp).
- **Commits** end with `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`; **PR bodies** end
  with `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.
- Commit/push only when asked; keep commits logical and each one QA-green (bisectable).

## Hard constraints (don't break these)

- **Harness ↔ experiment seam:** the agent (`agent/`) must stay unaware of skills/arms/scoring. Only
  the experiment layer decides conditions.
- **`evaluation/` is stdlib-only.** No numpy/scipy/pandas/statsmodels in the harness runtime — that
  stack is sandbox-only (it runs *model* code) and dev/test-only. Bootstrap CIs use `random`/`statistics`.
- **`src/` never imports `scripts/`.** Orchestration is library policy; CLIs are thin adapters.
- **Docker sandbox hard-fails** if Docker is unavailable — never add a silent local fallback (the
  `local` executor is for tests only).

## Running things

```bash
make sandbox-image                                              # build the pinned sandbox (once)
uv run python scripts/run.py --config configs/slice_ollama.yaml # one config end-to-end
uv run python scripts/gen_authored_data.py                      # generate the trap datasets
uv run python scripts/run_matrix.py configs/experiments/haiku_grid.yaml          # a grid
uv run python scripts/run_matrix.py configs/experiments/disclosure_grid.yaml --trials 1  # smoke
```

Providers (set in a config's `llm.provider`): `ollama` (local, keyless — set `OLLAMA_BASE_URL` if not
localhost), `anthropic` (Claude — needs `ANTHROPIC_API_KEY`; native SDK), `edenai` (gateway, currently
credit-blocked). Results land in `results/` (**gitignored**); grade with `scripts/grade.py`, compare
with `scripts/compare.py`.

## Footguns (learned the hard way)

- **YAML `off` is a boolean.** In manifests/`arms` maps, quote it (`"off"`). The parser rejects an
  unquoted one, but don't trip it.
- **Local coder models are below the skill-invocation threshold** — they never read agentic skills.
  Don't re-run that experiment expecting engagement; use a frontier model (see FINDINGS).
- **Frontier models emit Markdown** — the categorical verifier unwraps edge emphasis (`**Yes**`); keep
  it that way.
- The SSH key is passphrase-protected (the user runs `ssh-add` when the agent can't push).
