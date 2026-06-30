"""statskills-api — the web backend for the deliverable demo (ROADMAP §11).

A thin FastAPI layer over the untouched research harness: submit an analysis run
(prompt + dataset + skills/delivery toggle), stream the agent's steps over SSE, and
fetch the composed, traceable :class:`~statskills.reporting.Report`. It is a pure
*consumer* of ``statskills`` — the dependency points inward (``api -> statskills``),
the agent is never modified, and step streaming rides the existing LLM/sandbox
dependency-injection seam (see :mod:`statskills_api.stream`).
"""

from __future__ import annotations

__version__ = "0.1.0"
