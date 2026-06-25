#!/usr/bin/env python3
"""Run a config end-to-end (N trials x tasks) and write trajectories + provenance.

Thin CLI over :func:`statskills.experiments.runner.execute_run`: it owns the dotenv load
and the ``results/run-<ts>`` output location, then calls inward. Model access is EdenAI
(set EDENAI_API_KEY), a local Ollama server, or Anthropic (set ANTHROPIC_API_KEY).

Usage:
    python scripts/run.py                                          # default config
    python scripts/run.py --config configs/experiments/trap_haiku.yaml --trials 5
    python scripts/run.py --executor local --provider ollama --model qwen2.5-coder:7b
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import logging
from pathlib import Path
import sys

from _paths import DEFAULT_CONFIG, REPO_ROOT, RESULTS_DIR
from dotenv import load_dotenv

from statskills.experiments.runner import execute_run
from statskills.sandbox.docker import DockerError

logger = logging.getLogger("statskills.run")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a config over N trials x tasks.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument(
        "--executor",
        choices=["docker", "local"],
        default=None,
        help="Override the configured executor. 'local' is UNSANDBOXED (trusted only).",
    )
    parser.add_argument(
        "--provider", choices=["edenai", "ollama", "anthropic"], default=None
    )
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

    out_dir = RESULTS_DIR / datetime.now(UTC).strftime("run-%Y%m%dT%H%M%SZ")
    try:
        run_dir = execute_run(
            args.config,
            out_dir=out_dir,
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
    print(f"\nGrade it: uv run python scripts/grade.py {run_dir}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
