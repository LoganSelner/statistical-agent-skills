# Findings

The research record. For the system that produced these see [ARCHITECTURE.md](ARCHITECTURE.md);
for framing and the forward plan see [ROADMAP.md](ROADMAP.md). Quantitative claims here are taken
from the run artifacts (`results/matrix-*/matrix.json`), not memory; each is reproducible via the
command in [Reproducibility](#reproducibility).

## TL;DR

- **The headline (first significant positive result):** on **Claude Haiku 4.5**, agent-activated
  ("agentic") skill delivery raises trap-arm pass rate **+12pp [95% CI +4, +20]** over no-skills —
  the CI excludes zero — and beats force-**injecting** the same skills (72% vs 56%). These are the
  project's **first meaningful confidence intervals** (Haiku is stochastic across trials; the local
  models were deterministic).
- **Why:** Haiku engages **selectively** — it reads a skill only for the task whose procedure is
  genuinely non-obvious (multiple-comparison correction) and fast-paths the rest. Agentic delivery
  gets that targeted benefit with no context cost; **injection distracts** on tasks the model
  already solved, cancelling the gain.
- **The instrument broadened — and the delivery effect _flips_ (newest, the bigger result):** four
  authored *regression* traps (Simpson's/omitted-variable, heteroskedasticity, influential points,
  non-linearity) that Haiku fails **0%** unaided (the naive answer 20/20). Skills produce large,
  multi-procedure gains — **injected +95pp [85, 100] > agentic +75pp [55, 95]** — breaking the
  single-task dependency. Injection *wins* here because *every* task needs the skill (no already-solved
  tasks for the payload to distract), while agentic **under-engages** (30% read-rate). And the
  mechanism is now clean: **every agentic skill read led to a pass (6/6)**, the right skill is picked
  every time, and the failures are all non-read trials — the per-trial "right skill → solve" story the
  monogenic arm couldn't support. §0 sharpens: the *sign* of injected−agentic tracks the fraction of
  tasks that need the skill.
- **The flip, explained — selectivity is the lever (the cleanest result, §0 delivered):** a 5-arm
  dose-response separates *what* is injected from *how much*. Injecting **all** skills helps **0pp** on
  the original arm (`all·L1` = off = 60%); injecting **only the task-relevant** skill recovers the full
  **+12pp** (`rel·L1` = 72%) — the five distractor skills cost the *entire* gain (MC alone: 0% under
  all-injection → 100% under relevant-injection). And **`rel·L1` ≈ agentic** (both 72%): agent-
  activation's benefit *is* selectivity, reproducible by oracle-relevant injection. Where every task
  needs the skill (regression), there's nothing to distract, so `rel·L1` = `all·L1` = 100% > agentic
  75% (under-engagement). Bonus (resolution × difficulty): descriptions alone (`all·L0`) carry
  *nameable* fixes (confounding, robust SEs → 100%) but not *procedural* ones (leverage, non-linearity
  → 20%; `all·L0` regression 60% vs `all·L1` 100%).
- **Model choice reframes the delivery story — "agentic" is not reliably selective (model axis,
  on Sonnet 4.6; n=2, model-dependent per SRA, not a demonstrated capability law):** the selectivity
  lever *strengthens* — relevant-only injection beats inject-all by
  **+36pp** on Sonnet (`rel·L1` 100% vs `all·L1` 64%), and **Sonnet + `rel·L1` = 100% on both arms**
  (the right skill ceilings a capable model). But **agent-activation stops being selective**: Sonnet
  *over-reads* (agentic read-rate **84–100%** vs Haiku's 10–36%), re-importing the distraction, so its
  agentic *ties* inject-all and *loses* to relevant-injection. So the lever is **relevance routing**,
  which agent-activation only approximates when engagement is well-calibrated (Haiku under-reads, Sonnet
  over-reads). Capability also shrinks headroom (regression `off` 5%→50% — Sonnet solves the easy traps
  unaided).
- **The hard precondition:** this only appears on a **frontier** model. Local coder models
  (qwen2.5-coder 7B/14B, qwen3-14B) **never read an offered skill** (0/55 agentic trials) — skill
  *invocation* is an emergent capability they sit below.
- **A residual gap:** one trap (`trap-correlation`) is never solved by any model/arm — even Haiku
  fast-paths "what is the correlation?" to Pearson and never consults the skill. This points at
  **task framing**, not the skill.

## The question

Do curated agent skills improve an LLM's performance on inferential-statistics data-analysis tasks?
Operationalised as: does providing *packaged procedural knowledge* raise **task pass rate** vs no
skills, on tasks that do **not** pre-specify the method?

## Method

- **Task arm — `authored_trap` (5 tasks):** each dataset is engineered so the *naive* method
  reaches the wrong conclusion while the *correct* method yields a known closed-form answer
  (correlation: Pearson 0.86 vs Spearman 0.18; welch; paired; multiple-comparison correction
  Holm→2 not 5; Mann-Whitney). Scored pass/fail by deterministic verifier.
- **Conditions:** `off` (no skills) vs `curated`, where curated splits on **delivery** —
  `injected` (skill bodies in the system prompt) vs `agentic` (skills as sandbox files the agent
  reads on demand) — and **disclosure** L1 (instructions) / L2 (+worked code).
- **Aggregation:** N trials per (arm, task); pass-rate with a **percentile bootstrap CI** that
  resamples whole trials (`evaluation/trials.py`).
- **Models:** local qwen2.5-coder 7B/14B and qwen3-14B (Ollama); Claude Haiku 4.5 (Anthropic).

## Results

### Phase 3b — constrained arm (DABench): skills **hurt** (−25pp)
On benchmark tasks whose method is dictated by the prompt, curated skills *lowered* pass rate —
the method decision a skill would inform is already removed, so the skill payload is pure
distraction. This is why the project pivoted to authored **trap** tasks (method-free).

### Phases 4–5 — trap arm on local models (deterministic; degenerate CIs)
*Disclosure grid* (`results/matrix-disclosure-n5`, N=5):

| model | off | L1 | L2 |
|---|---|---|---|
| qwen2.5-coder:7b | 20% | **60% (+40)** | 20% |
| qwen2.5-coder:14b | 60% | 60% (+0) | 60% (+0) |

- 7B/L1 is a real flip but only on **test selection** (welch, mwu) — exactly where frontier models
  are near-ceiling, "achievable" only because the 7B is weak. **L2 distracts** (back to 20%). The
  14B solves welch/paired/mwu unaided and is immovable; `correlation` and `multiple-comparisons`
  never flip on either model.
- Every cell is deterministic at temp 0 → CIs collapse; **N is the wrong axis** for these models.

*Engagement grid* (`results/matrix-engagement-n5`, N=5) added the `agentic` arm — and the decisive
negative: across **all 50 agentic trials (both models × 5 tasks × 5 trials), the agent read an
offered skill 0 times.** Agentic ≤ off on both (7B 40%, 14B 40% — the L0 prompt preamble even
distracts). The engagement gap is **behavioural, not a delivery artifact**.

### Model-axis probe — qwen3-14B also doesn't engage
A newer, more agentic local model (qwen3-14B ≈ qwen2.5-32B capability) **also read 0 skills** in a
single-trial agentic probe (5 task-runs) — climbing the local ladder didn't help. Skill invocation
is a late-emerging capability; local scale sits below the threshold. → the experiment needs a
**frontier** model. (Combined with the grid, that's **0 reads in 55 local agentic trials**: 50 + 5.)

### Phase 5+ — Claude Haiku 4.5 (the headline)
`results/matrix-haiku-n5`, N=5 (after the markdown verifier fix, PR #17):

| arm | pass-rate (95% CI) | Δ vs off |
|---|---|---|
| off | 60% [60, 60] | — |
| L1 (injected) | 56% [44, 68] | −4% [−16, +8] (n.s.) |
| **agentic** | **72% [64, 80]** | **+12% [+4, +20]** |

**Clean per-task decomposition** (pass-frequency over 5 trials):

| task | off | L1 | agentic |
|---|---|---|---|
| trap-correlation | 0% | 0% | 0% |
| trap-multiple-comparisons | 0% | 60% | 60% |
| trap-mwu | 100% | 60% | 100% |
| trap-paired | 100% | 100% | 100% |
| trap-welch | 100% | 60% | 100% |

- **agentic = off + MC(0→60%)**, everything else untouched → 72%.
- **injected = off + MC(0→60%) − mwu(100→60%) − welch(100→60%)** → 56%: the full payload distracts
  on tasks Haiku already solved, offsetting the MC gain.
- **Engagement (agentic cell) — now a measured artifact** (`evaluation/engagement.py`, emitted to
  each run's `engagement.jsonl` and into `matrix.json`, no agent re-run): Haiku read a skill only for
  `trap-multiple-comparisons` (**4/5 trials**, reading the MC-correction + assumption-checks skills)
  and **0** for the other four tasks (read-rate **16%**) — selective, calibrated invocation. The
  cell-level read×pass barely separates (P(pass|read) 75% vs P(pass|¬read) 71%) because no-reads pile
  up on tasks already solved; the **per-task** read-frequency is what isolates the mechanism. At N=5
  the per-trial "right skill → solve" story is still unsupported (MC reads passed 2/3; one solve came
  from reading the *assumption-checks* skill, one MC read still failed).
- **Real stochasticity:** off is deterministic, but L1 [40,40,60,60,80] and agentic [80,60,60,80,80]
  vary trial-to-trial → the first non-degenerate CIs in the project.

### Phase 6 — inferential-regression traps (the instrument broadens; the delivery effect flips)
`results/matrix-20260630T041619Z`, N=5, four authored regression traps on Haiku (`authored_regression`):

| arm | pass-rate (95% CI) | Δ vs off | read-rate |
|---|---|---|---|
| off | 0% [0, 0] | — | 0% |
| L1 (injected) | 95% [85, 100] | **+95% [+85, +100]** | 0% |
| agentic | 75% [55, 95] | **+75% [+55, +95]** | 30% |

Per-task pass-frequency (off / L1 / agentic): `reg-confounding` 0/100/100, `reg-heteroskedasticity`
0/100/100, `reg-influence` 0/100/60, `reg-nonlinearity` 0/80/40 (%).

- **Headroom is total and genuine.** off gives the *naive* answer on every trap, every trial (20/20,
  0 errors) — the frontier fast-path reliably falls for each. This is the headroom the original arm
  lacked (welch/mwu/paired were solved unaided), so **the single-task dependency is broken**: four
  procedures, each 0% → high with skills.
- **The delivery effect flips — injected (95%) > agentic (75%)**, the reverse of the original arm.
  When *every* task needs the skill there are no already-solved tasks for the injected payload to
  distract, so reliable delivery wins; agentic only helps when the model engages, and Haiku
  **under-engages** (30% read-rate). Selectivity is an asset when most tasks don't need the skill and a
  liability when all do.
- **Clean mechanism (what the monogenic arm couldn't show).** In the agentic arm **read → pass is
  6/6 (100%)** vs no-read → pass 9/14 (64%); the agent picks the right skill every time
  (`regression-diagnostics`, 6/6, from a 6-skill library); failures concentrate in non-read trials
  (`reg-nonlinearity`: every read passed, every non-read failed). The per-trial "right skill → solve"
  story now holds.
- **Nuance — the L0 description is itself a nudge.** `reg-confounding` and `reg-heteroskedasticity`
  pass in agentic with 0–2 body reads: the L0 discovery surface (skill *names + descriptions* in the
  prompt) flips behavior without a body read (off, lacking even that, is 0%). So the agentic gain
  blends an L0-description effect with the body-read effect — worth separating in a future probe.
- **Caveat:** N=5 (reads N=6) — the read→pass gap is clean and directional but small-N; the headline
  campaign (higher N) will firm it.

### Phase 7 — injection dose-response (the flip, explained: selectivity is the lever)
`results/matrix-20260630T051151Z` (original) + `…T053552Z` (regression), N=5 — a 5-arm delivery sweep
{off, injected·all·L1, injected·all·L0, injected·relevant·L1, agentic} on Haiku, where `relevant` is a
deterministic oracle router (the task's concepts → its target skill(s)).

| arm | original | regression |
|---|---|---|
| off | 60% [60, 60] | 10% [0, 20] |
| injected · all · L1 | 60% [60, 60] | 100% [100, 100] |
| injected · all · L0 (descriptions only) | 60% [60, 60] | 60% [50, 70] |
| injected · **relevant** · L1 | **72% [64, 80]** | 100% [100, 100] |
| agentic | 72% [64, 80] | 75% [60, 90] |

- **Distraction is real and large — measured causally.** Original arm: injecting *all* 6 skills
  (`all·L1`) helps **0pp** (= off, 60%); injecting *only the relevant* skill (`rel·L1`) recovers the
  full **+12pp [+4, +20]** (72%). The five distractor skills cost the *entire* gain. The per-task
  smoking gun is multiple-comparison correction: **0% under all-injection** (the MC skill is buried
  among distractors) → **100% under relevant-injection**. This is GSM-DC dose-response, applied to
  *skills* as a *delivery* variable — the §0 contribution, now causal.
- **The flip is explained: selectivity is the lever, not "agentic magic."** `rel·L1` ≈ `agentic` (both
  72%) on the original arm — agent-activation's benefit *is* selectivity, reproducible by oracle-
  relevant injection. On regression, `rel·L1` = `all·L1` = 100% > agentic 75%: with no distractors to
  avoid, injection's reliable delivery beats agentic's under-engagement. So **agentic ≈ relevant-
  injection; both beat inject-all when distractors are present, and lose to it only via under-
  engagement when they aren't.**
- **Resolution × procedure difficulty (the Phase-6 L0 nudge, resolved).** Descriptions alone (`all·L0`)
  suffice for *nameable* fixes — regression confounding 100%, heteroskedasticity 100% (the description
  cues "control for confounders" / "use robust SEs") — but not *procedural* ones that need the body:
  influence 20%, non-linearity 20% (Cook's distance, the quadratic term). Hence `all·L0` regression =
  60% vs `all·L1` 100% (−40pp); on the original arm `all·L0` = 60% = off.
- **Honest nuance:** even a *relevant* skill can mislead on an already-solved task — `rel·L1` dropped
  `trap-welch` 100→60% (the test-selection skill flipped two trials to the wrong "Yes") — but the MC
  recovery dominates (+12 net). And off-regression was 10% here (Haiku sometimes controls for the
  confounder unprompted) vs the 0% Phase-6 draw; both show large headroom.

### Phase 8 — model axis (model choice reframes delivery: "agentic" ≠ reliably selective; n=2)
`results/matrix-20260630T064130Z` (original) + `…T075725Z` (regression), N=5 — the 5-arm sweep on
**Sonnet 4.6 alongside Haiku 4.5** in one run.

| arm | orig. Haiku | orig. Sonnet | reg. Haiku | reg. Sonnet |
|---|---|---|---|---|
| off | 60% | 60% | 5% | 50% |
| injected · all · L1 | 60% | 64% | 90% | 95% |
| injected · all · L0 | 56% | 80% | 50% | 100% |
| injected · **relevant** · L1 | 60% | **100%** | 95% | 100% |
| agentic | 72% | 72% | 75% | 85% |
| *agentic read-rate* | *36%* | ***84%*** | *10%* | ***100%*** |

- **Engagement is model-dependent — and it flips between our two models** (n=2; per SRA, loading is
  model-dependent rather than scale-monotonic, so we do not attribute this to capability). Haiku
  *under*-engages, *selectively*
  (read-rate 10–36%, only where a procedure is missing); Sonnet *over*-engages, *non-selectively*
  (84–100%, reading nearly every task's skills). The "selective engagement" that made Haiku's agentic
  win is a Haiku *calibration*, not a property of the delivery channel.
- **The selectivity lever generalizes — and is cleaner on Sonnet.** Relevant-only injection beats
  inject-all by **+36pp** on Sonnet's original arm (`rel·L1` 100% vs `all·L1` 64%): the distractor
  payload costs the stronger model *more*. (Haiku's original-arm dose is noisy this draw — the relevant
  skill recovers MC 0→100% but misleads `trap-welch`, netting ~0; see caveat.)
- **"Agent-activation" is not a reliable proxy for selectivity.** Because Sonnet over-reads, its
  agentic (72%) *ties* inject-all (64%) and *loses* to `rel·L1` (100%) on the original arm — it
  re-imports the distraction by reading broadly. The robust optimum is **oracle-relevant injection**:
  **Sonnet + `rel·L1` = 100% on both arms** — give a capable model exactly the right skill and it
  ceilings.
- **Capability shrinks headroom.** Regression `off` rises 5%→50%: Sonnet solves confounding (100%) and
  non-linearity (100%) unaided, leaving headroom only on the hardest procedural traps
  (heteroskedasticity, influence). The flip (injected ≥ agentic) persists on regression but its deltas
  shrink.
- **Caveat — N=5 stochasticity.** This fresh Haiku draw differs from Phase 7 (original `rel·L1` 60% vs
  72%; regression `off` 5% vs 10%); CIs overlap and the qualitative story holds, but the original-arm
  `rel·L1` "recovery" is draw-dependent (the relevant skill's damage to already-solved `trap-welch`
  varies). The case for the higher-N headline campaign.

## Interpretation

1. **Delivery is decisive, and the lever is *selectivity* (now causal, Phase 7).** A dose-response
   isolates it: injecting *only the relevant* skill matches agent-activation (both 72% on the original
   arm) and beats injecting *all* skills (60%) — the distractor payload, not the delivery channel, is
   what costs the gain. Agent-activation is one way to get selectivity (the model self-selects);
   oracle-relevant injection is another (the experimenter selects). The practical case for progressive
   disclosure, measured as a correctness effect.
2. **Capability is a precondition.** The same agentic mechanism yields *zero* on local models
   because they never invoke skills. Matches SkillsBench's preconditions (the model must engage) and
   the literature that tool/skill invocation is emergent with scale.
3. **Test selection ≠ where skills help.** The local "win" was on test selection, which capable
   models near-saturate; the durable, model-agnostic gain is on **multiple-comparison correction**
   (a genuinely missing procedure) — exactly the methodological-error territory the design targeted.
4. **The correlation gap is task framing.** Even Haiku, well-calibrated, fast-paths "what is the
   correlation coefficient?" to `df.corr()` (Pearson) without consulting a skill — the task cues the
   naive method and the model is (over)confident. A deliberation-forcing framing is the lever, not a
   better skill.
5. **Selectivity cuts both ways (the delivery lever is task-mix-dependent).** Agent-activation's
   selectivity *wins* when the skill is needed on only some tasks (original arm: it avoids injection's
   distraction) but *loses* when it is needed on all (regression arm: the model under-fires and misses
   it, while injection delivers reliably). So the correctness-optimal delivery mechanism depends on the
   fraction of tasks that need the skill — the cleanest evidence yet for delivery-mechanism-as-a-lever
   (§0), and a caution against reading "agentic > injected" as universal.
6. **Disclosure level interacts with procedure difficulty (Phase 7).** A skill's *description* alone
   delivers *nameable* fixes (control for confounders, use robust SEs) but the *body* is needed for
   *procedural* ones (Cook's-distance diagnostics, adding a quadratic term). The L0→L1 step is not
   uniform — it pays off only where the procedure isn't already cued by the name. This refines
   progressive disclosure beyond "less context is better."
7. **The lever is *relevance*; agent-activation is a *model-dependent* approximation of it (Phase
   8; n=2, per SRA not yet a capability trend).** Selectivity wins for both models, but Haiku reaches it by *under*-reading and Sonnet defeats it
   by *over*-reading — only oracle-relevant injection delivers it reliably (Sonnet + relevant = 100% on
   both arms). So the practical recommendation shifts from "let the agent activate skills" to "**route
   the *relevant* skill**"; agent-activation pays off only when the model's engagement is
   well-calibrated. This subsumes #1 and #5: "agentic > injected" was a Haiku calibration, not a law.

## Relation to concurrent work (mid-2026)

The general phenomenon here — injected skills can distract; selectivity helps — was measured
concurrently in several venues: **SWE-Skills-Bench** (skills help only ~+1.2% on average and can
*degrade* via context interference), **SkillsInjector** (packing skills degrades through attention
dispersion), and **SkillReducer** (compressing skills *improves* quality — less-is-more). This links to
the older distraction line (GSM-IC; GSM-DC, EMNLP 2025). So "delivery matters" is corroborated, not
novel.

How this record relates to that cluster (honestly):

- **The delivery decomposition corroborates, it doesn't lead.** Phase 7 (inject-all ≈ off,
  inject-relevant ≈ agentic) is the same cut as Skill-Retrieval-Augmentation's oracle / inject /
  progressive-disclosure arms and Skill-Shadowing's selection-error vs context-overhead split. Our
  value is a *clean, contamination-free, deterministically-verified* confirmation in inferential
  statistics — not first-to-find.
- **The Phase-8 engagement difference is model-dependent — not a "capability reversal."** Haiku
  under-reads and Sonnet over-reads, but at n=2 this is confounded with model identity — exactly what
  SRA warns when it finds loading is *model-dependent, not monotonic with scale*, and what "Agentic
  Skills in the Wild" shows when higher loading rates fail to help. We report it as model-dependent
  engagement calibration, consistent with that work, pending ≥3 models.
- **What is genuinely distinctive is the domain and framing.** Every neighbor lives in software
  engineering, tool/customer-service, or general agentic tasks; this is inferential statistics, with
  contamination-free authored **validity traps** scored by a deterministic verifier — skills as
  *validity correction* (the model is capable but confidently invalid), not capability extension. The
  clearest route to a novel contribution is the **validity decomposition** (does the skill fix the
  *specific* validity error), which the tool-domain neighbors structurally cannot measure.

Neighbouring statistics-agent benchmarks (**StatABench, StatEval, DSAEval, StatQA, QRData**) evaluate
statistical *capability*, not skills, and are candidate external task arms. Positioning is a standing
practice — see ROADMAP §0–§1.

## Threats to validity

- **Coarse instrument:** 4–5 trap tasks per arm → ~20pp granularity; N=5 gives real-but-wide CIs.
- **Two frontier models, one vendor:** the delivery interaction now spans **Haiku + Sonnet** (the
  capability axis is the headline of Phase 8), but Opus and cross-vendor models are untested, and the
  per-cell CIs are still N=5 (the higher-N campaign will tighten them).
- **Pretraining-rich domain:** inferential statistics is well-covered, so headroom is inherently
  limited (the literature's biggest skill gains are in under-represented domains).
- **Determinism vs stochasticity:** local CIs are degenerate (temp-0 determinism); only the frontier
  run produces meaningful intervals, so cross-model CI comparison is uneven.
- **The Phase-8 engagement difference is n=2, confounded with model identity.** SRA finds skill loading
  is model-dependent rather than scale-monotonic, so "capability reverses selectivity" is not supported
  until ≥3 models (Opus + a cross-vendor) show a trend; we frame it as model-dependent engagement.
- **The oracle-relevant arm is a diagnostic, not a method.** Giving exactly the right skill is optimal
  by construction; identifying it without an oracle is the field's open routing problem. This arm
  bounds the ceiling and isolates the mechanism; it does not propose a router.
- **The effect may be a mid-capability window.** Sonnet already solves half the regression traps
  unaided (off 50% vs Haiku 5%); at the true frontier (Opus / GPT-5.5 / Gemini 3.1) the traps may be
  solved without skills and the delivery effect wash out — worth testing before resting on its durability.

## Reproducibility

`results/` is gitignored; regenerate any result with:

```bash
uv run python scripts/gen_authored_data.py                          # the trap datasets
uv run python scripts/run_matrix.py configs/experiments/<grid>.yaml # off/.../arm grid
```

| result | manifest | output |
|---|---|---|
| disclosure (7B/14B × off/L1/L2) | `disclosure_grid.yaml` | `results/matrix-disclosure-n5/` |
| engagement (7B/14B × off/L1/agentic) | `engagement_grid.yaml` | `results/matrix-engagement-n5/` |
| **Haiku traps (off/L1/agentic)** | `haiku_grid.yaml` | `results/matrix-haiku-n5/` |
| **Haiku regression traps (off/L1/agentic)** | `regression_haiku_grid.yaml` | `results/matrix-<ts>/` |
| **Haiku dose-response (5 arms, original)** | `dose_traps_haiku.yaml` | `results/matrix-<ts>/` |
| **Haiku dose-response (5 arms, regression)** | `dose_regression_haiku.yaml` | `results/matrix-<ts>/` |
| **Model axis Haiku+Sonnet (5 arms, original)** | `model_axis_traps.yaml` | `results/matrix-<ts>/` |
| **Model axis Haiku+Sonnet (5 arms, regression)** | `model_axis_regression.yaml` | `results/matrix-<ts>/` |

Haiku needs `ANTHROPIC_API_KEY`; local grids need a reachable Ollama (`OLLAMA_BASE_URL`). All need
the Docker sandbox image (`make sandbox-image`). Each cell's `run.json` carries full provenance.

## What's next

The model axis sharpened the thesis: the lever is **relevance routing**, and "agent-activation" only
approximates it when engagement is calibrated (Haiku under-reads, Sonnet over-reads); oracle-relevant
injection is the robust optimum (Sonnet + relevant = 100% both arms). The research spine is strong
across two frontier models, and the **deliverable track (reporting layer + web app) is already built**.
Remaining, in priority order: (1) the **validity decomposition** — score whether a skill fixes the
*specific* validity error (method / assumptions / interpretation / fabrication), the one axis the
tool-domain neighbors cannot reach and our clearest route to a distinctive contribution; (2) a
**higher-N headline campaign** (N≥20) plus **Opus and a cross-vendor model** (GPT-5.5 / Gemini 3.1 Pro)
— enough model points to tell whether the Haiku/Sonnet engagement difference is a *trend* or a
*model-idiosyncrasy* (SRA cautions the latter), and to check whether the effect **washes out** as
frontier models solve the traps unaided; (3) an **external benchmark arm** (a StatABench / StatEval
slice) and/or more traps past ~9; and (4) the **L0-description vs L1-body probe**. Prioritised in
[ROADMAP.md](ROADMAP.md) §15–§16.
