---
name: parametric-assumption-checks
description: Verify the assumptions of a parametric test (normality, equal variance, independence) and switch to a nonparametric alternative when they fail. Use before reporting a t-test, ANOVA, or Pearson correlation result.
---

A parametric test's p-value is only trustworthy if its assumptions hold. Check them
explicitly and report what you found.

1. Normality (of each group, or of the paired differences):
   - Shapiro-Wilk test (scipy.stats.shapiro); p < 0.05 suggests non-normality.
   - The test is over-sensitive at large n and weak at small n, so also look at the skew
     and a histogram / Q-Q plot before deciding.

2. Equal variance (homogeneity) for t-tests and ANOVA:
   - Levene's test (scipy.stats.levene), which is robust to non-normality.
   - If variances differ, use Welch's t-test (equal_var=False) or Welch's ANOVA instead
     of the pooled-variance version.

3. Independence:
   - A property of the design, not a test: observations must not be repeated, clustered,
     or otherwise linked. If they are, use a paired/repeated-measures method.

4. If normality fails, use the nonparametric equivalent: Mann-Whitney U (two independent),
   Wilcoxon signed-rank (paired), Kruskal-Wallis (>2 groups), or Spearman (association).

Report which assumptions you checked, the test statistics, and the resulting choice.

## Examples

```python
from scipy import stats

# normality per group
stats.shapiro(group_a)
stats.shapiro(group_b)

# equal variance
stats.levene(group_a, group_b)

# assumptions OK -> Welch t-test; normality failed -> Mann-Whitney
stats.ttest_ind(group_a, group_b, equal_var=False)
stats.mannwhitneyu(group_a, group_b, alternative="two-sided")
```
