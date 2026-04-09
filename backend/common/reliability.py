"""Retry helpers for background services and integrations."""

from __future__ import annotations

import time
from typing import Callable, Iterable, TypeVar


T = TypeVar("T")


def retry_call(
    operation: Callable[[], T],
    *,
    retries: int = 3,
    initial_delay: float = 1.0,
    backoff: float = 2.0,
    retry_exceptions: Iterable[type[BaseException]] = (Exception,),
    logger=None,
    operation_name: str = "operation",
) -> T:
    """Execute an operation with bounded retry and exponential backoff."""
    delay = initial_delay
    retry_exceptions = tuple(retry_exceptions)

    for attempt in range(1, retries + 1):
        try:
            return operation()
        except retry_exceptions as exc:
            if attempt == retries:
                if logger:
                    logger.error(
                        "%s failed after %s attempts: %s",
                        operation_name,
                        attempt,
                        exc,
                    )
                raise

            if logger:
                logger.warning(
                    "%s failed on attempt %s/%s: %s. Retrying in %.1fs...",
                    operation_name,
                    attempt,
                    retries,
                    exc,
                    delay,
                )
            time.sleep(delay)
            delay *= backoff
