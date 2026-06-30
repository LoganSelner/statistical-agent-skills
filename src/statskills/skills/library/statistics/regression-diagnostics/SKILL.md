---
name: regression-diagnostics
description: Check and fix common inferential-regression pitfalls before trusting a coefficient or its significance — omitted-variable/confounding bias (Simpson's paradox), heteroskedasticity (robust SEs), influential points and leverage, non-linearity, and multicollinearity. Use whenever estimating or interpreting the linear effect of a predictor on an outcome.
---

A single OLS fit can give a confident but wrong coefficient — biased, mis-signed, or with
standard errors that over- or under-state significance. Before you report an effect or its
p-value, run these checks and decide from the model that survives them, not the first fit.

- **Confounding / omitted-variable bias.** A bivariate slope (`y ~ x` alone) can be biased
  or even sign-flipped by a variable you left out. Include plausible confounders that are
  present in the data and check whether the coefficient's sign or significance changes
  (Simpson's paradox). Interpret the *adjusted* coefficient.
- **Heteroskedasticity.** If the residual spread changes with the fitted values or a
  predictor (look at residuals-vs-fitted, or run a Breusch–Pagan test), the default OLS
  standard errors are wrong. Re-fit with heteroskedasticity-robust SEs (`cov_type="HC3"`);
  significance can flip.
- **Influential points / leverage.** One high-leverage point can drive the whole slope.
  Check Cook's distance (a common flag is > 4/n); refit without the point and see whether
  the conclusion holds.
- **Non-linearity.** A near-zero, non-significant *linear* slope can hide a strong
  non-linear relationship. Inspect residuals for curvature; add a polynomial term (e.g.
  `x**2`) or transform before concluding "no effect".
- **Multicollinearity.** Highly correlated predictors inflate standard errors and make
  individual coefficients unstable; check the variance inflation factor (VIF).

## Examples

```python
import numpy as np
import statsmodels.api as sm
from statsmodels.stats.diagnostic import het_breuschpagan

X = sm.add_constant(df[["x"]])  # add confounders here, e.g. df[["x", "z"]]
model = sm.OLS(df["y"], X).fit()

# Heteroskedasticity: detect, then use robust SEs (significance may change).
bp_p = het_breuschpagan(model.resid, model.model.exog)[1]
robust = model.get_robustcov_results(cov_type="HC3")
print(model.pvalues, robust.pvalues, "BP p =", bp_p)

# Influential points: flag by Cook's distance, refit without them.
cooks = model.get_influence().cooks_distance[0]
keep = cooks <= 4 / len(df)
refit = sm.OLS(df["y"][keep], X[keep]).fit()

# Non-linearity: test a quadratic term.
Xq = sm.add_constant(np.column_stack([df["x"], df["x"] ** 2]))
quad = sm.OLS(df["y"], Xq).fit()  # is the x**2 coefficient significant?
```
