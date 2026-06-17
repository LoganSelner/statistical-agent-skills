---
name: hypothesis-test-selection
description: Choose the correct hypothesis test for comparing groups or measuring an association, from the outcome type, number of groups, and pairing. Use whenever a task asks whether groups differ, whether an association is significant, or which statistical test to apply.
---

Pick the test from the data's structure — do not default to a t-test.

1. Identify three things:
   - Outcome type: continuous, ordinal, or categorical.
   - Number of groups compared: one, two, or more than two.
   - Design: independent groups, or paired/repeated measures on the same units.

2. Continuous outcome:
   - Two independent groups -> independent-samples t-test (Welch's by default); if
     normality fails, Mann-Whitney U.
   - Two paired measurements -> paired t-test; if the differences are non-normal,
     Wilcoxon signed-rank.
   - More than two independent groups -> one-way ANOVA; if normality/variance fail,
     Kruskal-Wallis.
   - More than two repeated measures -> repeated-measures ANOVA, else Friedman.

3. Association between two categorical variables:
   - Chi-square test of independence; use Fisher's exact test if any expected cell
     count is below 5.

4. Association between two continuous variables:
   - Pearson correlation if the relationship is linear and roughly normal; otherwise
     Spearman rank correlation.

State H0 and H1, use a two-sided test unless a direction is explicitly justified, and
confirm the test's assumptions before trusting its p-value.

## Examples

```python
from scipy import stats

# two independent groups, continuous outcome (Welch by default)
stats.ttest_ind(group_a, group_b, equal_var=False)

# more than two groups
stats.f_oneway(g1, g2, g3)      # parametric
stats.kruskal(g1, g2, g3)       # nonparametric fallback

# categorical association
stats.chi2_contingency(table)

# continuous association
stats.pearsonr(x, y)
stats.spearmanr(x, y)
```
