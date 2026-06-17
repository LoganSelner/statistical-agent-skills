---
name: effect-sizes-and-intervals
description: Report an effect size and a confidence interval alongside every significance test, not just a p-value. Use whenever you report a group difference, an association, or any estimate from data.
---

A p-value says whether an effect is detectable, not how big it is. Report a magnitude and
its uncertainty too.

- Difference in means -> Cohen's d: (mean1 - mean2) / pooled_sd, where pooled_sd combines
  both groups' standard deviations. Rough guide: 0.2 small, 0.5 medium, 0.8 large.
- Correlation -> r (or Spearman's rho) is itself the effect size; report it with its CI.
- Categorical association -> odds ratio, risk ratio, or Cramer's V.

Always give a confidence interval (95% by default) for the estimate. For a difference in
means, prefer scipy's Welch interval — it uses the correct (Satterthwaite) degrees of
freedom — over a hand-rolled estimate +/- t_crit * SE; a bootstrap also works. If the
interval excludes the null value (0 for a difference, 1 for a ratio), that is consistent
with a significant test.

Report the estimate, its CI, and the effect size — then interpret the size, not only the
significance.

## Examples

```python
import numpy as np
from scipy import stats

# Cohen's d for two groups
n1, n2 = len(a), len(b)
pooled_sd = np.sqrt(
    ((n1 - 1) * np.var(a, ddof=1) + (n2 - 1) * np.var(b, ddof=1)) / (n1 + n2 - 2)
)
d = (np.mean(a) - np.mean(b)) / pooled_sd

# 95% CI for the difference in means, mean(a) - mean(b)
# (Welch; scipy uses the correct Satterthwaite degrees of freedom)
ci = stats.ttest_ind(a, b, equal_var=False).confidence_interval(confidence_level=0.95)
lo, hi = ci.low, ci.high
```
