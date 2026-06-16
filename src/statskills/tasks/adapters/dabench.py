"""InfiAgent-DABench adapter — normalise the benchmark into our Task (ROADMAP §4).

Reads the downloaded dev set (``da-dev-questions.jsonl`` + ``da-dev-labels.jsonl`` +
``da-dev-tables/*.csv``; fetch with ``make dabench-data``) into closed-form
:class:`~statskills.tasks.schema.Task`s. A question's ``format`` field (the
``@name[value]`` spec) drives the prompt, and the label's ``common_answers`` give the
per-key ground truth. Per-key numeric tolerance is half a unit in the label's last
decimal place (near-zero for integers) — the same rounding policy as the authored tasks.
We never fork DABench's evaluation; these tasks are scored by our own verifier.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from statskills.tasks.schema import AnswerKey, Dataset, ExpectedAnswer, Task

REPO_ROOT = Path(__file__).resolve().parents[4]
DABENCH_DIR = REPO_ROOT / "data" / "benchmarks" / "dabench"


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _answer_key(name: str, value: str) -> AnswerKey:
    """Build a per-key expected answer, inferring numeric vs categorical."""
    try:
        float(value)
    except ValueError:
        return AnswerKey(value, "categorical", name=name)
    decimals = len(value.split(".")[1]) if "." in value else 0
    tolerance = 0.5 * 10 ** (-decimals) if decimals else 1e-9
    return AnswerKey(value, "numeric", tolerance=tolerance, name=name)


def _build_prompt(question: dict[str, Any]) -> str:
    parts = [str(question["question"])]
    if constraints := question.get("constraints"):
        parts.append(f"Constraints:\n{constraints}")
    if fmt := question.get("format"):
        parts.append(f"Format your final answer exactly as:\n{fmt}")
    return "\n\n".join(parts)


def load_dabench_tasks(data_dir: Path = DABENCH_DIR) -> list[Task]:
    """Load the DABench dev set as Tasks (fetch first via make dabench-data)."""
    questions = _read_jsonl(data_dir / "da-dev-questions.jsonl")
    labels = {
        item["id"]: item["common_answers"]
        for item in _read_jsonl(data_dir / "da-dev-labels.jsonl")
    }
    tables = data_dir / "da-dev-tables"

    tasks: list[Task] = []
    for question in questions:
        common = labels.get(question["id"])
        if not common:
            continue  # no ground-truth label
        keys = tuple(_answer_key(name, str(value)) for name, value in common)
        tasks.append(
            Task(
                id=f"dabench-{question['id']}",
                prompt=_build_prompt(question),
                datasets=(Dataset(tables / question["file_name"]),),
                expected=ExpectedAnswer(keys=keys, format_spec=question.get("format")),
                concepts=tuple(question.get("concepts", [])),
                source="dabench",
            )
        )
    return tasks
