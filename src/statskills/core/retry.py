"""Shared retry policy for transient external-service failures.

One definition reused by every external-service client (the EdenAI LLM client,
sandbox calls, dataset fetches) so the policy can't drift between modules. The
retry predicate is deliberately **type-based and provider-agnostic**: it retries
anything that is not an obvious programming error (``TypeError``/``ValueError``/
...). This keeps the module in ``core`` with no provider-SDK imports — teaching it
to recognize provider auth exceptions (to *not* retry a 401/4xx) would invert the
dependency rule. The accepted minor cost: an auth/4xx failure retries the full
budget before surfacing.
"""

from __future__ import annotations

from collections.abc import Callable
import logging
from typing import Any, TypeVar

from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)

_F = TypeVar("_F", bound=Callable[..., Any])

# Programming errors that will not recover on retry — re-raised immediately.
NON_RETRYABLE: tuple[type[BaseException], ...] = (
    TypeError,
    ValueError,
    KeyError,
    AttributeError,
    SyntaxError,
)


def retry_transient(attempts: int = 3, *, max_wait: float = 60.0) -> Callable[[_F], _F]:
    """Build a retry decorator for one external call (one HTTP/SDK request).

    Exponential backoff over ``attempts`` tries, re-raising the last exception so the
    caller can wrap it in a domain error. The predicate is type-based (retry anything
    that is not an obvious programming error). A caller whose request already carries a
    timeout keeps ``attempts`` low, so a stalled call fails fast instead of retrying the
    full timeout several times.
    """
    return retry(
        retry=retry_if_exception(lambda e: not isinstance(e, NON_RETRYABLE)),
        wait=wait_exponential(multiplier=1, min=2, max=max_wait),
        stop=stop_after_attempt(attempts),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
