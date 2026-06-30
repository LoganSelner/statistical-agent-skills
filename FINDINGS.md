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

## Threats to validity

- **Coarse instrument:** 4–5 trap tasks per arm → ~20pp granularity; N=5 gives real-but-wide CIs.
- **One frontier model:** the delivery interaction is shown on Haiku only — and is **task-mix
  dependent** (agentic>injected on the original arm, injected>agentic on regression); the
  capability×delivery interaction (Sonnet/Opus) is untested.
- **Pretraining-rich domain:** inferential statistics is well-covered, so headroom is inherently
  limited (the literature's biggest skill gains are in under-represented domains).
- **Determinism vs stochasticity:** local CIs are degenerate (temp-0 determinism); only the frontier
  run produces meaningful intervals, so cross-model CI comparison is uneven.

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

Haiku needs `ANTHROPIC_API_KEY`; local grids need a reachable Ollama (`OLLAMA_BASE_URL`). All need
the Docker sandbox image (`make sandbox-image`). Each cell's `run.json` carries full provenance.

## What's next

The dose-response closed the §0 loop: skill delivery is a correctness lever *via selectivity*, and the
distractor payload — not the channel — is what costs the gain. The mechanism is now understood on
Haiku across both task arms. Next: the **model axis** (Sonnet ± Opus) to test how the
capability×delivery×task-mix surface generalises; higher **N** to tighten the dose-response CIs; and
then the **reporting layer / deliverable track**. Prioritised in [ROADMAP.md](ROADMAP.md) §15.
