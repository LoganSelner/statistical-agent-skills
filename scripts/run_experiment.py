#!/usr/bin/env python3
"""Run a paired N-trials experiment (skills off vs curated) and report the delta.

Runs both configs over N trials, grades each, and prints the trials comparison:
per-task pass-frequency plus a bootstrapped pass-rate delta CI. One command for the
overnight curated-vs-off run; reuses ``execute_run`` and the grade/compare CLIs.

Usage:
    python scripts/run_experiment.py \\
        --off configs/trap_ollama.yaml \\
        --skills configs/trap_ollama_skills.yaml \\
        --trials 10
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
import subprocess
import sys

from dotenv import load_dotenv
from run_slice import REPO_ROOT, execute_run

from statskills.sandbox.docker import DockerError

SCRIPTS = Path(__file__).resolve().parent
logger = logging.getLogger("statskills.experiment")


def main() -> int:
    parser = argparse.ArgumentParser(description="Paired off-vs-curated N-trials run.")
    parser.add_argument("--off", type=Path, required=True, help="skills-off config")
    parser.add_argument(
        "--skills", type=Path, required=True, help="skills-curated config"
    )
    parser.add_argument("--trials", type=int, default=None, help="repeats per task")
    parser.add_argument("--executor", choices=["docker", "local"], default=None)
    parser.add_argument("--provider", choices=["edenai", "ollama"], default=None)
    parser.add_argument("--model", default=None)
    parser.add_argument("--max-steps", type=int, default=None)
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )
    load_dotenv(REPO_ROOT / ".env")

    def run(config: Path) -> Path:
        return execute_run(
            config,
            executor=args.executor,
            provider=args.provider,
            model=args.model,
            max_steps=args.max_steps,
            trials=args.trials,
        )

    try:
        print("\n########## OFF ##########")
        off_dir = run(args.off)
        print("\n########## CURATED ##########")
        skills_dir = run(args.skills)
    except (ValueError, DockerError) as exc:
        logger.error("%s", exc)
        return 1

    for run_dir in (off_dir, skills_dir):
        subprocess.run(
            [sys.executable, str(SCRIPTS / "grade.py"), str(run_dir)], check=True
        )
    print("\n########## COMPARE ##########")
    subprocess.run(
        [sys.executable, str(SCRIPTS / "compare.py"), str(off_dir), str(skills_dir)],
        check=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
