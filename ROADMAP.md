# Statistical Agent Skills — Research Roadmap

Status: **Phases 0–5 built; first result in; consolidating and broadening (Phase 6+).**

This document is the project anchor: research framing, committed design decisions, the
experimental condition matrix, and the phased roadmap. It is the *design + plan* doc — for the
system **as built** see [ARCHITECTURE.md](ARCHITECTURE.md), and for **what the experiments found**
see [FINDINGS.md](FINDINGS.md).

**Headline result (see FINDINGS):** on **Claude Haiku 4.5**, agent-activated ("agentic") skill
delivery raises trap-arm pass rate **+12pp [95% CI +4, +20]** over no-skills and beats *injecting*
the same skills — via *selective* engagement (the model reads only the skill it needs). The
precondition is a frontier model: local coder models never invoke an offered skill (0/55 trials).
One trap (`correlation`) resists every condition — a task-framing limit, not a skill one.

**What that result is currently made of (the honest caveat that drives the next phase).** The whole
+12pp is carried by a **single task** — `trap-multiple-comparisons` (0→60%); agentic is flat on the
other four traps. And at the per-trial level the mechanism is noisy: one MC solve happened after
reading the *assumption-checks* skill (not the MC one), and one trial that *did* read the MC skill
still failed (read-MC → 2/3 passed; didn't → 1/2). So the aggregate effect is real but **monogenic**,
and the per-trial "reads the right skill → solves" story is **not** established at N=5. Breaking that
single-task dependency is the top priority (§15).

---

## 0. The sharpened research spine

The original question — "do curated skills help statistical analysis?" — is largely answered at the
*general* level by SkillsBench, and the most useful, least-covered contribution this project can make
is sharper:

> **Skill *delivery mechanism* is a correctness lever, not just a token-budget one.** A correct,
> generally-relevant skill becomes a *distractor* when force-injected on a task that does not need it;
> agent-activated delivery's *selectivity* is what makes skills net-positive — and the size/direction
> of this effect interacts with model capability.

This sits precisely at the intersection of two literatures that have not been connected:

- **Distraction.** Irrelevant context degrades reasoning, with a measured dose-response (GSM-IC; and
  GSM-DC at EMNLP 2025, where accuracy falls as distractor count rises). This line studies distractor
  *sentences in the problem* — never *skills* or *delivery*.
- **Progressive disclosure.** The field asserts that injecting full skill bodies causes "context rot"
  and that detailed instructions "become reasoning noise rather than guidance" — but as *design
  wisdom*, justified by token economy, **not** measured as a *correctness* effect. Adjacent skills
  work optimizes *which* skills reach the agent (SkillFlow, SkillRouter measure retrieval/use-rate) or
  studies skill *generation* (SkillLearnBench) and *security* (Skill-Inject) — none treats
  preload-vs-activate as a controlled correctness variable.

Our `injected = off + MC − mwu − welch` decomposition is the measured, within-model version of what
the literature only asserts. (Converging evidence from a different lever: a multi-agent study found
that giving each task its own worker *insulates the model from context interference* by not diluting
attention across irrelevant material.) The statistics-trap domain is the **testbed**, not the
headline — closed-form, method-free, verifiable, with a known structure for *where* a procedure is
genuinely missing.

**This reframing is the spine; the professor's deliverables (regression, a report, a clickable app)
ride alongside it on the same core — see §3.**

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
- Gap we target (§0): the delivery-mechanism-as-correctness-lever question, in a focused inferential
  domain, on tasks that do **not** pre-specify the method.

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

**Primary outcome (LOCKED).** Task **pass rate** on closed-form answers. Deferred (seamed, not
implemented): validity decomposition (method / assumptions / interpretation / fabrication), trajectory
error-mode classification, integrity-under-pressure probing.

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
- **Seams left for deferred work (interfaces only):** `ValidityScorer`, `ErrorModeClassifier`,
  `IntegrityProbe`.

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
   `model × delivery` grid on both arms. **Capability reframes the thesis:** the lever is *relevance
   routing*, not "agentic" per se — Haiku under-reads (selective, agentic wins), Sonnet over-reads
   (non-selective, agentic ties inject-all and loses to relevant-injection); oracle-relevant injection
   is the robust optimum (Sonnet + relevant = **100% on both arms**). Capability shrinks headroom
   (regression off 5%→50%). See FINDINGS Phase 8.
5. **Reporting layer (§10). ✅ BUILT (text + traceability).** A new `reporting/` module narrates a
   saved trajectory into a typed `Report`: a deterministic evidence/verify backbone (every cited
   number must appear in its observation — `compute-dont-fabricate` mechanized) wrapped around an
   injected, mockable LLM-composer (schema + validate/retry), plus a Markdown renderer and
   `scripts/report.py`. Validated end-to-end on a real regression trajectory (it narrates the
   robust-SE assumption check, cites every step, flags nothing fabricated). **Next slice:** figures
   (residuals/QQ/leverage — needs the matplotlib sandbox bump, §8). **← next deliverable step.**
6. **Web app (§11)** then a **headline campaign**. `apps/api` (jobs + SSE) + `apps/web` (the
   clickable UI) render this `Report` with the skills/delivery toggle as the live demo; the campaign
   (±Opus, N≥20 over the `model × delivery` grid + `make_figures.py`, deferred for now) tightens the
   CIs for the writeup.

### Future (seamed)

`self_generated` content control; `description_match` / `model_choice` routers; validity
decomposition, error-mode classification, integrity probing; multi-agent sweep; cross-vendor models;
skills-vs-RAG (procedural vs declarative).

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
