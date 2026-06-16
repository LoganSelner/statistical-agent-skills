"""Sandboxed code execution — Executor/Session interfaces and backends.

The Docker-backed executor is the secure default; a local-subprocess executor is
provided for tests only and is never selected as an automatic fallback (ROADMAP §7).
"""
