#!/usr/bin/env python3
"""Run the Phase 1 vertical slice end-to-end.

Loads the authored slice tasks, runs the single-agent CodeAct loop over the
sandbox (Docker by default), and writes one trajectory JSONL plus a run.json with
provenance. Model access is EdenAI (set EDENAI_API_KEY) or a local Ollama server.

Usage:
    python scripts/run_slice.py                      # Docker executor (default)
    python scripts/run_slice.py --executor local     # trusted-code local executor
    python scripts/run_slice.py --model openai/gpt-4o --max-steps 8
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
from statskills.skills import build_skill_context
from statskills.tasks.loader import load_tasks

logger = logging.getLogger("statskills.slice")

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = REPO_ROOT / "configs" / "slice.yaml"
RESULTS_DIR = REPO_ROOT / "results"


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run the Phase 1 vertical slice.")
    p.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    p.add_argument(
        "--executor",
        choices=["docker", "local"],
        default=None,
        help="Override the configured executor. 'local' is UNSANDBOXED (trusted only).",
    )
    p.add_argument(
        "--provider",
        choices=["edenai", "ollama"],
        default=None,
        help="Override the configured LLM provider.",
    )
    p.add_argument("--model", default=None, help="Override the provider/model id.")
    p.add_argument("--max-steps", type=int, default=None)
    p.add_argument("-v", "--verbose", action="store_true")
    return p.parse_args()


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


def main() -> int:
    args = _parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )
    load_dotenv(REPO_ROOT / ".env")

    cfg: dict[str, Any] = load_yaml_with_inheritance(args.config)
    llm_config = resolve_llm_config(
        cfg.get("llm"), provider=args.provider, model=args.model
    )
    max_steps = args.max_steps or int(cfg.get("max_steps", 10))
    executor_kind = args.executor or str(cfg.get("executor", "docker"))
    image = str(cfg.get("sandbox_image", "statskills-sandbox:0.1.0"))
    timeout = float(cfg.get("timeout", 60))

    try:
        llm = build_llm(llm_config)
    except ValueError as e:
        logger.error("%s", e)
        return 1
    try:
        executor, image_digest = _build_executor(executor_kind, image, timeout)
    except DockerError as e:
        logger.error("Sandbox unavailable: %s", e)
        return 1

    agent = ReActAgent(llm, executor, max_steps=max_steps)
    tasks_spec = dict(cfg.get("tasks") or {"set": "authored"})
    tasks = load_tasks(tasks_spec)
    skill_ctx = build_skill_context(cfg.get("skills"))
    skills_mode = "off" if skill_ctx is None else "curated"

    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out_dir = RESULTS_DIR / f"run-{run_id}"
    out_dir.mkdir(parents=True, exist_ok=True)
    provenance = RunProvenance.capture()

    print(
        f"\nRunning {len(tasks)} {tasks_spec.get('set', 'authored')} task(s) · "
        f"provider={llm_config.provider} · model={llm.model} · "
        f"executor={executor_kind} · skills={skills_mode}\n"
    )
    records: list[dict[str, Any]] = []
    for task in tasks:
        selection = skill_ctx.resolve(task) if skill_ctx else None
        try:
            traj = agent.run(
                task, skill_payload=selection.payload if selection else None
            )
        except Exception as e:
            logger.exception("Task %s failed", task.id)
            records.append({"task_id": task.id, "error": str(e)})
            print(f"  {task.id:18} ERROR: {e}")
            continue
        record = traj.to_dict()
        if selection is not None:
            record["skills"] = list(selection.names)
        records.append(record)
        print(
            f"  {task.id:18} answer={traj.final_answer!r}  "
            f"[{traj.stop_reason}, {len(traj.steps)} steps]"
        )

    (out_dir / "trajectories.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in records)
    )
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
        "provenance": asdict(provenance),
        "task_set": tasks_spec,
        "skills": skills_meta,
        "config": {
            "provider": llm_config.provider,
            "model": llm.model,
            "base_url": getattr(llm, "base_url", None),
            "temperature": llm_config.temperature,
            "max_tokens": llm_config.max_tokens,
            "max_steps": max_steps,
            "executor": executor_kind,
            "sandbox_image": image if executor_kind == "docker" else None,
            "sandbox_image_digest": image_digest,
        },
        "tasks": [t.id for t in tasks],
    }
    (out_dir / "run.json").write_text(json.dumps(meta, indent=2))
    print(f"\nWrote {out_dir}\nGrade it: uv run python scripts/grade.py {out_dir}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
