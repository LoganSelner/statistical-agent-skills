"""Authored slice tasks for the Phase 1 vertical slice.

Five small, closed-form data-analysis tasks over two bundled CSVs — enough to exercise
the agent end-to-end (read data, run pandas/scipy, report an answer). Each carries an
:class:`ExpectedAnswer` so the run can be deterministically graded
(:mod:`statskills.evaluation`). The set deliberately includes a two-sample t-test so the
slice touches the inferential-statistics core, not just descriptives.

Numeric tolerances follow the answer's rounding (about half a unit in the last requested
decimal place), so a correctly-rounded value passes while a genuine error fails.
"""

from __future__ import annotations

from pathlib import Path

from statskills.tasks.schema import Dataset, ExpectedAnswer, Task

# Repo-relative data dir: .../src/statskills/tasks/authored/ -> repo root / data.
AUTHORED_DATA_DIR = Path(__file__).resolve().parents[4] / "data" / "authored"


def load_slice_tasks(data_dir: Path = AUTHORED_DATA_DIR) -> list[Task]:
    """Build the five authored slice tasks against ``data_dir``."""
    sales = Dataset(data_dir / "sales.csv")
    groups = Dataset(data_dir / "groups.csv")
    return [
        Task(
            id="slice-mean",
            prompt=(
                "What is the mean of the 'units' column in sales.csv? "
                "Round to 2 decimals."
            ),
            datasets=(sales,),
            expected=ExpectedAnswer(16.00, "numeric", tolerance=5e-3),
            concepts=("descriptive",),
        ),
        Task(
            id="slice-count",
            prompt="How many rows in sales.csv have region equal to 'North'?",
            datasets=(sales,),
            expected=ExpectedAnswer(3, "numeric", tolerance=0.5),
            concepts=("filtering",),
        ),
        Task(
            id="slice-correlation",
            prompt=(
                "What is the Pearson correlation coefficient between 'units' and "
                "'revenue' in sales.csv? Round to 3 decimals."
            ),
            datasets=(sales,),
            expected=ExpectedAnswer(0.999, "numeric", tolerance=5e-4),
            concepts=("correlation",),
        ),
        Task(
            id="slice-groupby",
            prompt="Which region has the highest total revenue in sales.csv?",
            datasets=(sales,),
            expected=ExpectedAnswer("South", "categorical"),
            concepts=("aggregation",),
        ),
        Task(
            id="slice-ttest",
            prompt=(
                "Perform a two-sample t-test comparing 'score' between group A and "
                "group B in groups.csv. Report the p-value rounded to 4 decimals."
            ),
            datasets=(groups,),
            expected=ExpectedAnswer(0.0039, "numeric", tolerance=5e-5),
            concepts=("two_sample_test",),
        ),
    ]
