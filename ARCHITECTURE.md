# Architecture (as built)

This describes the system **as implemented today**. For the research framing and the
phased plan see [ROADMAP.md](ROADMAP.md); for what the experiments found see
[FINDINGS.md](FINDINGS.md).

The codebase is a reproducible research harness: it drives a single-agent CodeAct loop over
data-analysis tasks in a sandbox, under toggleable skill conditions, and scores closed-form
answers with deterministic verifiers — then aggregates many trials into bootstrapped
condition deltas.

## Two load-bearing principles

1. **Harness ↔ experiment seam.** The agent never knows whether skills are on, which arm a
   task belongs to, or how it is scored. The *experiment layer* decides conditions and
   feeds the agent only a rendered task (and, in `injected` mode, a skill payload appended
   to the system prompt). This keeps the skills-on/off comparison honest — the no-skills
   baseline is byte-for-byte the plain agent.
2. **The Dependency Rule.** Source dependencies point inward: `core` ← everything; the
   library (`src/statskills/`) never imports from `scripts/` (the CLIs are outermost
   adapters that call inward). A direct corollary: **`evaluation/` is stdlib-only** — the
   scientific stack (numpy/scipy/pandas/statsmodels) is *not* a harness runtime dependency;
   it lives only in the sandbox image (where model code runs) and the dev/test group. The
   bootstrap CIs in `evaluation/trials.py` are written against `random`/`statistics`.

## Layers

```
src/statskills/
  core/         project-agnostic plumbing: registry, extends-config, provenance, retry, types
  agent/        the LLM clients + CodeAct loop (the thing under test)
  skills/       parse / disclose / route curated skills; the statistics library
  sandbox/      isolated code execution (Docker default; local for tests)
  tasks/        Task schema + loaders (authored slice/trap, DABench adapter)
  evaluation/   deterministic verifiers, metrics, N-trial bootstrap CIs, run-artifact I/O
  reporting/    narrate a trajectory into a typed, traceable report (deliverable track)
  experiments/  the run orchestrator + the condition-matrix runner
configs/        YAML configs with `extends:` inheritance (experiments/ = grid manifests)
scripts/        thin CLIs: run, run_matrix, grade, compare, report, gen_authored_data, fetch_dabench
```

### `core/` — plumbing
`registry.py` (a decorator registry so components resolve by name from config),
`config/loading.py` (`load_yaml_with_inheritance` — deep-merge `extends:`, with an
impl-selector replacement rule), `provenance.py` (`RunProvenance.capture()` — git SHA + dirty
flag), `retry.py` (`retry_transient` — a tenacity factory; type-based, provider-agnostic),
`types.py` (the neutral `Message`/`LLMResponse`). Nothing here imports the layers above it.

### `agent/` — the system under test
- **LLM access** behind a narrow protocol `LLM` (`model` + `complete(messages)`): `llm.py`
  has `LLMClient` (OpenAI-compatible — EdenAI and Ollama) and `build_llm` (the single build
  path; a `PROVIDERS` preset dict). `anthropic_client.py` is a **second** `LLM` implementation
  using the native Anthropic SDK (Claude); `build_llm` dispatches `provider="anthropic"` to it.
- **Action protocol** `action.py` — CodeAct: `parse_action` turns one model turn into a
  `CodeAction` (a fenced ```python block) or `FinalAnswer` (`FINAL ANSWER:` marker). This is
  harness-parsed, *not* provider tool-calling, so the loop is robust behind any gateway.
- **Loop** `loop.py` — `ReActAgent.run`: plan→code→execute→observe, up to a step budget; one
  sandbox session per task. Accepts `skill_payload` (injected) **or** `skill_discovery` +
  `skill_files` (agentic — see below). `trajectory.py` is the serialisable per-step log.

### `skills/` — curated agent skills (the treatment)
`parser.py` reads an Anthropic-style `SKILL.md` (frontmatter + body + `## Examples` + bundled
resources) into a `Skill`. `loader.py` controls **progressive disclosure** — `render(skill,
level)` for L0 (name+desc) / L1 (+body) / L2 (+examples) / L3 (+resources), and
`render_discovery` (the L0 list). A router selects which skills a task gets: `router/forced.py`
(all skills — the oracle "everything available") or `router/relevant.py` (only the task's
concept-mapped skill(s) — the oracle-relevance arm for the injection dose-response).
`context.py` (`SkillContext` + `build_skill_context`) turns a config `skills:` block into
a per-task payload, keyed on **`delivery`**:
- `injected` → a single rendered payload appended to the system prompt (the agent is passive).
- `agentic` → an L0 *discovery* surface in the prompt + the skill bodies staged as **files in
  the sandbox**, which the agent reads on demand (`open("skills/<name>.md")`) — progressive
  disclosure the Claude-Code way. `library/statistics/` holds six skills (the five starter skills +
  `regression-diagnostics`).

### `sandbox/` — isolated execution
`base.py` defines the `Executor`/`Session` protocols. `docker.py` (default) runs each session
in a fresh `--network none` container of a pinned image and **hard-fails if Docker is absent —
never a silent local fallback**. `local.py` is an in-process executor for tests only.
`Executor.start(datasets=…, skills=…)` stages read-only dataset and skill files; `session.py`
is the stateful-kernel subprocess driver.

### `tasks/` — what the agent is asked
`schema.py` (`Task`, `Dataset`, `ExpectedAnswer`/`AnswerKey`). `loader.py` dispatches a config
`tasks:` spec to a task list: `authored` (slice), `authored_trap` (the 5 traps),
`authored_regression` (the 4 inferential-regression traps), `dabench` (adapter).
`authored/trap_tasks.py` + `authored/regression_trap_tasks.py` + `scripts/gen_authored_data.py`
generate the trap datasets (engineered so the *naive* method misleads); each arm is self-checked by
`tests/test_*trap_tasks.py` (correct method == truth, naive != it).

### `evaluation/` — deterministic scoring (stdlib-only)
`verifiers.py` (`ClosedFormVerifier` — per-`AnswerKey` numeric/categorical/exact/set/regex
checks), `grading.py` (`grade` over saved trajectories — never re-runs the agent),
`metrics.py` (pass-rate/PASQ aggregates), `trials.py` (`summarize_trials` + percentile
**bootstrap CIs** resampling whole trials), `compare.py` (`compare_trials` — the per-arm delta
CI), `engagement.py` (`extract_engagement` + `summarize_engagement` — skill-file reads and the
**read×pass** contingency from saved trajectories, the same trajectory-consumer pattern as
grading), `runs.py` (run-directory I/O: `grade_run` / `load_scores` / `load_engagement`),
`_deferred.py` (seamed interfaces for validity/error-mode/integrity scoring — interfaces only).

### `reporting/` — narrate a trajectory (deliverable track)
The sibling of `evaluation/`: where evaluation *scores* a saved trajectory, reporting *narrates*
one into a typed, traceable `Report` (the §10 sections). A **deterministic backbone** —
`evidence.py` (`observed_steps`: the citable code-step/observation pairs) + `verify.py` (every
cited number must appear in its step's observation — the `compute-dont-fabricate` skill mechanized,
stdlib-only) — wraps an **injected, mockable LLM-composer** (`compose.py`: prompt → schema JSON →
validate + bounded retry → `verify`). `figures.py` adds report-time regression diagnostics
(residuals-vs-fitted / QQ / Cook's distance) generated from the same dataset+fit, **gated** on the
diagnostics the agent actually ran and **cited** to the step — lazily importing matplotlib + the
scientific stack via the optional `reporting` extra (so the harness stays light). `render.py` emits
Markdown with inline `[step N]` indices, a `## Figures` section, and unverified-claim flags;
`schema.py` is the frozen-dataclass `Report`/`Claim`/`Figure`. Like grading, it **never re-runs the
agent** (figures visualise, they don't recompute findings); the composer uses the agent's `LLM`.
CLI: `scripts/report.py`.

### `experiments/` — orchestration
`runner.py` — `execute_run_config(cfg, *, out_dir, …)` (the testable core; optional injected
`llm`/`sandbox`) and `execute_run(path, …)`. It builds the LLM/sandbox/agent, runs N trials ×
tasks, and writes `trajectories.jsonl` + `run.json`. `matrix.py` — the condition-matrix runner:
`parse_manifest` (a grid = an `arms` overlay map + `{model, config, arm}` cells), `run_matrix`
(pure; side effects injected via `MatrixIO`), `default_matrix_io` (the production wiring), and
`compose_cell_config` (model base + arm overlay → effective config).

## Data flow

```
config.yaml ─▶ execute_run ─▶ results/run-*/trajectories.jsonl   (one record per trial×task)
                            └▶ results/run-*/run.json             (provenance + resolved config)
trajectories ─▶ grade_run ─▶ scores.jsonl                        (re-gradeable; no agent re-run)
scores (×arms) ─▶ compare_trials / run_matrix ─▶ matrix.json     (per-arm deltas + CIs)
```

Run/grade are separate so re-grading (e.g. after a verifier fix) never re-runs the agent.

## Key design decisions (and why)

- **CodeAct, not native tool-calling.** Actions are harness-parsed fenced Python, so the loop
  works behind any OpenAI-compatible gateway and any model regardless of tool-calling support.
- **Stdlib-only `evaluation/`.** Keeps the harness runtime free of the heavy scientific stack;
  that stack is pinned in the sandbox image (its digest recorded in provenance) and dev-only.
- **Native Anthropic SDK, not an OpenAI-compat shim.** The study's whole point is testing
  Claude faithfully; a compat layer is a validity risk. Claude is a second `LLM` impl behind
  the same protocol — exactly what the protocol is for.
- **Agentic delivery = skills as sandbox files.** Mirrors how skills actually work in industry
  (Claude Code): the agent reads `SKILL.md` with its normal tools. Reuses the existing code
  action (no bespoke "activate" verb) and makes the engagement signal observable in the trace.
- **Orchestration lives in the library, CLIs are thin.** `execute_run` is high-level policy, so
  it belongs inward (testable, importable by the matrix runner) — not in `scripts/`.
- **A grid is one self-contained manifest.** Skill overlays are defined once in an `arms` map;
  cells are `{model, base-config, arm}`. No per-(model×arm) config cross-product.
- **Components resolve by name via the registry**, so conditions are configured in YAML, not
  code (routers, verifiers, executors).

## Extension points

- **A model/provider** — add a `PROVIDERS` preset in `agent/llm.py` (OpenAI-compatible) or a
  new `LLM` impl + `build_llm` branch (like `anthropic_client.py`).
- **A skill** — add a `SKILL.md` folder under `skills/library/statistics/` (frontmatter
  name+description, body, optional `## Examples`/resources).
- **A task set** — add a loader + register it in `tasks/loader.py`; add a verifier `kind` if
  needed.
- **A verifier / router** — register a new `@registry.register("verifier"|"router", name)` impl.
- **A skills router** — `forced` (all) and `relevant` (oracle concept→skill map) exist;
  `description_match` / `model_choice` (learned relevance) are designed-for but unbuilt — drop a
  new impl into `skills/router/`.

## Provenance & reproducibility

Each `run.json` records the git SHA (+ dirty flag), the resolved provider/model/temperature/
max_tokens/request_timeout, the sandbox image digest, the task set, N trials, and the skills
condition. Bootstrap CIs are seeded (`random.Random(0)`), so intervals are reproducible.
Determinism otherwise rests on fixed temperature + N trials (not provider seeds — see
ROADMAP §13).
