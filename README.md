# statistical-agent-skills

An experiment harness investigating one question: **do curated agent skills improve an
LLM's performance on inferential-statistics data-analysis tasks?**

It drives a ReAct-style agent (model access via the **EdenAI** gateway) over data-analysis
tasks inside a sandboxed Python kernel, under toggleable conditions — skills
on / off / self-generated, skill disclosure level, task arm — and scores closed-form
answers with deterministic verifiers. See **[ROADMAP.md](ROADMAP.md)** for the research
framing, the layered architecture, and the phased build plan.

> **Status: Phase 0 — foundation.** The project-agnostic harness `core/` (component
> registry, YAML config loading with `extends:` inheritance, run provenance, retry policy)
> is in place. The agent, sandbox, tasks, skills, and evaluation layers land in later
> phases.

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

Model access goes through **EdenAI** (OpenAI-compatible endpoint, reached with the
`openai` SDK). Copy the example env file and add your key:

```bash
cp .env.example .env     # then set EDENAI_API_KEY=...
```

## Project layout

```
src/statskills/
  core/              # project-agnostic harness: registry, config, provenance, retry
tests/               # pytest suite
configs/             # YAML experiment configs (extends: inheritance)   [later phases]
ROADMAP.md           # research framing + architecture + phased plan
```

## Development

`uv` + `ruff` (lint + format) + `mypy` (strict) + `pytest` + `pre-commit`. CI runs the
same quality gate on every push and pull request.
