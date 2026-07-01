# Statistical Agent Skills — Research Roadmap

Status: **Research spine complete across two frontier models (Phases 0–8); the deliverable track (reporting layer + web app) is built. Active: the validity decomposition (§9, §15) and a higher-N / ≥3-model campaign.**

This document is the project anchor: research framing, committed design decisions, the
experimental condition matrix, and the phased roadmap. It is the *design + plan* doc — for the
system **as built** see [ARCHITECTURE.md](ARCHITECTURE.md), and for **what the experiments found**
see [FINDINGS.md](FINDINGS.md).

**Headline result (see FINDINGS):** on **Claude Haiku 4.5**, agent-activated ("agentic") skill
delivery raises trap-arm pass rate **+12pp [95% CI +4, +20]** over no-skills and beats *injecting*
the same skills — via *selective* engagement (the model reads only the skill it needs). The
precondition is a frontier model: local coder models never invoke an offered skill (0/55 trials).
One trap (`correlation`) resists every condition — a task-framing limit, not a skill one.

**What that result rests on now (updated).** The original +12pp was **monogenic** — carried by a
single task (`trap-multiple-comparisons`, 0→60%), with a per-trial mechanism too noisy to call at N=5
(one MC solve followed the *assumption-checks* read, and one MC-reading trial still failed). Phase 6
**broke that single-task dependency**: four authored *regression* traps give large, multi-procedure
gains (injected +95pp / agentic +75pp) with a clean read→pass mechanism (6/6). The live caveats are now
different — the Haiku/Sonnet engagement difference is **n=2** (model-dependent, not a capability law;
§0), and the per-trial "right skill → solves" story wants the **higher-N campaign** (§15).

---

## 0. The sharpened research spine

The original question — "do curated skills help statistical analysis?" — is largely answered at the
*general* level by SkillsBench, and the most useful, least-covered contribution this project can make
is sharper:

> **The correctness lever is *relevance routing*, not the delivery channel.** A correct, on-topic skill
> still distracts when force-injected on a task that does not need it; delivering *only the relevant*
> skill recovers the gain — whether the experimenter routes it (oracle injection) or the agent
> self-selects (activation). Agent-activation is only a *proxy* for relevance routing, and how good a
> proxy it is **varies by model** — in our two-model probe Haiku under-reads (stays selective, so
> activation helps) while Sonnet over-reads (loses selectivity, re-importing the distraction); we treat
> this as a model-dependent calibration, **not** a demonstrated capability law (see §1, and SRA below).

**The field caught up to the general phenomenon — so it is no longer the novelty.** Since this project
began, several concurrent works measured that injected skills can degrade performance: SWE-Skills-Bench
(skills help only marginally and can *degrade* via context interference — a holistic-skill /
focused-task mismatch), SkillsInjector (packing skills degrades through attention dispersion), and
SkillReducer (compressing skills *improves* quality — less-is-more). This connects to the older
distraction line (GSM-IC; GSM-DC at EMNLP 2025, where accuracy falls as distractor *count* rises).
"Injected skills distract; selectivity helps" is now corroborated design wisdom, not our contribution.

**What remains distinctive (after a closer read of the nearest neighbors).** The two *mechanistic*
results — the delivery-channel decomposition (inject-all ≈ off, inject-relevant ≈ agentic) and the
model-dependent engagement (Haiku under-reads, Sonnet over-reads) — are, on closer inspection,
**corroborated rather than unprecedented**: Skill-Retrieval-Augmentation runs the same
oracle / inject / progressive-disclosure arms and reports loading is *model-dependent, not monotonic
with scale*; "Agentic Skills in the Wild" runs the same force-load / agent-decide / distractor
comparison and finds higher loading need not help; DecisionBench ablates the same
preloaded-vs-on-demand delivery axis; Skill-Shadowing decomposes the same drop into selection-error vs
context-overhead. So we present these as **clean, contamination-free confirmation in a controlled
statistics setting**, not as first-to-find — and we do **not** claim a "capability reversal": at n=2
(Haiku, Sonnet) the engagement difference is confounded with model identity, exactly the caution SRA
raises. What *is* distinctive is (1) the **inferential-statistics validity-trap domain** — every
neighbor lives in software engineering, tool/customer-service, or general agentic tasks — and (2) the
**framing shift**: in a capability-saturated domain the model is *able* but *confidently invalid*, so a
skill's job is **validity correction**, not capability extension. The route to a genuinely novel
contribution is (3) the **validity decomposition** (§9, now an active direction): measuring whether a
skill fixes the *specific* validity error — a dimension the tool-domain neighbors structurally cannot
access, because their tasks have no "executes fine but is invalid" failure mode.

The statistics validity-trap instrument is the distinctive, **contamination-free**, deterministically-
verified testbed this rests on. **This is the spine; the professor's deliverables (regression, a
report, a clickable app) ride alongside it on the same core — see §3.**

---

## 1. Research framing

**Question (operational).** Does the *way* a curated statistics skill is delivered — not at all,
force-injected, or agent-activated — change an agent's **task pass rate** on inferential-statistics
tasks, and how does that interact with model capability?

**Positioning against prior work.**
- SkillsBench (broad, 11 domains): curated skills raised average pass rate ~16.2pp but with wide
  variance; 16 of 84 tasks got *worse*; self-generated skills ~−1.3pp; a smaller model with skills
  beat a larger one without.
- SciVisAgentSkills (scientific analysis + viz): skills improved mean scores, with harness-dependent
  efficiency effects — and the explicit caution that skills must be studied *with* the harness.
- DARE (closest neighbor, R ecosystem): statistical competence via *distribution-aware retrieval* of
  CRAN functions — **declarative** tool-discovery, not curated **procedural** skills, and not a
  skills-on/off study. (We seam a skills-vs-RAG comparison into future work.)
- Empirical ceiling to design around: a 2026 multi-model study put frontier LLMs at ~100% on basic
  *test selection* but diverging on *assumption checking* and *validity*, with separate work flagging
  *fabrication*. The lift from skills concentrates in assumptions / correction / traps /
  anti-fabrication — **not** "which test" — which shapes task weighting (§5).
- Gap we target (§0): not *whether* delivery matters (now shown concurrently) but *what the lever is*
  — relevance routing vs the activation channel — and how engagement **varies by model** (model-
  dependent per SRA, not yet a capability trend), in an inferential-statistics validity-trap domain, on
  tasks that do **not** pre-specify the method.

**The constraint insight (shapes task design).** Auto-gradable benchmarks like InfiAgent-DABench make
tasks closed-form partly by baking the method into the task constraints. That removes the exact
decision a statistics skill would help with. Running skills-on/off on method-constrained tasks risks
measuring nothing (confirmed: skills **hurt** −25pp on the constrained arm). We therefore center the
**trap arm** (§5).

**Scope (LOCKED — focused core, now including inferential regression).** In scope: inferential
statistics — hypothesis testing, confidence intervals, effect sizes, assumption checking (normality,
variance, independence), multiple-comparison correction, correlation/association, **and inferential
regression: coefficient inference + assumption diagnostics** (heteroskedasticity/robust SEs, omitted-
variable bias & Simpson's paradox, influential points/leverage, multicollinearity, non-linearity).
Out of scope: **regression-as-prediction / ML / AutoML**, causal inference beyond confounding
illustrations, Bayesian methods, time-series forecasting.

**Primary outcome (LOCKED).** Task **pass rate** on closed-form answers. **Now promoted to an active
direction (§9, §15):** the **validity decomposition** — does the skill fix the *specific* validity
error (method / assumptions / interpretation / fabrication) — the one axis the tool-domain literature
cannot reach, and thus our clearest route to a distinctive contribution. Still seamed: trajectory
error-mode classification, integrity-under-pressure probing.

### Concurrent work & positioning (mid-2026)

The area moves fast; keeping positioning current is a standing practice (see §0). As of mid-2026:

- **Delivery/injection is now a measured phenomenon — including its close neighbors.** Beyond the
  general result (SWE-Skills-Bench 2603.15401, SkillsInjector 2605.29794, SkillReducer 2603.29919,
  SKILL0 2604.02268, ClawsBench 2604.05172, SkillJuror 2606.11543), the *nearest* work overlaps our own
  arms: Skill-Retrieval-Augmentation (2604.24594; oracle / inject / progressive-disclosure arms + a
  model-dependent-loading analysis), "Agentic Skills in the Wild" (2604.04323; force-load /
  agent-decide / distractor + loading rates), DecisionBench (2605.19099; a preloaded-vs-on-demand
  ablation), and Skill-Shadowing (2605.24050; selection-error vs context-overhead decomposition). So
  our delivery-decomposition and model-dependent-engagement results **corroborate** this cluster in a
  clean statistics setting; they are not the novelty. The distinctive residue is the **domain**, the
  **validity-correction framing**, and the promoted **validity decomposition** (§9).
- **The statistics-agent domain is heating up — but on capability, not skills.** StatABench
  (2606.22977), StatEval, DSAEval, StatQA, and QRData evaluate statistical *capability*; none studies
  *skills* or uses validity traps. They are the right domain citations and candidate **external task
  arms** (a contamination-caveated comparison to our authored traps).
- **Methodology posture vs 2026 norms.** Two deliberate strengths: the authored traps are
  **contamination-free by construction** (contamination is a headline credibility problem this year),
  and scoring is **deterministic / closed-form** (sidestepping contested LLM-as-judge reliability). The
  trade-off is instrument size — ~9 traps at N=5 — well below field norms; the higher-N campaign (§15)
  and an external benchmark arm are the fixes. Our engagement metric aligns with the emerging
  **Skill Coverage** adequacy line (arXiv 2606.20659).

---

## 2. Design principles

1. **Harness/experiment seam.** Framework code (config, registry, provenance, results, comparison)
   knows nothing about statistics, skills, or reporting. Domain code depends on the framework, never
   the reverse.
2. **The agent is the system under test and stays untouched.** Reporting, the web app, and the
   experiment runner are all *consumers* of the agent core, never modifications of it.
3. **Everything is a toggleable condition.** Delivery, dose, resolution, model, agent shape, task arm
   — all selected by config, never by editing code.
4. **Compose and grade from saved trajectories; never re-run the agent.** Scoring, engagement
   extraction, and report composition are all trajectory consumers.
5. **Total provenance.** Every reported number traces to a git SHA + resolved config + exact model
   identifier + sandbox image digest + dataset hash. Every *report* claim traces to the computed
   observation it came from.
6. **Distributions over point estimates.** A stochastic agent demands N trials per cell with reported
   variance/CIs.
7. **Pre-1.0 latitude (LOCKED).** Nothing is published or in use; reproducibility of *old* runs is
   explicitly **not** a constraint. We may break schemas, restructure, and delete dead paths to reach
   the right end-state — used for *correctness/cleanliness*, not as licence to rewrite code that is
   already good.
8. **Seam the deferred work.** Define interfaces for validity scoring, error-mode classification, and
   integrity probing now; implement later.

---

## 3. Two tracks on one core

The project now has two tracks that **share the agent core** and never touch each other:

- **Research track (the spine).** Closed-form trap tasks → conditions → pass/fail scoring → matrix
  campaigns. Answers §0.
- **Deliverable track (the professor's ask).** A regression-capable agent that, from a prompt + a
  dataset, produces a **traceable report** (§10), usable through a **clickable web app** (§11).

They are not in tension. Regression traps double as both research instrument and deliverable
substrate (§5). The web app exposes the **skills on/off toggle**, so the deliverable *is* a live
demonstration of the research finding (§11). The seam (§2) is what lets both ride the same untouched
agent.

---

## 4. Experimental factors (condition matrix)

The orchestrator runs the Cartesian product over these axes; "sweep if time" axes default to a single
value. **`delivery` is the headline factor** (it carries §0).

| Factor | Values | Notes |
|---|---|---|
| `model` | Anthropic-first: `haiku` / `sonnet` / `±opus` (native SDK); cross-vendor later | Tests capability interaction + "skills substitute for scale" |
| `delivery` | `off` / `injected` / `agentic` | **Headline.** off = plain agent; injected = skill body in context; agentic = agent reads skill files on demand |
| `dose` | `relevant_only` / `all` | **For `injected` only.** The dose-response arm that turns "injection distracts" into a causal test |
| `resolution` | `L0` / `L1` / `L2` / `L3` | For `injected`; how much of the skill enters context (§6) |
| `task_arm` | `authored_trap` (primary) / `authored_open` / `adopted_constrained` | See §5 |
| `agent_arch` | `single` / `reviewer` | Factor; sweep if time |
| `trials` | N (≥20 for headline cells; budget is not a constraint) | Deterministic baselines mean N buys real CI width |

**Concrete arm labels** map onto `(delivery, dose, resolution)` — e.g. the as-built `off`/`L1`/`L2`/
`agentic` arms are `off`, `injected·all·L1`, `injected·all·L2`, `agentic`. The new `injected·
relevant_only` arm is the dose-response addition. `self_generated` (content-origin control) remains
seamed for future work.

---

## 5. Task model

Three arms, all scored by pass/fail on a closed-form answer:

- **`authored_trap` (primary).** A dataset engineered so the *naive* method reaches the wrong
  conclusion while the *correct* method reaches a known closed-form answer. Pass/fail: the ground
  truth is the answer the correct method yields.
- **`authored_open`.** Goal stated, method free; the agent must choose the approach.
- **`adopted_constrained`.** External benchmark tasks as-is (method dictated). Kept for comparability;
  known to be a ceiling/anti-skill arm (−25pp), so it is a control, not a focus.

**Regression is the trap engine (the convergence).** Inferential regression is the richest source of
*missing-procedure* traps in statistics — exactly the kind needed to break the single-task dependency
(§15). Each is closed-form ("is the effect of X on Y significant?" → Yes-naive / No-correct):
- omitted-variable bias / **Simpson's paradox** (sign flips after conditioning on a confounder),
- **heteroskedasticity** (naive SEs significant, robust SEs not),
- **influential points / leverage** (one point drives the slope),
- **multicollinearity**, **non-linearity** laundered into a misleading linear slope.

This is why broadening the instrument (research) and "regression, specifically" (professor) are the
**same authoring work**. The matching `regression-diagnostics` skill powers both the traps and the
deliverable agent.

**Task weighting (informed by the §1 ceiling finding).** Because "which test" is near-saturated for
frontier models, the authored set is weighted toward where methodological errors live: assumption
checking, multiple-comparison correction, the regression traps, anti-fabrication. `authored_trap` is a
first-class result, not a late add-on.

*(The `Task` / `Dataset` / `ExpectedAnswer` / `Verifier` schema is unchanged from the as-built version
— see [ARCHITECTURE.md](ARCHITECTURE.md). Regression traps are normal `authored_trap` entries with
deterministic datasets generated by `scripts/gen_authored_data.py`.)*

---

## 6. Skill model

A skill is a valid **Anthropic Agent-Skills folder** (portable, ecosystem-comparable): required
frontmatter `name` (≤64 chars) and `description` (≤1024 chars, *what it does and when to use it*);
optional bundled `scripts/`, `references/`, `assets/`. The **progressive-disclosure loader is ours**,
an ablation layer *on top of* the standard, controlling exactly what enters context per level:

| Level | Payload entering context |
|---|---|
| `L0` | name + description only (discovery surface) |
| `L1` | + `SKILL.md` body |
| `L2` | + inline executable examples |
| `L3` | + bundled scripts / reference resources |

Under `agentic` delivery the agent instead *reads* skill files from the sandbox on demand (selective
by construction — this is the mechanism the headline measures). Under `injected` delivery the loader
renders the chosen level directly into context.

**Skill library.** As built: test selection · assumption checks · multiple-comparison correction ·
effect-size/CI reporting · anti-fabrication ("never report a statistic you did not compute"). **To
add: `regression-diagnostics`** (assumption checks + robust SEs + confounding/leverage/collinearity
procedure), serving both the regression traps and the deliverable agent.

*(`SkillResolution` / `Skill` / `SkillLoader` / `SkillRouter` schema unchanged — see ARCHITECTURE.md.
`self_generated` content control remains seamed for future work.)*

---

## 7. Agent & model access

ReAct/CodeAct loop: **plan → write code → execute → observe → iterate**, configurable step budget,
single-agent default (`reviewer` variant swappable). Context assembly is explicit and inspectable
(system prompt + task + optional skill payload + scratchpad/observations). The **action protocol is
harness-parsed (LOCKED — not provider-native tool-calling):** the model emits a fenced Python code
action the harness runs in the sandbox. This is robust across providers and matches the dominant
data-analysis agent shape.

**Model access (LOCKED — EdenAI retired).** EdenAI was the original gateway but ended up credit-
blocked and unused; under the pre-1.0 latitude (§2.7) it is **dropped as dead weight**. A thin
internal `LLMClient` wraps backends:
- **`anthropic`** — native Anthropic SDK, the frontier instrument (`haiku`/`sonnet`/`opus`).
- **`ollama`** — local, keyless, for offline/free iteration.
- **cross-vendor (future)** — added via direct provider SDKs (OpenAI/Google) for external validity,
  behind the same `LLMClient`; the rest of the harness never imports a provider SDK.

`model` factor values are explicit provider model identifiers; provenance records the exact model
string + API version + token usage per call (§12). Worth porting from the RAG repo: transient-retry
(`tenacity`) and best-effort usage extraction.

---

## 8. Sandbox / execution

Executing model-generated code is the security- and reproducibility-critical layer.

- **Default:** a pinned Docker image running a **stateful Jupyter kernel** (namespace retained between
  steps); **fresh kernel per task** for isolation. Resource + wall-clock limits; pinned library
  versions; **image digest recorded in provenance**.
- **+ matplotlib** in the image (new), so the agent can produce regression diagnostic figures
  (residuals-vs-fitted, QQ, leverage) for the report (§10).
- **Executor interface** so a managed backend (E2B/Firecracker microVM) can be swapped in untouched.
- **Reference architectures (don't reinvent):** DSGym's manager→worker fresh-kernel-per-trajectory
  sandbox; AutoGen's stateful Jupyter executor. Isolation tiers weakest→strongest: plain Docker
  (default) → gVisor → microVM (for untrusted/multi-tenant).

*(`Executor` / `Session` protocol unchanged — see ARCHITECTURE.md.)*

---

## 9. Evaluation (current = pass rate) + engagement as a first-class metric

- **Deterministic verifier:** numeric-tolerance / regex / exact / set match on the closed-form answer.
  Markdown-tolerant. No external model required.
- **Metrics:** pass rate; for multi-part tasks all-or-nothing and proportional-by-subquestion scores;
  per-condition deltas with bootstrap CIs; token/step efficiency per condition.
- **Engagement (BUILT — closed the one real rigor gap).** Skill engagement used to live only in raw
  trajectories (`open("skills/<name>.md")` actions), recovered by hand. The stdlib-only
  **engagement extractor** (`evaluation/engagement.py`) now scans saved trajectories into per-`(task,
  trial)` skill-read records and folds them — plus the **read×pass contingency** — into versioned
  artifacts (`engagement.jsonl` per run + an `engagement` block per cell in `matrix.json`). This
  turned "selective engagement" from a narrative into a measurement (validated against the Haiku run:
  read-rate 16%, MC read-freq 0.8, others 0). At N=5 the *cell-level* read×pass barely separates
  (no-reads pile up on already-solved tasks); the **per-task** read-frequency isolates the mechanism,
  and the higher N of §15 will power the per-trial story the headline can't yet support.
- **Now active — the `ValidityScorer` (§0 novelty direction).** Beyond pass/fail, score whether the
  skill corrected the *specific* validity error (method / assumptions / interpretation / fabrication),
  deterministically where possible (was the assumption check run? was the correction applied?) with a
  validated judge only where unavoidable — preserving the contamination-free / deterministic strengths.
- **Seams left for deferred work (interfaces only):** `ErrorModeClassifier`, `IntegrityProbe`.

---

## 10. Reporting layer (NEW — deliverable track)

A new `src/statskills/reporting/` module, the **sibling of `evaluation/`**: where evaluation *scores*
a trajectory, reporting *narrates* one. It is a pure trajectory consumer — it **never re-runs the
agent**.

- **Structured + schema-defined.** The report is a typed object with sections: question & data summary
  → method chosen and why → assumption checks performed and their results → results with effect sizes
  and uncertainty → interpretation → caveats. (Mirrors the current report-generation pattern of a
  structured-output schema filled by the model, rather than one free-form blob.)
- **Traceable.** Every quantitative claim carries a pointer to the computed observation it came from —
  the `anti-fabrication` skill expressed as an *output contract*. The report cannot state a number the
  agent did not compute; the reader can click any value back to the code that produced it. (Mirrors
  clinical report-gen systems' inline source indices + a decoupled interactive front end.)
- **Figures.** For regression, the agent emits residuals-vs-fitted, QQ, and leverage/influence plots
  as part of its assumption checks; the composer embeds them (needs matplotlib, §8) so the diagnostic
  is *visible*.
- **Output.** A structured object the web app renders richly, plus a rendered Markdown/HTML artifact
  for sharing (PDF optional).

---

## 11. Web app & monorepo topology (NEW — deliverable track)

**Topology decision (LOCKED): single monorepo, hard internal boundary.** The library is the
importable core; the web app is a deploy-only area that depends *inward*. Rationale: app and core
co-evolve constantly for a solo researcher, so atomic commits beat a publish-bump-reinstall dance
across two repos; nothing is published and old-version reproducibility is off the table (§2.7), so the
usual reasons to split do not apply. The boundary that matters is the **dependency rule at repo
scale:** `web → api → statskills`, never the reverse. The research harness and stdlib-only
`evaluation/` must keep working with **zero web dependencies installed** (own manifests, own CI jobs;
the JS stack never touches the core).

**Backend shape.** An agent run is many sandboxed steps over seconds–minutes, so it cannot be a
blocking endpoint: submit a run (prompt + uploaded dataset + skill config) → background **job** →
the agent's steps **stream** to the client (server-sent events; WebSockets unnecessary) → on
completion the client fetches the composed report. At single-user research scale, **FastAPI
background tasks + an in-process job registry** suffice — *no Celery/Redis*. The existing Docker
sandbox already handles the RCE concern of running user-prompted code on user-uploaded data; the
backend enforces upload-size, wall-clock, and concurrency limits.

**The toggle is the demo.** The UI exposes **skills off/on** (and ideally delivery: off / injected /
agentic). Running the same regression with skills off vs agentic, and *watching* the assumption check
appear and the conclusion change, makes the deliverable and the research narrative the **same
artifact** — the best possible outcome for two supposedly-orthogonal asks.

---

## 12. Reproducibility & provenance

Per-run record (alongside results): git SHA, fully resolved config, the **exact model identifier
(provider + model + API version)**, sandbox image digest, dataset hashes, temperature, token usage,
timestamps. **Trajectories and scores stored separately** so re-grading/re-reporting is free. No
provider passes a usable seed, so reproducibility rests on fixed temperature + N trials + reported
distributions; frontier models are not deterministic even at temperature 0 — which is what produced
meaningful CIs. (Pre-1.0: provenance is for *current* defensibility, not migration of old runs.)

---

## 13. Carrying forward proven patterns from the RAG repo

The reusable *patterns* (not RAG code) remain the asset: the `extends:` YAML config system, the
decorator-based component registry, the run-metadata/provenance schema, the results/comparison engine,
the tooling/CI/QA gate. These live in an internal `core/` that knows nothing about statistics, skills,
or reporting.

---

## 14. Directory structure (monorepo target)

> For the module-by-module layout **as built**, ARCHITECTURE.md is the source of truth. This is the
> *target* topology after the deliverable track lands.

```
statistical-agent-skills/                 # monorepo
├─ pyproject.toml  uv.lock  Makefile  .pre-commit-config.yaml   # statskills core
├─ src/statskills/
│   ├─ core/         # config, registry, provenance, results, compare (project-agnostic)
│   ├─ tasks/        # schema + adapters/ + authored/ (+ inferential-regression traps)
│   ├─ agent/        # CodeAct loop, context, LLMClient (anthropic | ollama | future)  — UNCHANGED core
│   ├─ skills/       # parser, L0–L3 loader, router/, library/ (+ regression-diagnostics)
│   ├─ sandbox/      # stateful Jupyter-in-Docker (+ matplotlib), Executor/Session
│   ├─ evaluation/   # verifiers, metrics, + engagement extractor + read×pass   (stdlib-only)
│   ├─ reporting/    # NEW: trajectory → structured, traceable report with figures
│   └─ experiments/  # condition-matrix runner, trial mgmt, caching
├─ configs/  scripts/  tests/  data/  results/      # trajectories/ and scores/ separate
└─ apps/
    ├─ api/          # FastAPI backend; imports statskills; background jobs + SSE
    └─ web/          # clickable UI (own package.json); skills/delivery toggle
.github/workflows/   # core QA gate (py) + api checks + web build/lint as SEPARATE jobs
```

---

## 15. Build roadmap

### History (as built; the path diverged from the plan where evidence demanded)

- **Phase 0–1 — Foundation + vertical slice. ✅** Repo reconciled to `statskills` (FastAPI template +
  RAG carryover removed); sandbox + single-agent CodeAct loop validated end-to-end. Python 3.13.
- **Phase 2 — Scoring + baseline. ✅** Deterministic closed-form verifier + pass-rate/N-trial metrics
  + DABench adapter.
- **Phase 3 — Skills. ✅** Parser/loader (L0–L3) + `forced` router + five statistics skills;
  `curated` vs `off`. *Finding:* on the **constrained** arm skills **hurt** (−25pp) — method baked in
  → payload distracts. Motivated the trap arm.
- **Phase 4 — Trap arm. ✅** Five validity-trap tasks + the N-trials/bootstrap-CI harness.
- **Phase 5 — Scale the matrix. ✅ (with a pivot).** Condition-matrix runner; swept `{7B,14B} ×
  {off,L1,L2}`, then added **agentic** delivery and a model axis. *Findings:* local models give a
  fragile selection-only 7B/L1 win and **never invoke agentic skills (0/55)** — invocation is emergent
  above local scale. Added a **frontier provider (Claude, native SDK)**; **Haiku 4.5: agentic 72% >
  off 60% (+12pp [+4,+20]) > injected 56% (injected ≈ off, n.s.).** Bonus: clean-architecture pass +
  Markdown-tolerant verifier.

### Forward plan (foundation-first — perfect the instrument before the headline campaign)

Build **and smoke-validate** each step; the full results campaign waits until the instrument is broad
and the metrics are first-class. (Smoke/sanity runs to confirm a phase works are encouraged; the
deadline is not close, so quality wins over speed.)

1. **Engagement as a first-class metric (§9). ✅ BUILT.** `evaluation/engagement.py` extracts skill
   reads + the read×pass contingency into `engagement.jsonl` + `matrix.json`; validated against the
   Haiku run (it reproduces the hand numbers). Unblocks the honest mechanism claim.
2. **Broaden the instrument with inferential-regression traps (§5). ✅ BUILT + smoke-validated.** Four
   regression traps (`authored_regression`) + the `regression-diagnostics` skill. Haiku fails them
   **0%** unaided (single-task dependency broken); skills give **injected +95pp / agentic +75pp**, and
   the delivery effect **flips** (injected > agentic, because every task needs the skill) with a clean
   read→pass 6/6 mechanism. See FINDINGS Phase 6. Sharpens §0: the sign of injected−agentic is
   task-mix-dependent.
3. **Injection dose-response arm (§4). ✅ BUILT + smoke-validated.** A `relevant` oracle router +
   5-arm sweep {off, all·L1, all·L0, relevant·L1, agentic} on both task arms. **Causally explains the
   flip:** the *distractor payload* is the lever — inject-all helps 0pp on the original arm while
   inject-relevant recovers the full +12pp, and `relevant·L1` ≈ `agentic` (selectivity is the
   mechanism, by injection or activation). Bonus: descriptions (L0) carry nameable fixes but the body
   is needed for procedural ones. See FINDINGS Phase 7. Closes the §0 loop.
4. **Model axis — Sonnet 4.6 alongside Haiku (§4 model factor). ✅ BUILT + smoke-validated.** A
   `model × delivery` grid on both arms. **Model choice reframes the thesis** (n=2, model-dependent per
   SRA — not a capability law): the lever is *relevance
   routing*, not "agentic" per se — Haiku under-reads (selective, agentic wins), Sonnet over-reads
   (non-selective, agentic ties inject-all and loses to relevant-injection); oracle-relevant injection
   is the robust optimum (Sonnet + relevant = **100% on both arms**). Capability shrinks headroom
   (regression off 5%→50%). See FINDINGS Phase 8.
5. **Reporting layer (§10). ✅ BUILT (text + traceability + figures).** A `reporting/` module narrates
   a saved trajectory into a typed `Report`: a deterministic evidence/verify backbone (every cited
   number must appear in its observation — `compute-dont-fabricate` mechanized) wrapped around an
   injected, mockable LLM-composer (schema + validate/retry), a Markdown renderer, and
   `scripts/report.py`. **Figures** (`figures.py`): report-time regression diagnostics
   (residuals-vs-fitted / QQ / Cook's distance) **gated** on the agent's actual checks and **cited** to
   the step — generated offline from the dataset+fit (no agent change, no sandbox change), via the
   optional `reporting` extra. Validated end-to-end on a real regression trajectory (narrates the
   robust-SE check, cites every step, embeds a residuals-vs-fitted plot, flags nothing fabricated).
6. **Web app (§11)** then a **headline campaign**.
   - **Backend (`apps/api`). ✅ BUILT.** A FastAPI service (a uv-workspace member, FastAPI
     out of the core runtime) exposes submit→stream→report: `POST /runs` launches a worker
     thread, `GET /runs/{id}/events` streams the agent's steps over SSE, `GET /runs/{id}`
     returns the composed traceable `Report` (+ a figure endpoint). Live streaming rides the
     agent's LLM/sandbox **dependency-injection seam** via a pass-through *tap*, so the agent
     stays byte-for-byte untouched (the trajectory is identical with or without it). The
     off/injected/agentic toggle maps onto the skills block — the demo *is* the finding.
     Hermetic tests (fake LLM + in-memory executor, no Docker/API) on a separate CI job.
   - **Frontend (`apps/web`). ✅ BUILT.** A Vite + Svelte 5 + TS single-page app (a Node
     package outside the Python workspace; `web → api → statskills`, its own CI job) renders
     the run: a submit form with the **off/injected/agentic** toggle, the agent's steps
     streaming live over SSE, and the traceable, figure-bearing `Report`. Relative URLs only
     (dev = Vite proxy; prod = the API's opt-in `STATSKILLS_WEB_DIST` static mount, one
     origin). Flipping the toggle and re-running *is* the demo — the §0 finding made
     interactive. The web app (§11) is now complete.
   - **Headline campaign** (higher N over the `model × delivery` grid + `make_figures.py`) — plus
     **Opus and a cross-vendor model** (GPT-5.5 / Gemini 3.1 Pro): enough model points to tell whether
     the Haiku/Sonnet engagement difference is a *trend* or a *model-idiosyncrasy* (SRA cautions the
     latter), and to check whether the effect **washes out** as frontier models solve the traps
     unaided (the mid-capability-window hypothesis). Deferred; tightens the CIs for the writeup.

7. **Validity decomposition (the novelty direction — active).** Build the `ValidityScorer` (§9): for
   each trajectory, score whether the skill corrected the *specific* validity error, not just
   pass/fail — the one measurement the tool-domain neighbors (SRA, in-the-wild, DecisionBench)
   structurally cannot make. This is where the contribution stops being a clean replication and becomes
   distinctive; run it across the ≥3-model sweep above.

### Future (seamed)

`self_generated` content control; `description_match` / `model_choice` routers; error-mode
classification, integrity probing; multi-agent sweep; skills-vs-RAG (procedural vs declarative).
(**Validity decomposition** and **cross-vendor / ≥3-model sweep** are promoted to the active plan above.)

---

## 16. Open decisions

- Frontier tiers beyond Haiku for the headline campaign (Sonnet certainly; Opus if warranted) and
  exact N.
- How many regression traps to author to make the effect rest on ≥6–8 procedures rather than one.
- Whether the `correlation` gap closes under a deliberation-forcing task framing.
- Report output: confirm figures are wanted (assumed yes — regression makes them worthwhile); PDF
  export optional.
- Web UI stack specifics (framework, styling) — deferred to implementation; the contract (jobs + SSE +
  toggle, inward dependency rule) is what's locked.
- **External benchmark arm.** Whether to adopt a StatABench / StatEval slice as a comparable
  (contamination-caveated) arm alongside the authored traps, to grow the instrument past ~9 tasks.
- **L0-description vs L1-body probe.** Phases 6–7 showed the L0 discovery surface itself flips
  *nameable* fixes; a probe should separate that description nudge from the body-read effect.
- **≥3-model + cross-vendor sweep** (Opus, GPT-5.5 / Gemini 3.1 Pro) to tell whether the Haiku/Sonnet
  engagement difference is a *trend* or a *model-idiosyncrasy* (SRA's caution) — not to confirm a
  "reversal."
- **Validity-decomposition scope.** How to score "fixed the specific validity error" reliably —
  deterministic checks where possible, a validated judge only where unavoidable — keeping the
  contamination-free / deterministic strengths.
- **Mid-capability-window test.** Whether to include Opus / a frontier cross-vendor model specifically
  to see if the delivery effect survives or washes out as traps become solvable unaided.

---

## References

- SkillsBench — skillsbench.ai; arXiv 2602.12670.
- SciVisAgentSkills — arXiv 2606.05525.
- "When Skills Don't Help" (negative result, offensive cybersecurity) — arXiv 2605.20023.
- Agent Skills for LLMs: Architecture, Acquisition, Security (the "context rot / reasoning noise"
  framing) — arXiv 2602.12430.
- Externalization in LLM Agents (progressive disclosure as reasoning-noise mitigation) — arXiv 2604.08224.
- GSM-DC: distraction dose-response in reasoning — arXiv 2505.18761 (EMNLP 2025); GSM-IC: Shi et al. 2023.
- SkillFlow (skill retrieval/use-rate) — arXiv 2504.06188; SkillRouter — arXiv 2603.22455;
  SkillLearnBench — arXiv 2604.20087; Skill-Inject — arXiv 2602.20156.
- Multi-agent insulation from context interference — medRxiv 2025.08.22.25334049.
- InfiAgent-DABench — arXiv 2401.05507. DSBench — arXiv 2409.07703. DataSciBench — arXiv 2502.13897.
- DARE (R ecosystem, distribution-aware retrieval) — arXiv 2603.04743.
- DSGym (fresh-kernel-per-trajectory sandbox) — arXiv 2601.16344. AutoGen Jupyter executor —
  microsoft.github.io/autogen.
- LLM statistical test-selection vs assumption/validity quality (ceiling finding) — PMC12627256.
- Anthropic Agent Skills open standard — agentskills.io; github.com/anthropics/skills.
- Report-generation patterns: structured-output schema (LlamaIndex); two-layer structured-summary +
  interactive front end with traceability (clinical RAG+LLM report gen, MDPI AI 6(8):188).
- Concurrent delivery/injection work (the general phenomenon): SWE-Skills-Bench — arXiv 2603.15401;
  SkillsInjector — arXiv 2605.29794; SkillReducer — arXiv 2603.29919; SKILL0 — arXiv 2604.02268;
  ClawsBench — arXiv 2604.05172; SkillJuror — arXiv 2606.11543; Skill Coverage / SBC — arXiv 2606.20659.
- Nearest-neighbor work (same delivery/loading arms): Skill-Retrieval-Augmentation (oracle / inject /
  progressive-disclosure + model-dependent loading) — arXiv 2604.24594; "How Well Do Agentic Skills
  Work in the Wild" (force-load / agent-decide / distractor) — arXiv 2604.04323; DecisionBench
  (preloaded-vs-on-demand delivery ablation) — arXiv 2605.19099; Skill-Shadowing (selection-error vs
  context-overhead) — arXiv 2605.24050; "stronger backbones defer more" — arXiv 2606.14476.
- Statistics-agent benchmarks (capability, not skills): StatABench — arXiv 2606.22977; StatEval,
  DSAEval, StatQA, QRData.
- Frontier model panel (mid-2026): Claude Opus 4.8 / Sonnet 4.6 / Haiku 4.5; GPT-5.5; Gemini 3.1 Pro.
