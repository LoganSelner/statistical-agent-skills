"""The run service — drive one analysis to a traceable report (ROADMAP §10, §11).

Given a prompt, an uploaded dataset, and a delivery toggle (``off`` / ``injected`` /
``agentic``), this builds an ad-hoc :class:`~statskills.tasks.schema.Task`, runs the
untouched agent through the shared ``run_with_skills`` dispatch (with the LLM + sandbox
wrapped in a :class:`~statskills_api.stream.RunTap` so steps stream live), then composes
the trajectory into a verified :class:`~statskills.reporting.Report` and attaches
report-time diagnostic figures. It is a pure consumer of the harness: the agent is never
modified, and like grading it never re-runs the agent to report (figures visualise the
same fit, they don't recompute it).

The blocking run executes on a worker thread (see :mod:`statskills_api.app`). ``llm``
and ``executor`` are injected in tests (a fake LLM + in-memory executor); in production
they default to the Claude provider and the Docker sandbox.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from statskills.agent.llm import LLM, build_llm, resolve_llm_config
from statskills.agent.loop import ReActAgent
from statskills.experiments.runner import run_with_skills
from statskills.reporting import (
    FiguresUnavailable,
    Report,
    compose_report,
    generate_figures,
)
from statskills.sandbox.base import Executor
from statskills.sandbox.docker import DEFAULT_IMAGE, DockerExecutor
from statskills.skills import build_skill_context
from statskills.tasks.schema import Dataset, Task
from statskills_api.stream import RunTap, StepEvent, TappingExecutor, TappingLLM

_DELIVERIES = ("off", "injected", "agentic")


def skills_config(delivery: str) -> dict[str, str] | None:
    """The skills block for a delivery toggle (``off`` → ``None``, the no-skills arm).

    ``injected``/``agentic`` use the full ``statistics`` library (router ``forced``) at
    ``L1`` — the off/injected/agentic arms the headline finding compares.
    """
    if delivery == "off":
        return None
    if delivery not in _DELIVERIES:
        known = ", ".join(_DELIVERIES)
        raise ValueError(f"Unknown delivery {delivery!r}. Known: {known}")
    return {
        "mode": "curated",
        "delivery": delivery,
        "router": "forced",
        "resolution": "L1",
    }


def run_analysis(
    *,
    prompt: str,
    dataset_path: Path,
    delivery: str,
    out_dir: Path,
    tap: RunTap,
    llm: LLM | None = None,
    executor: Executor | None = None,
    provider: str = "anthropic",
    model: str | None = None,
    max_steps: int = 10,
    sandbox_timeout: float = 60.0,
) -> Report:
    """Run ``prompt`` over ``dataset_path`` → its verified, figure-bearing report.

    Emits step events on ``tap`` throughout (the agent's turns via the wrappers, plus a
    ``composing`` status before narration). Figures are best-effort: absent the optional
    ``reporting`` stack, or for a non-regression dataset, the report carries none.
    """
    task = Task(
        id=out_dir.name or "web-run",
        prompt=prompt,
        datasets=(Dataset(dataset_path),),
    )
    skill_ctx = build_skill_context(skills_config(delivery))

    base_llm = llm or build_llm(
        resolve_llm_config(None, provider=provider, model=model)
    )
    base_executor = executor or DockerExecutor(
        image=DEFAULT_IMAGE, timeout=sandbox_timeout
    )
    agent = ReActAgent(
        TappingLLM(base_llm, tap),
        TappingExecutor(base_executor, tap),
        max_steps=max_steps,
    )

    trajectory = run_with_skills(agent, task, skill_ctx).to_dict()

    # The narrative is a separate LLM pass over the finished transcript; run it on the
    # untapped LLM so its call does not appear as another agent step in the stream.
    tap.emit(StepEvent(kind="status", text="composing report"))
    report = compose_report(trajectory, task, base_llm)

    try:
        figures = generate_figures(trajectory, task, out_dir)
    except FiguresUnavailable:
        figures = ()
    return replace(report, figures=figures)
