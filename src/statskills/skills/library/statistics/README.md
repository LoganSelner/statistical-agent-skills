# Statistics skill library

Curated inferential-statistics skills for the `curated` condition. Each skill is an
[Anthropic Agent-Skills](https://agentskills.io) folder so it stays portable and
comparable to the ecosystem; our loader adds progressive-disclosure control (L0–L3) on
top of the standard.

This directory is intentionally **empty of skills for now** — the parser/loader/router
engine ships first (Phase 3a). The starter skills (test selection, parametric assumption
checks, multiple-comparison correction, effect size + CI, anti-fabrication) are authored
in Phase 3b (ROADMAP §5, §12).

## SKILL.md layout

```
<skill-name>/
  SKILL.md            # required: YAML frontmatter + markdown body
  scripts/            # optional: executable helpers (L3)
  references/         # optional: reference docs (L3)
```

```markdown
---
name: hypothesis-test-selection          # ≤64 chars, [a-z0-9-]
description: Choose the correct hypothesis test for a comparison and when to use it.
---

Body = the procedural instructions (the L1 payload).

## Examples
Fenced code blocks in this section are the L2 payload; put `## Examples` last.

```python
from scipy import stats
stats.mannwhitneyu(a, b)   # non-normal two-group
```
```

Disclosure levels (cumulative): **L0** name + description · **L1** + body · **L2** +
Examples · **L3** + bundled `scripts/` / `references/` contents.
