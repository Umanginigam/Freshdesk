"""Client-side sliding-window rate limiter.

Keeps the connector under Freshdesk's per-minute budget so we rarely see a 429 at all.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from typing import Callable


class RateLimiter:
    def __init__(
        self,
        max_calls: int,
        period: float = 60.0,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ):
        if max_calls < 1:
            raise ValueError("max_calls must be at least 1")
        if period <= 0:
            raise ValueError("period must be positive")
        self._max_calls = max_calls
        self._period = period
        self._clock = clock
        self._sleep = sleep
        self._calls: deque[float] = deque()
        self._lock = threading.Lock()

    def acquire(self) -> None:
        """Block until a call is allowed, then record it."""
        while True:
            with self._lock:
                now = self._clock()
                while self._calls and now - self._calls[0] >= self._period:
                    self._calls.popleft()
                if len(self._calls) < self._max_calls:
                    self._calls.append(now)
                    return
                wait = self._period - (now - self._calls[0])
            self._sleep(max(wait, 0.01))
