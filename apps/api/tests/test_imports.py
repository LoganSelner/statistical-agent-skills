"""Smoke test — the api package imports and depends inward on the core harness."""

from __future__ import annotations


def test_package_imports() -> None:
    import statskills_api

    assert statskills_api.__version__


def test_core_harness_is_importable() -> None:
    # The api is a consumer of statskills (the dependency points inward).
    from statskills.agent.llm import LLM  # noqa: F401
    import statskills.reporting  # noqa: F401
