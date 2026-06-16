"""statskills — experiment harness for studying agent skills on statistical tasks.

See ROADMAP.md for the research framing and the layered architecture. The
``core`` subpackage holds project-agnostic harness machinery (registry, config
loading, provenance, retry); domain layers (tasks, agent, skills, sandbox,
evaluation) depend on ``core``, never the reverse.
"""

__version__ = "0.1.0"
