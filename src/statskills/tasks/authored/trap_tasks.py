"""Authored TRAP tasks — data engineered so the naive method misleads (ROADMAP §4).

Each task states a goal *without naming a method*; the dataset (built by
``scripts/gen_authored_data.py``) is engineered so the naive default method yields one
answer while the statistically correct method yields the ground truth baked here. A
curated statistics skill (test selection, assumption checks, multiple-comparison
correction) is what should steer a capable agent from the naive answer to the correct
one — the arm where skills should help, unlike the method-constrained DABench arm.
``test_trap_tasks.py`` verifies these (correct method == truth; naive method != it).
"""

from __future__ import annotations

from pathlib import Path

from statskills.tasks.schema import Dataset, ExpectedAnswer, Task

AUTHORED_DATA_DIR = Path(__file__).resolve().parents[4] / "data" / "authored"


def load_trap_tasks(data_dir: Path = AUTHORED_DATA_DIR) -> list[Task]:
    """Build the five authored trap tasks against ``data_dir``."""

    def ds(name: str) -> Dataset:
        return Dataset(data_dir / name)

    return [
        Task(
            id="trap-correlation",
            prompt=(
                "The file trap_correlation.csv has numeric columns 'x' and 'y'. "
                "What is the correlation coefficient between x and y? "
                "Round to 2 decimals."
            ),
            datasets=(ds("trap_correlation.csv"),),
            # Outliers inflate Pearson (~0.86); robust Spearman (~0.18) is correct.
            expected=ExpectedAnswer.single(0.18, "numeric", tolerance=5e-3),
            concepts=("correlation",),
            source="authored_trap",
        ),
        Task(
            id="trap-welch",
            prompt=(
                "The file trap_welch.csv has columns 'group' (A or B) and 'value'. "
                "Is there a statistically significant difference in 'value' between "
                "group A and group B at the 0.05 significance level? Answer Yes or No."
            ),
            datasets=(ds("trap_welch.csv"),),
            # Unequal variance/n: pooled t says Yes (p=.022); Welch says No (p=.155).
            expected=ExpectedAnswer.single("No", "categorical"),
            concepts=("two_sample_test", "equal_variance"),
            source="authored_trap",
        ),
        Task(
            id="trap-paired",
            prompt=(
                "The file trap_paired.csv has columns 'subject', 'before', and "
                "'after' (the same subjects measured twice). Is there a statistically "
                "significant change from 'before' to 'after' at the 0.05 level? "
                "Answer Yes or No."
            ),
            datasets=(ds("trap_paired.csv"),),
            # Repeated measures: independent t says No (p=.41); paired t says Yes.
            expected=ExpectedAnswer.single("Yes", "categorical"),
            concepts=("two_sample_test", "paired"),
            source="authored_trap",
        ),
        Task(
            id="trap-multiple-comparisons",
            prompt=(
                "The file trap_mc.csv has columns 'group' (g1 through g5) and "
                "'value'. Across all 10 pairwise comparisons between the five groups, "
                "how many pairs differ significantly at the 0.05 level? "
                "Report a single integer."
            ),
            datasets=(ds("trap_mc.csv"),),
            # Uncorrected counts 5; after Holm/Bonferroni only 2 survive.
            expected=ExpectedAnswer.single(2, "numeric", tolerance=1e-9),
            concepts=("multiple_comparisons",),
            source="authored_trap",
        ),
        Task(
            id="trap-chi2",
            prompt=(
                "The file trap_chi2.csv has columns 'treatment' (X or Y) and "
                "'outcome' (success or fail). Is there a statistically significant "
                "association between treatment and outcome at the 0.05 level? "
                "Answer Yes or No."
            ),
            datasets=(ds("trap_chi2.csv"),),
            # Small expected counts: chi-square says Yes; Fisher exact says No.
            expected=ExpectedAnswer.single("No", "categorical"),
            concepts=("association", "categorical"),
            source="authored_trap",
        ),
    ]
