"""Run orchestration — execute a config over N trials x tasks (ROADMAP §6, §9).

This is the central run policy: build the LLM, sandbox, and agent from a config, run
the single-agent CodeAct loop once per (trial, task), and write a trajectories JSONL
(appended incrementally so a long run survives interruption with a still-gradeable
partial dir) plus a ``run.json`` with provenance. It lives in the library — not a
script — so the matrix runner can call it directly and it is testable; the thin CLIs
(``scripts/run.py``, ``scripts/run_matrix.py``) are adapters that own path/dotenv
policy and call inward.

:func:`execute_run_config` takes an already-loaded config dict (and optional injected
``llm``/``sandbox`` for tests); :func:`execute_run` loads a config file then calls it.
``out_dir`` is required — callers own where results land.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict
from datetime import UTC, datetime
import json
import logging
from pathlib import Path
from typing import Any

from statskills.agent.llm import LLM, build_llm, resolve_llm_config
from statskills.agent.loop import ReActAgent
from statskills.core.config import load_yaml_with_inheritance
from statskills.core.provenance import RunProvenance
from statskills.sandbox.base import Executor
from statskills.sandbox.docker import DEFAULT_IMAGE, DockerExecutor
from statskills.sandbox.local import LocalExecutor
from statskills.skills import SkillContext, build_skill_context
from statskills.tasks.loader import load_tasks
from statskills.tasks.schema import Task

logger = logging.getLogger(__name__)


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
        if selection is None or skill_ctx is None:
            traj = agent.run(task)
        elif skill_ctx.delivery == "agentic":
            traj = agent.run(
                task,
                skill_discovery=selection.discovery,
                skill_files=selection.files,
            )
        else:
            traj = agent.run(task, skill_payload=selection.payload)
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


def execute_run_config(
    cfg: Mapping[str, Any],
    *,
    out_dir: Path,
    executor: str | None = None,
    provider: str | None = None,
    model: str | None = None,
    max_steps: int | None = None,
    trials: int | None = None,
    llm: LLM | None = None,
    sandbox: Executor | None = None,
) -> Path:
    """Run an already-loaded config over N trials x tasks into ``out_dir``.

    ``llm`` / ``sandbox`` may be injected (tests); otherwise they are built from the
    config. Build problems (missing key / sandbox) raise ValueError / DockerError.
    """
    llm_config = resolve_llm_config(cfg.get("llm"), provider=provider, model=model)
    n_trials = trials if trials is not None else int(cfg.get("trials", 1))
    steps = max_steps if max_steps is not None else int(cfg.get("max_steps", 10))
    executor_kind = executor or str(cfg.get("executor", "docker"))
    image = str(cfg.get("sandbox_image", DEFAULT_IMAGE))
    timeout = float(cfg.get("timeout", 60))

    llm = llm or build_llm(llm_config)
    if sandbox is None:
        sandbox, image_digest = _build_executor(executor_kind, image, timeout)
    else:
        image_digest = None
    agent = ReActAgent(llm, sandbox, max_steps=steps)

    tasks_spec = dict(cfg.get("tasks") or {"set": "authored"})
    tasks = load_tasks(tasks_spec)
    skill_ctx = build_skill_context(cfg.get("skills"))
    skills_mode = "off" if skill_ctx is None else "curated"

    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out_dir.mkdir(parents=True, exist_ok=True)

    skills_block = cfg.get("skills") or {}
    skills_meta: dict[str, Any] = {"mode": skills_mode}
    if skill_ctx is not None:
        skills_meta.update(
            resolution=skill_ctx.level.name,
            delivery=skill_ctx.delivery,
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

    print(f"\nWrote {out_dir}")
    return out_dir


def execute_run(
    config_path: Path,
    *,
    out_dir: Path,
    executor: str | None = None,
    provider: str | None = None,
    model: str | None = None,
    max_steps: int | None = None,
    trials: int | None = None,
) -> Path:
    """Load a config file (resolving ``extends:``) and run it into ``out_dir``."""
    cfg: dict[str, Any] = load_yaml_with_inheritance(config_path)
    return execute_run_config(
        cfg,
        out_dir=out_dir,
        executor=executor,
        provider=provider,
        model=model,
        max_steps=max_steps,
        trials=trials,
    )
