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
negative: across **all 55 agentic trials (both models × 5 tasks × 5 trials), the agent read an
offered skill 0 times.** Agentic ≤ off on both (7B 40%, 14B 40% — the L0 prompt preamble even
distracts). The engagement gap is **behavioural, not a delivery artifact**.

### Model-axis probe — qwen3-14B also doesn't engage
A newer, more agentic local model (qwen3-14B ≈ qwen2.5-32B capability) **also read 0 skills** —
climbing the local ladder didn't help. Skill invocation is a late-emerging capability; local scale
sits below the threshold. → the experiment needs a **frontier** model.

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
- **Engagement (agentic cell):** Haiku read a skill only for `trap-multiple-comparisons` (**4/5
  trials**, reading the MC-correction + assumption-checks skills) and **0** skills for the other
  four tasks. Selective, calibrated invocation.
- **Real stochasticity:** off is deterministic, but L1 [40,40,60,60,80] and agentic [80,60,60,80,80]
  vary trial-to-trial → the first non-degenerate CIs in the project.

## Interpretation

1. **Delivery is decisive.** Agent-activated delivery wins because it is *selective* — the model
   pulls only the procedure it needs, with none of injection's context-pollution cost on tasks it
   already handles. This is the practical case for progressive disclosure, measured.
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

## Threats to validity

- **Coarse instrument:** 5 trap tasks → 20pp granularity; N=5 gives real-but-wide CIs.
- **One frontier model:** the agentic>injected result is shown on Haiku only; the
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
| **Haiku (off/L1/agentic)** | `haiku_grid.yaml` | `results/matrix-haiku-n5/` |

Haiku needs `ANTHROPIC_API_KEY`; local grids need a reachable Ollama (`OLLAMA_BASE_URL`). All need
the Docker sandbox image (`make sandbox-image`). Each cell's `run.json` carries full provenance.

## What's next

The model axis (add Sonnet ± Opus), task design (`authored_open` / a deliberation-forcing
correlation framing for the residual gap), and more N to tighten the +12% CI — prioritised in
[ROADMAP.md](ROADMAP.md) §12.
