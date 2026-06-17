---
name: compute-dont-fabricate
description: Never report a statistic you did not compute and print from the data in code. Use on every analysis task to avoid guessed, recalled, or hand-rounded numbers.
---

Every number you report must come from code you ran on the actual data.

1. Inspect first: print the shape, column names, dtypes, and missing-value counts before
   computing anything, so you use the right columns and handle NaNs deliberately.
2. Compute in code and print() the exact value you intend to report — never estimate it,
   recall it from memory, or round it in your head.
3. Read the printed value back and report that, matching any requested rounding or format
   exactly (e.g. two decimals).
4. If a value cannot be computed (missing column, empty filter), say so explicitly rather
   than inventing a plausible number.
5. After fixing a code error, re-run and report the final printed value, not an earlier
   guess.

A confident-sounding number your code did not print is a fabrication; prefer an honest
"cannot compute" over a guess.

## Examples

```python
import pandas as pd

df = pd.read_csv("data.csv")
print(df.shape)
print(df.columns.tolist())
print(df.isna().sum())

# compute, print, then report exactly what printed
mean_fare = df["fare"].mean()
print(round(mean_fare, 2))
```
