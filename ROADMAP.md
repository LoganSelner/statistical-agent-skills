# Statistical Agent Skills — Experiment Harness Architecture

Status: **design locked (phase 1 scope)** · Last updated: 2026-06-15 (revised after a
research-validation pass: EdenAI integration, action protocol, task weighting, sandbox
references, and novelty positioning)

This document is the anchor for the project. It records the research framing, the
design decisions we have committed to, the layered architecture, the concrete data
schemas, the experimental condition matrix, and a phased build roadmap. Decisions
explicitly deferred to "future work" are seamed into the architecture (interfaces
defined, implementation omitted) so they become drop-ins rather than refactors.

---

## 1. Research framing

**Question.** Do agent skills actually improve statistical data analysis?

**Operationalization (current phase).** Does providing an agent with *curated
statistics skills* — packaged procedural knowledge loaded at inference time — raise
its **task pass rate** on statistical data-analysis tasks, relative to (a) no skills
and (b) self-generated skills (a control that isolates the model's latent knowledge)?

**Positioning against prior work.**
- SkillsBench (broad, 11 domains): curated skills raised average pass rate by ~16.2
  percentage points but with wide variance, and 16 of 84 tasks got *worse*;
  self-generated skills came in slightly negative (~-1.3pp). Notably, a smaller model
  with curated skills beat a larger model without them.
- SciVisAgentSkills (scientific data analysis + visualization): skills improved mean
  task scores, with efficiency effects that depended on the execution harness.
- DARE (closest neighbor, R statistical ecosystem): gives an agent statistical competence
  via *distribution-aware retrieval* of CRAN functions — i.e. **declarative** tool-discovery,
  not curated **procedural** skills, and not a skills-on/off validity study. Evidence the
  procedural-vs-declarative question is live, not a collision (we seam a skills-vs-RAG
  comparison into future work).
- Empirical ceiling to design around: a 2026 multi-model study put frontier LLMs at ~100%
  on basic statistical *test selection* but diverging on *assumption checking* and
  *validity*, with separate work flagging *fabrication*. The lift from skills concentrates
  in assumptions / correction / traps / anti-fabrication, **not** "which test" — which
  shapes task weighting (§4).
- Gap we target: a **focused study on inferential statistics**, a domain where the
  expensive errors are *methodological* (wrong test, unchecked assumptions,
  overclaiming), evaluated on tasks that do **not** pre-specify the method.

**The constraint insight (shapes task design).** Auto-gradable benchmarks like
InfiAgent-DABench make tasks closed-form partly by baking the method into the task
constraints (which test, which parameters). That removes the exact decision a
statistics skill would help with. Running skills-on vs skills-off on method-constrained
tasks risks measuring nothing. We therefore use **two task arms** (see §4).

**Scope (LOCKED — focused core).** In scope: inferential statistics — hypothesis
testing, confidence intervals, effect sizes, assumption checking (normality, variance,
independence), multiple-comparison correction, basic correlation/association.
Out of scope for now (future): broad ML/predictive modeling, causal inference,
Bayesian methods, time-series forecasting, visualization-heavy tasks.

**Primary outcome (LOCKED).** Task **pass rate** on closed-form answers.
Deferred (seamed, not implemented): validity decomposition (method / assumptions /
interpretation / fabrication), trajectory error-mode classification, and
integrity-under-pressure probing.

---

## 2. Design principles

1. **Harness/experiment seam.** Framework code (config, registry, provenance,
   results, comparison) knows nothing about statistics or skills. Domain code depends
   on the framework, never the reverse.
2. **Everything is a toggleable condition.** Skills, model, agent shape, skill
   resolution level, task arm — all selected by config, never by editing code.
3. **Trajectories are cached separately from scores.** Re-grading must never require
   re-running an agent.
4. **Total provenance.** Every reported number traces to a git SHA + resolved config +
   model snapshot id + sandbox image digest + dataset hash + seed.
5. **Distributions over point estimates.** A stochastic agent demands N trials per
   condition cell and reported variance/CIs.
6. **Seam the deferred work.** Define interfaces for validity scoring, error-mode
   classification, and integrity probing now; implement later.

---

## 3. Experimental factors (condition matrix)

The orchestrator runs the Cartesian product over these axes. Not every axis is swept in
every campaign; "sweep if time" axes default to a single value.

| Factor | Values | Notes |
|---|---|---|
| `model` | small + large pair, plus others | Tests "skills substitute for scale" |
| `skills_mode` | `off` / `curated` / `self_generated` | Core comparison + latent-knowledge control |
| `skill_resolution` | `L0` / `L1` / `L2` / `L3` | Swept within `curated`; see §5 |
| `skill_router` | `forced` / `description_match` / `model_choice` | Factor; sweep if time |
| `agent_arch` | `single` / `reviewer` | Factor; sweep if time |
| `task_arm` | `adopted_constrained` / `authored_open` / `authored_trap` | See §4 |
| `trials` | N (e.g. 5) | Fixed temperature; report distributions |

---

## 4. Task model

Three arms, all scored by pass/fail on a closed-form answer:

- **`adopted_constrained`** — external benchmark tasks as-is (start: InfiAgent-DABench;
  later DSBench, DataSciBench). Method is dictated by constraints. Measures
  *execution-level* help and connects us to the field's framing.
- **`authored_open`** — goal stated, method free. The agent must choose the approach.
  This is where curated skills should earn their keep.
- **`authored_trap`** — a dataset engineered so the *naive* method reaches the wrong
  conclusion while the *correct* method reaches a known closed-form answer (e.g.,
  non-normal data where a t-test misleads but the appropriate test does not). Still
  pass/fail: the ground-truth answer is the one the correct method yields.

**Task weighting (informed by the §1 ceiling finding).** Because "which test" is
near-saturated for frontier models, a mix dominated by test-selection risks a ceiling
effect — skills-on vs skills-off measuring ~nothing, the same hazard the constrained arm
carries. The authored set is weighted toward where the methodological errors actually
live: assumption checking, multiple-comparison correction, the validity-trap arm, and
anti-fabrication. `authored_trap` is a first-class result, not a late add-on.

Concrete schema (illustrative):

```python
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Protocol

class TaskArm(str, Enum):
    ADOPTED_CONSTRAINED = "adopted_constrained"
    AUTHORED_OPEN = "authored_open"
    AUTHORED_TRAP = "authored_trap"

@dataclass(frozen=True)
class Dataset:
    name: str
    path: Path           # csv/parquet, copied into the sandbox per task
    sha256: str          # integrity + provenance

@dataclass(frozen=True)
class ExpectedAnswer:
    value: object        # ground truth for closed-form scoring
    kind: str            # "numeric" | "categorical" | "set" | "regex"
    tolerance: float | None = None     # numeric comparison tolerance
    format_spec: str | None = None     # required output format, if any

@dataclass(frozen=True)
class Task:
    id: str
    arm: TaskArm
    prompt: str
    datasets: tuple[Dataset, ...]
    concepts: tuple[str, ...]          # e.g. ("two_sample_test", "normality")
    method_specified: bool             # True only for the constrained arm
    expected: ExpectedAnswer
    verifier: str                      # registry key for a Verifier
    constraints: str | None = None     # method/workflow restrictions, if any
    difficulty: str | None = None
    source: str | None = None          # provenance: dabench id, "authored", ...
    metadata: dict = field(default_factory=dict)

class Verifier(Protocol):
    def score(self, submitted: str, task: Task) -> "Verdict": ...
```

External benchmarks are normalized into `Task` via per-benchmark adapters; we never
fork their formats into our code.

---

## 5. Skill model

A skill is a folder: `SKILL.md` (YAML frontmatter + markdown body) plus optional
bundled scripts/references. The **progressive-disclosure loader is ours**, so we
control exactly what enters the context window at each level — this is the ablation
axis SkillsBench found mattered most (the jump from examples to bundled resources).

**Stay on the open standard.** Authored skills are valid Anthropic Agent-Skills folders
so they stay portable and comparable to the ecosystem: required frontmatter is `name`
(≤64 chars, lowercase/digits/hyphens) and `description` (≤1024 chars, stating *what it
does and when to use it*); optional bundled `scripts/`, `references/`, `assets/`. The
L0–L3 loader is an ablation layer *on top of* the standard — the standard defines the
artifact, the loader controls how much of it enters context.

| Level | Payload entering context |
|---|---|
| `L0` | name + description only (discovery surface) |
| `L1` | + `SKILL.md` body (instructions) |
| `L2` | + inline executable examples |
| `L3` | + bundled scripts / reference resources |

```python
class SkillResolution(int, Enum):
    L0 = 0; L1 = 1; L2 = 2; L3 = 3

@dataclass(frozen=True)
class SkillResource:
    relative_path: str
    kind: str            # "script" | "reference"

@dataclass(frozen=True)
class Skill:
    name: str
    description: str                       # frontmatter; the L0 discovery surface
    body: str                              # L1
    examples: tuple[str, ...]              # L2
    resources: tuple[SkillResource, ...]   # L3
    path: Path

class SkillLoader(Protocol):
    def render(self, skill: Skill, level: SkillResolution) -> str:
        """Exact context payload for a disclosure level."""

class SkillRouter(Protocol):
    def select(self, task: Task, library: "SkillLibrary") -> list[Skill]:
        """forced/oracle | description_match | model_choice"""
```

**`self_generated` condition.** Before solving, the agent is prompted to write its own
procedural notes for the task; those notes are injected in place of a curated skill.
This isolates whether the benefit comes from the *curated content* or merely from
*thinking procedurally* (prior work found self-generated skills do not help).

**Starter statistics skill library (initial set to author).**
test selection (continuous two-group / paired / >2 groups / categorical) ·
assumption checking before a parametric test (normality, equal variance,
independence) and the nonparametric fallback · multiple-comparison correction ·
effect size + confidence interval reporting · "never report a statistic you did not
compute in code" (anti-fabrication procedure).

---

## 6. Agent

ReAct-style loop: **plan → write code → execute → observe → iterate**, with a
configurable step budget. This mirrors the loop shape used by data-analysis agent
frameworks. Default is single-agent; a `reviewer` variant (statistician + reviewer)
is swappable as a factor.

- **Model access goes through EdenAI** (a hard project constraint — see §6.1). The
  client exposes a provider-agnostic interface internally so the rest of the harness is
  unaware of the gateway; `model` factor values are EdenAI-routed model identifiers.
- **Explicit, inspectable context assembly:** system prompt + task + optional skill
  payload + running scratchpad/observations.
- **Harness-controlled action protocol (LOCKED — not provider-native tool-calling):**
  the model emits a fenced Python code action that the harness parses and runs in the
  sandbox, rather than a provider's function-calling API. This is robust regardless of
  which sub-provider EdenAI routes to (§6.1) and matches the dominant DABench-style
  data-analysis agent shape. The `uwf-rag-experiments` ReAct loop is reused for **loop
  shape only** (plan→act→observe, step budget, forced-final); its native `bind_tools`
  path is deliberately *not* carried over.
- **Trajectory log:** every step records thought, action/code, observation, token
  usage. The final closed-form answer is extracted for scoring.

### 6.1 LLM access via EdenAI

EdenAI is the required model gateway for this research team; a single `EDENAI_API_KEY` is
the only credential. **Decision (LOCKED): use EdenAI's OpenAI-compatible endpoint via the
official `openai` SDK** — not the legacy `langchain-community` `ChatEdenAI` wrapper the RAG
repo used. This drops a heavy dependency and gives direct control over parameters and
provenance:

```python
from openai import OpenAI
client = OpenAI(api_key=os.environ["EDENAI_API_KEY"],
                base_url="https://api.edenai.run/v3")
resp = client.chat.completions.create(
    model="openai/gpt-4o",                  # provider/model — the routed identifier
    messages=[...], temperature=0, max_tokens=...,
)
```

Constraints the design respects:

- **Provider-agnostic above the client.** A thin internal `LLMClient` wraps the SDK call;
  the rest of the harness never imports `openai`. `model` factor values are the routed
  `provider/model` strings (`openai/gpt-4o`, `anthropic/claude-sonnet-4-5`, …).
- **Provenance for free.** The `provider/model` string *is* the exact routed identifier
  (§9), and the response carries `usage.{prompt,completion,total}_tokens` — recorded per
  call.
- **No dependence on native tool-calling or structured output.** The ReAct loop uses the
  harness-parsed code action (§6), so per-sub-provider tool-calling support is irrelevant.
- **`seed` is undocumented on EdenAI — verify empirically per model.** Until confirmed,
  reproducibility rests on fixed temperature + N trials + reported distributions (§9), not
  seeds. Also verify temperature/max_tokens pass-through for each model in the small+large
  pair.
- The RAG repo's `core/retry.py` (tenacity transient-retry) and its best-effort
  usage-extraction pattern are worth porting; its `ChatEdenAI` wrapper is not.

A **local Ollama** provider is also supported through the same OpenAI-compatible client
(`provider: ollama`, keyless) for offline / credit-free development; EdenAI remains the
default and the required gateway for the research runs.

---

## 7. Sandbox / execution

Executing model-generated code is the security- and reproducibility-critical layer.

- **Default:** a pinned Docker image running a **stateful Jupyter kernel** (namespace
  retained between steps, so the agent fixes only the erroneous code next iteration —
  like notebook cells). A **fresh kernel per task** for isolation and reproducibility.
- Resource and wall-clock limits per execution; pinned library versions baked into the
  image; the **image digest is recorded in provenance** (so "scipy chose this default"
  stays reproducible).
- **Executor interface** so a managed backend (e.g. an E2B/Firecracker microVM with a
  Jupyter server) can be swapped in without touching agent code.
- **Reference architectures (don't reinvent):** DSGym runs each agent trajectory in a
  dedicated Jupyter kernel inside a fresh per-trajectory worker container (manager→worker)
  — exactly our "fresh kernel per task"; AutoGen's stateful Jupyter executor is a reference
  for the kernel-session mechanics. Isolation tiers, weakest→strongest: plain Docker
  (shared kernel, our default) → gVisor (syscall-level) → microVM (Firecracker/E2B,
  hardware-level) for untrusted/multi-tenant runs.

```python
class Executor(Protocol):
    def start(self, datasets: tuple[Dataset, ...]) -> "Session": ...
class Session(Protocol):
    def run(self, code: str) -> "ExecResult":   # stdout, stderr, artifacts
        ...
    def close(self) -> None: ...
```

---

## 8. Evaluation (current = pass rate)

- **Deterministic verifier:** numeric-tolerance / regex / exact / set match on the
  closed-form answer. No external model required.
- **Metrics:** pass rate; for multi-part tasks an all-or-nothing per-question score and
  a proportional-by-subquestion score; per-condition deltas with confidence intervals;
  token/step efficiency per condition.
- **Seams left for deferred work (interfaces only):** `ValidityScorer` (method /
  assumptions / interpretation / fabrication), `ErrorModeClassifier` over trajectories,
  `IntegrityProbe` (does a correct conclusion survive leading pressure).

---

## 9. Reproducibility & provenance

Per-run record (written alongside results): git SHA, fully resolved config, the exact
EdenAI-routed model identifier (provider + model + version), sandbox image digest,
dataset hashes, seeds, temperature, token usage, timestamps. **Trajectories and scores
are stored separately** so re-grading is free.
LLM nondeterminism is handled by fixed temperature + N trials + reported distributions;
we note explicitly that even temperature 0 is not fully deterministic across API calls.

---

## 10. Carrying forward proven patterns from the RAG repo

The `uwf-rag-experiments` repo already solved several things well, and those *patterns*
— not the RAG-specific code — are the asset worth reusing: the YAML config system with
`extends:` inheritance and resolution; the decorator-based component registry; the
run-metadata/provenance schema; the results format and comparison engine; and the
tooling/CI/QA gate.

**Implementer's latitude.** Bringing over scaffolding files (`Makefile`,
`pyproject.toml`, `.pre-commit-config.yaml`, the CI workflow, and similar) as starting
points and adapting them to this project is encouraged, but *which* files to port and
how to edit them is **delegated to the implementer's judgment** rather than prescribed
here. The reference implementation is the RAG repo.

These cross-cutting concerns naturally live in an internal `core/` module (config,
registry, provenance, results, compare) that knows nothing about statistics or skills.
Whether that core is ever factored into a separately installable package shared across
repos is a **future decision, not a phase-1 requirement** — this repo is self-contained.

---

## 11. Directory structure (locked for phase 1)

```
statistical-agent-skills/         # importable package: src/statskills/ · Python 3.13
  pyproject.toml  uv.lock  .python-version  Makefile  .pre-commit-config.yaml
  .github/workflows/        # CI: qa gate (fmt, ruff, mypy, tests)
  ARCHITECTURE.md
  src/statskills/           # replaces the RAG repo's ragbench package
    core/                   # config, registry, provenance, results, compare (project-agnostic)
    tasks/
      schema.py             # Task, Dataset, ExpectedAnswer, Verifier
      adapters/             # dabench.py, dsbench.py, datascibench.py -> Task
      authored/             # underspecified + validity-trap task specs
    agent/
      loop.py               # ReAct plan/code/execute/observe
      context.py            # explicit context assembly
      models/               # provider-agnostic LLM clients
      multiagent/           # statistician + reviewer variant (optional)
    skills/
      parser.py             # SKILL.md (frontmatter + body + resources)
      loader.py             # progressive disclosure, L0..L3 control
      router/               # forced | description_match | model_choice
      library/              # the statistics skills (each its own folder)
    sandbox/
      base.py               # Executor / Session interfaces
      jupyter_docker.py     # default: stateful kernel in pinned image
      e2b.py                # optional managed backend
    evaluation/
      verifiers/            # deterministic closed-form checks
      metrics.py            # pass rate, deltas, efficiency
      _deferred/            # ValidityScorer/ErrorModeClassifier/IntegrityProbe seams
    experiments/
      matrix.py             # condition-matrix runner, trial mgmt, caching
  configs/
    base.yaml
    experiments/            # extends: base; one factor per file
  scripts/
    run_experiment.py  compare.py  grade_trajectories.py  make_figures.py
  tests/
  results/                  # trajectories/ and scores/ kept separate
  data/
    benchmarks/  authored/  cache/
```

---

## 12. Build roadmap (phased)

- **Phase 0 — Foundation & repo reconciliation.** The repo is currently a half-merged
  FastAPI template + RAG carryover; reconcile it: **delete** the FastAPI app
  (`src/app/main.py`, `tests/test_app.py`, the uvicorn `Dockerfile`); **rewrite**
  `pyproject.toml` (drop faiss/ragas/chromadb/sentence-transformers/bm25s/pymupdf; rename
  the package `ragbench`→`statskills`; declare the **foundation** deps now —
  pydantic/pyyaml/python-dotenv/tenacity/rich — with the scientific stack
  (numpy/scipy/pandas/statsmodels), `openai`, and a sandbox dep added as their modules
  land in Phase 1+, so each phase's deps are justified by its code); **keep** the
  `.pre-commit-config.yaml`, CI workflow, and `.gitignore`. **Pin Python 3.13** — 3.11
  hits EOL Oct 2026 and statsmodels has no 3.14 wheels yet, so 3.13 is the supported
  sweet spot (full numpy/scipy/pandas/statsmodels support; EOL Oct 2029). **Port** the
  proven `core/` patterns (`registry.py`, the `extends:` config loader, `git.py`
  provenance, `retry.py`) under `statskills`; the neutral message/result types follow
  with the agent layer (Phase 1). Rewrite the README and add `.env.example` with
  `EDENAI_API_KEY`.
- **Phase 1 — Minimal vertical slice.** Sandbox + single-agent ReAct loop +
  `execute_python`; validate end-to-end on ~5 adopted tasks (no skills, no scoring yet).
- **Phase 2 — Scoring + baseline.** Deterministic verifier + pass-rate metrics +
  DABench adapter; produce a clean no-skills baseline.
- **Phase 3 — Skills.** Skill parser/loader + `forced` router; author 3–5 starter
  skills; run `curated` vs `off` on the constrained arm.
- **Phase 4 — The real test.** Author `open` and `trap` tasks; run the arm where skills
  should help; this is the core result.
- **Phase 5 — Scale the matrix.** Add models (small+large), trials, the
  `self_generated` control, and the `L0..L3` sweep.
- **Phase 6 — Analysis & writeup.** Per-task deltas, significance, figures, draft.
- **Future (seamed).** Validity decomposition, error-mode classification, integrity
  probing, multi-agent sweep, broader statistical scope, and a skills-vs-RAG comparison
  (procedural vs declarative knowledge).

---

## 13. Deferred / open decisions

- Specific small+large model pair and the full model set (must be available via EdenAI).
- Exact pass/fail tolerance policy for numeric answers.
- Size and sourcing of the authored task sets.
- Whether EdenAI passes `seed` through (undocumented) — until verified, reproducibility
  rests on fixed temperature + N trials, not seeds.

---

## References

- SkillsBench: Benchmarking Agent Skills for Frontier LLM Agents — skillsbench.ai;
  arXiv 2602.12670.
- SciVisAgentSkills — arXiv 2606.05525.
- "When Skills Don't Help" (negative result, offensive cybersecurity) — arXiv 2605.20023.
- InfiAgent-DABench — arXiv 2401.05507; infiagent.github.io.
- DSBench — arXiv 2409.07703. DataSciBench — arXiv 2502.13897.
- Anthropic Agent Skills open standard — agentskills.io; github.com/anthropics/skills;
  SKILL.md spec at platform.claude.com/docs (agent-skills).
- DARE: distribution-aware retrieval for the R statistical ecosystem — arXiv 2603.04743.
- DSGym: evaluating/training data-science agents; fresh-kernel-per-trajectory sandbox —
  arXiv 2601.16344.
- LLM statistical test-selection vs assumption/validity quality (the ceiling finding) —
  PMC12627256 (NCBI).
- AutoGen Jupyter Code Executor — stateful-kernel reference (microsoft.github.io/autogen).
- EdenAI OpenAI-compatible chat endpoint — docs.edenai.co (`/v3` base URL, `provider/model`).
