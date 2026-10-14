from __future__ import annotations

import threading
import time
from collections import deque

from django.conf import settings


class RateLimitExceeded(Exception):
    def __init__(self, message: str, retry_after: float):
        super().__init__(message)
        self.retry_after = retry_after


class SlidingWindowLimiter:
    def __init__(self, max_calls: int, window_seconds: float = 60.0):
        self.max_calls = max(1, max_calls)
        self.window_seconds = window_seconds
        self._times: deque[float] = deque()
        self._lock = threading.Lock()

    def acquire(self, *, label: str = "API") -> None:
        now = time.monotonic()
        with self._lock:
            cutoff = now - self.window_seconds
            while self._times and self._times[0] < cutoff:
                self._times.popleft()
            if len(self._times) >= self.max_calls:
                retry_after = self.window_seconds - (now - self._times[0])
                raise RateLimitExceeded(
                    f"{label} rate limit reached ({self.max_calls}/min). "
                    f"Retry in {max(1, int(retry_after))}s.",
                    retry_after=max(1.0, retry_after),
                )
            self._times.append(now)


_ors_limiter: SlidingWindowLimiter | None = None
_ors_lock = threading.Lock()


def get_ors_limiter() -> SlidingWindowLimiter:
    global _ors_limiter
    with _ors_lock:
        limit = int(getattr(settings, "ORS_RATE_LIMIT_PER_MINUTE", 35))
        if _ors_limiter is None or _ors_limiter.max_calls != max(1, limit):
            _ors_limiter = SlidingWindowLimiter(max_calls=limit, window_seconds=60.0)
        return _ors_limiter


def acquire_ors_slot() -> None:
    get_ors_limiter().acquire(label="OpenRouteService")
