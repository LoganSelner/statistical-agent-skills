---
name: multiple-comparison-correction
description: Adjust p-values when you run several hypothesis tests so the chance of a false positive stays controlled. Use when making multiple pairwise comparisons or testing many correlations or hypotheses at once.
---

Running m tests at alpha = 0.05 makes a false positive likely once m is large (the
family-wise error rate inflates). Correct for it and decide significance on the adjusted
p-values, not the raw ones.

Choose a method by goal:
- Bonferroni — strict control of the family-wise error rate; compare each p to alpha/m
  (equivalently multiply each p by m, capped at 1). Simple but conservative.
- Holm-Bonferroni — also controls the family-wise error rate but is uniformly more
  powerful than Bonferroni; prefer it over plain Bonferroni.
- Benjamini-Hochberg (FDR) — controls the false discovery rate; more powerful for many
  tests or exploratory screening where some false positives are tolerable.

Use statsmodels.stats.multitest.multipletests for all three, and report which correction
you used.

## Examples

```python
from statsmodels.stats.multitest import multipletests

pvals = [0.01, 0.04, 0.03, 0.20]
reject, p_adj, _, _ = multipletests(pvals, alpha=0.05, method="holm")
# method="bonferroni" for Bonferroni FWER, "fdr_bh" for Benjamini-Hochberg FDR
```
