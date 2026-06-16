"""Project-agnostic harness core.

Config loading, the component registry, run provenance, and the shared retry
policy. Nothing here knows about statistics, skills, tasks, or the agent —
domain code depends on ``core``, never the reverse (ROADMAP §2).
"""
