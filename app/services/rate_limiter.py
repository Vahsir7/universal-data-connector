import threading
import time
from dataclasses import dataclass
from typing import Dict, Tuple

from app.config import settings


@dataclass
class _Bucket:
    count: int
    window_start: float


class SourceRateLimiter:
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
