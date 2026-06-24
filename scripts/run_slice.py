#!/usr/bin/env python3
"""Run a config end-to-end (N trials x tasks) and write trajectories + provenance.

Loads the configured task set, runs the single-agent CodeAct loop over the sandbox
(Docker by default) once per (trial, task), and writes a trajectories JSONL — appended
incrementally so a long multi-trial run survives an interruption with a still-gradeable
partial dir — plus a run.json with provenance. Model access is EdenAI (set
EDENAI_API_KEY) or a local Ollama server. ``execute_run`` is reused by
``scripts/run_experiment.py``.

Usage:
    python scripts/run_slice.py                                  # default config
    python scripts/run_slice.py --config configs/trap_ollama.yaml --trials 10
    python scripts/run_slice.py --executor local --model openai/gpt-4o
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import UTC, datetime
import json
import logging
from pathlib import Path
import sys
from typing import Any

from dotenv import load_dotenv

from statskills.agent.llm import build_llm, resolve_llm_config
from statskills.agent.loop import ReActAgent
from statskills.core.config import load_yaml_with_inheritance
from statskills.core.provenance import RunProvenance
from statskills.sandbox.base import Executor
from statskills.sandbox.docker import DockerError, DockerExecutor
from statskills.sandbox.local import LocalExecutor
from statskills.skills import SkillContext, build_skill_context
from statskills.tasks.loader import load_tasks
from statskills.tasks.schema import Task

logger = logging.getLogger("statskills.run")

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = REPO_ROOT / "configs" / "slice.yaml"
RESULTS_DIR = REPO_ROOT / "results"


def _build_executor(
    kind: str, image: str, timeout: float
) -> tuple[Executor, str | None]:
    if kind == "local":
        logger.warning(
            "LOCAL executor selected: model-generated code runs UNSANDBOXED "
            "(trusted use only)."
        )
        return LocalExecutor(timeout=timeout), None
    executor = DockerExecutor(image=image, timeout=timeout)
    return executor, executor.image_digest


def _run_one(
    agent: ReActAgent, task: Task, skill_ctx: SkillContext | None, trial: int
) -> dict[str, Any]:
    """Run one (trial, task); return its trajectory record tagged with the trial."""
    selection = skill_ctx.resolve(task) if skill_ctx else None
    try:
        traj = agent.run(task, skill_payload=selection.payload if selection else None)
    except Exception as exc:
        logger.exception("Task %s (trial %d) failed", task.id, trial)
        return {"task_id": task.id, "trial": trial, "error": str(exc)}
    record = traj.to_dict()
    record["trial"] = trial
    if selection is not None:
        record["skills"] = list(selection.names)
    return record


def _print_record(task: Task, record: dict[str, Any]) -> None:
    if "error" in record:
        print(f"  {task.id:24} ERROR: {record['error']}")
        return
    steps = len(record.get("steps", []))
    print(
        f"  {task.id:24} answer={record.get('final_answer')!r}  "
        f"[{record.get('stop_reason')}, {steps} steps]"
    )


def execute_run(
    config_path: Path,
    *,
    executor: str | None = None,
    provider: str | None = None,
    model: str | None = None,
    max_steps: int | None = None,
    trials: int | None = None,
    out_dir: Path | None = None,
) -> Path:
    """Run a config over N trials x tasks; return the results directory.

    ``out_dir`` overrides the default ``results/run-<ts>`` location (the matrix runner
    uses it to place each cell in a stable per-cell directory). Build problems (missing
    key / sandbox) raise ValueError / DockerError.
    """
    cfg: dict[str, Any] = load_yaml_with_inheritance(config_path)
    llm_config = resolve_llm_config(cfg.get("llm"), provider=provider, model=model)
    n_trials = trials if trials is not None else int(cfg.get("trials", 1))
    steps = max_steps if max_steps is not None else int(cfg.get("max_steps", 10))
    executor_kind = executor or str(cfg.get("executor", "docker"))
    image = str(cfg.get("sandbox_image", "statskills-sandbox:0.1.0"))
    timeout = float(cfg.get("timeout", 60))

    llm = build_llm(llm_config)
    sandbox, image_digest = _build_executor(executor_kind, image, timeout)
    agent = ReActAgent(llm, sandbox, max_steps=steps)

    tasks_spec = dict(cfg.get("tasks") or {"set": "authored"})
    tasks = load_tasks(tasks_spec)
    skill_ctx = build_skill_context(cfg.get("skills"))
    skills_mode = "off" if skill_ctx is None else "curated"

    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out_dir = out_dir if out_dir is not None else RESULTS_DIR / f"run-{run_id}"
    out_dir.mkdir(parents=True, exist_ok=True)

    skills_block = cfg.get("skills") or {}
    skills_meta: dict[str, Any] = {"mode": skills_mode}
    if skill_ctx is not None:
        skills_meta.update(
            resolution=skill_ctx.level.name,
            router=str(skills_block.get("router", "forced")),
            library=str(skills_block.get("library", "statistics")),
            skills=list(skill_ctx.library.names),
        )
    meta = {
        "run_id": run_id,
        "provenance": asdict(RunProvenance.capture()),
        "task_set": tasks_spec,
        "trials": n_trials,
        "skills": skills_meta,
        "config": {
            "provider": llm_config.provider,
            "model": llm.model,
            "base_url": getattr(llm, "base_url", None),
            "temperature": llm_config.temperature,
            "max_tokens": llm_config.max_tokens,
            "request_timeout": llm_config.request_timeout,
            "max_steps": steps,
            "executor": executor_kind,
            "sandbox_image": image if executor_kind == "docker" else None,
            "sandbox_image_digest": image_digest,
        },
        "tasks": [t.id for t in tasks],
    }
    # Write provenance up front so an interrupted run is still gradeable.
    (out_dir / "run.json").write_text(json.dumps(meta, indent=2))

    print(
        f"\nRunning {len(tasks)} {tasks_spec.get('set', 'authored')} task(s) x "
        f"{n_trials} trial(s) · provider={llm_config.provider} · model={llm.model} · "
        f"executor={executor_kind} · skills={skills_mode}\n"
    )
    with (out_dir / "trajectories.jsonl").open("w") as handle:
        for trial in range(n_trials):
            if n_trials > 1:
                print(f"-- trial {trial + 1}/{n_trials} --")
            for task in tasks:
                record = _run_one(agent, task, skill_ctx, trial)
                handle.write(json.dumps(record) + "\n")
                handle.flush()
                _print_record(task, record)

    print(f"\nWrote {out_dir}\nGrade it: uv run python scripts/grade.py {out_dir}\n")
    return out_dir


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a config over N trials x tasks.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument(
        "--executor",
        choices=["docker", "local"],
        default=None,
        help="Override the configured executor. 'local' is UNSANDBOXED (trusted only).",
    )
    parser.add_argument("--provider", choices=["edenai", "ollama"], default=None)
    parser.add_argument("--model", default=None, help="Override the provider/model id.")
    parser.add_argument("--max-steps", type=int, default=None)
    parser.add_argument(
        "--trials",
        type=int,
        default=None,
        help="Repeats per task (default: config or 1).",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )
    load_dotenv(REPO_ROOT / ".env")
    try:
        execute_run(
            args.config,
            executor=args.executor,
            provider=args.provider,
            model=args.model,
            max_steps=args.max_steps,
            trials=args.trials,
        )
    except ValueError as exc:
        logger.error("%s", exc)
        return 1
    except DockerError as exc:
        logger.error("Sandbox unavailable: %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
