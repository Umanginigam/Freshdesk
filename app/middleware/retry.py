"""Retry with exponential backoff, honouring Retry-After on 429 responses."""

from __future__ import annotations

import time
from typing import Callable, Optional

import httpx

from app.freshdesk.errors import ApiTimeoutError, NetworkError, RateLimitedError

RETRYABLE_STATUS = {500, 502, 503, 504}
BASE_DELAY = 0.5
MAX_DELAY = 30.0


def backoff_delay(attempt: int, base: float = BASE_DELAY, cap: float = MAX_DELAY) -> float:
    return min(cap, base * (2**attempt))


def parse_retry_after(value: Optional[str], cap: float = MAX_DELAY) -> Optional[float]:
    if value is None:
        return None
    try:
        seconds = float(value)
    except ValueError:
        return None
    return max(0.0, min(seconds, cap))


def send_with_retries(
    send: Callable[[], httpx.Response],
    *,
    max_retries: int,
    sleep: Callable[[float], None] = time.sleep,
) -> httpx.Response:
    """Call `send` until it yields a non-retryable response or retries run out.

    - 429: wait for Retry-After (capped) or back off exponentially; raise RateLimitedError when exhausted.
    - 5xx (500/502/503/504): back off; the last response is returned for the caller to map.
    - Timeouts / transport errors: back off; raise ApiTimeoutError / NetworkError when exhausted.
    """
    attempt = 0
    while True:
        try:
            response = send()
        except httpx.TimeoutException as exc:
            if attempt >= max_retries:
                raise ApiTimeoutError() from exc
            sleep(backoff_delay(attempt))
            attempt += 1
            continue
        except httpx.TransportError as exc:
            if attempt >= max_retries:
                raise NetworkError() from exc
            sleep(backoff_delay(attempt))
            attempt += 1
            continue

        if response.status_code == 429:
            retry_after = parse_retry_after(response.headers.get("Retry-After"))
            if attempt >= max_retries:
                extra = {"retry_after_seconds": retry_after} if retry_after is not None else None
                raise RateLimitedError(extra=extra)
            sleep(retry_after if retry_after is not None else backoff_delay(attempt))
            attempt += 1
            continue

        if response.status_code in RETRYABLE_STATUS and attempt < max_retries:
            sleep(backoff_delay(attempt))
            attempt += 1
            continue

        return response
