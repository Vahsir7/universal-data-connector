"""Sliding-window rate limiter keyed by (source, client_id).

Each source-client pair gets its own time window; once the limit is hit
the caller receives a Retry-After hint (seconds).
"""

import threading
import time
from dataclasses import dataclass
from typing import Dict, Tuple

from app.config import settings


@dataclass
class _Bucket:
    """Tracks request count within a rolling window."""
    count: int
    window_start: float


class SourceRateLimiter:
    """Thread-safe in-memory per-source rate limiter."""
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._buckets: Dict[str, _Bucket] = {}

    def allow(self, source: str, client_id: str) -> Tuple[bool, int]:
        now = time.time()
        window = settings.RATE_LIMIT_WINDOW_SECONDS
        key = f"{source}:{client_id}"

        with self._lock:
            bucket = self._buckets.get(key)
            if bucket is None or (now - bucket.window_start) >= window:
                self._buckets[key] = _Bucket(count=1, window_start=now)
                return True, 0

            if bucket.count >= settings.RATE_LIMIT_PER_SOURCE:
                retry_after = int(max(1, window - (now - bucket.window_start)))
                return False, retry_after

            bucket.count += 1
            return True, 0


rate_limiter = SourceRateLimiter()
