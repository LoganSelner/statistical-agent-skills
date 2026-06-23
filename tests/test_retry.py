"""Tests for the parameterized transient-retry policy."""

from __future__ import annotations

import pytest

from statskills.core.retry import retry_transient


@pytest.fixture(autouse=True)
def _no_backoff_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    # Skip tenacity's real backoff so the tests are instant.
    monkeypatch.setattr("tenacity.nap.sleep", lambda *_a, **_k: None)


def test_retries_a_transient_error_up_to_attempts_then_reraises():
    calls = 0

    @retry_transient(attempts=3)
    def always_fails() -> None:
        nonlocal calls
        calls += 1
        raise ConnectionError("transient")

    with pytest.raises(ConnectionError):
        always_fails()
    assert calls == 3


def test_attempts_one_bounds_a_stalled_call_to_a_single_try():
    calls = 0

    @retry_transient(attempts=1)
    def always_fails() -> None:
        nonlocal calls
        calls += 1
        raise TimeoutError("stalled")

    with pytest.raises(TimeoutError):
        always_fails()
    assert calls == 1


def test_programming_errors_are_not_retried():
    calls = 0

    @retry_transient(attempts=4)
    def bad() -> None:
        nonlocal calls
        calls += 1
        raise ValueError("a programming error, not transient")

    with pytest.raises(ValueError):
        bad()
    assert calls == 1
