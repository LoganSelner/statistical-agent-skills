"""Authored inferential-REGRESSION traps — naive OLS misleads (ROADMAP §5).

Each task asks a closed-form question about a regression effect (no method named); the
dataset (built by ``scripts/gen_authored_data.py``) is engineered so a naive default fit
reaches one answer while the correct diagnostic reaches the ground truth baked here. The
``regression-diagnostics`` skill is what should steer a capable agent from the naive
answer to the correct one — the broadened trap arm that breaks the single-task
dependency of the original five traps. ``test_regression_trap_tasks.py`` verifies each
(correct method == truth; naive method != it).
"""

from __future__ import annotations

from pathlib import Path

from statskills.tasks.schema import Dataset, ExpectedAnswer, Task

AUTHORED_DATA_DIR = Path(__file__).resolve().parents[4] / "data" / "authored"


def load_regression_trap_tasks(data_dir: Path = AUTHORED_DATA_DIR) -> list[Task]:
    """Build the four authored regression-trap tasks against ``data_dir``."""

    def ds(name: str) -> Dataset:
        return Dataset(data_dir / name)

    return [
        Task(
            id="reg-confounding",
            prompt=(
                "The file reg_confounding.csv has numeric columns 'x', 'z', and 'y'. "
                "Does 'x' have a positive or negative effect on 'y'? Answer with a "
                "single word: positive or negative."
            ),
            datasets=(ds("reg_confounding.csv"),),
            # y~x alone is positive; adjusting for the confounder z, the x effect flips
            # negative (Simpson's paradox).
            expected=ExpectedAnswer.single("negative", "categorical"),
            concepts=("regression", "confounding"),
            source="authored_trap",
        ),
        Task(
            id="reg-heteroskedasticity",
            prompt=(
                "The file reg_heteroskedasticity.csv has numeric columns 'x' and 'y'. "
                "Is there a statistically significant linear effect of 'x' on 'y' at "
                "the 0.05 significance level? Answer Yes or No."
            ),
            datasets=(ds("reg_heteroskedasticity.csv"),),
            # Default OLS SEs say Yes (p=.031); robust HC3 SEs say No.
            expected=ExpectedAnswer.single("No", "categorical"),
            concepts=("regression", "heteroskedasticity"),
            source="authored_trap",
        ),
        Task(
            id="reg-influence",
            prompt=(
                "The file reg_influence.csv has numeric columns 'x' and 'y'. Is "
                "there a statistically significant linear effect of 'x' on 'y' at "
                "the 0.05 significance level? Answer Yes or No."
            ),
            datasets=(ds("reg_influence.csv"),),
            # The full-data fit is significant; dropping one high-leverage point
            # (Cook's distance > 4/n) it is not.
            expected=ExpectedAnswer.single("No", "categorical"),
            concepts=("regression", "influence"),
            source="authored_trap",
        ),
        Task(
            id="reg-nonlinearity",
            prompt=(
                "The file reg_nonlinearity.csv has numeric columns 'x' and 'y'. Is "
                "there a statistically significant relationship between 'x' and 'y'? "
                "Answer Yes or No."
            ),
            datasets=(ds("reg_nonlinearity.csv"),),
            # A linear slope is ~0 (n.s.), but a quadratic term is highly significant —
            # there is a strong (non-linear) relationship.
            expected=ExpectedAnswer.single("Yes", "categorical"),
            concepts=("regression", "nonlinearity"),
            source="authored_trap",
        ),
    ]
