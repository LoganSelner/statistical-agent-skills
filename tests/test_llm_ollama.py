"""Ollama round-trip smoke test — skipped unless a local Ollama is reachable.

Runs only when an Ollama server answers at the resolved base URL (default
http://localhost:11434/v1, or OLLAMA_BASE_URL). Requires the model to be pulled
(`ollama pull qwen2.5-coder:7b`). Marked ``slow``; it never fails CI — it passes on a
real round trip or skips.
"""

from __future__ import annotations

import os
import socket
from urllib.parse import urlparse

import pytest

from statskills.agent.llm import LLMConfig, build_llm

_MODEL = "qwen2.5-coder:7b"
_DEFAULT_BASE_URL = "http://localhost:11434/v1"


def _ollama_reachable() -> bool:
    url = os.environ.get("OLLAMA_BASE_URL", _DEFAULT_BASE_URL)
    parsed = urlparse(url)
    host, port = parsed.hostname or "localhost", parsed.port or 11434
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except OSError:
        return False


pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(not _ollama_reachable(), reason="Ollama not reachable"),
]


def test_ollama_round_trip():
    llm = build_llm(LLMConfig(provider="ollama", model=_MODEL, max_tokens=20))
    try:
        resp = llm.complete([{"role": "user", "content": "Reply with just: pong"}])
    except RuntimeError as e:
        pytest.skip(f"Ollama reachable but the call failed (model pulled?): {e}")
    assert resp.text.strip()  # a non-empty completion
    assert resp.model  # echoes a model id
