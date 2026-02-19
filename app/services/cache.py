"""Two-tier caching service: Redis (primary) with in-memory fallback.

When Redis is unavailable the service automatically degrades to a
thread-safe dictionary with TTL expiry, so the app keeps running.
"""

import json
import threading
import time
from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Dict, Optional

from app.config import settings


@dataclass
class _MemoryEntry:
    """In-memory cache entry with expiration timestamp."""
    value: Dict[str, Any]
    expires_at: float


class CacheService:
    """Redis-first cache that falls back to local memory on connection errors."""
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._memory_store: Dict[str, _MemoryEntry] = {}
        self._redis_client: Any = None
        self._redis_ready = False
        self._init_redis()

    def _init_redis(self) -> None:
        if not settings.ENABLE_REDIS_CACHE:
            return

        try:
            import redis

            client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
            client.ping()
            self._redis_client = client
            self._redis_ready = True
        except Exception:
            self._redis_client = None
            self._redis_ready = False

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        if self._redis_ready and self._redis_client is not None:
            try:
                raw = self._redis_client.get(key)
                if raw:
                    return json.loads(raw)
            except Exception:
                self._redis_ready = False

        now = time.time()
        with self._lock:
            entry = self._memory_store.get(key)
            if entry is None:
                return None
            if entry.expires_at <= now:
                self._memory_store.pop(key, None)
                return None
            return entry.value

    def set(self, key: str, value: Dict[str, Any], ttl_seconds: int) -> None:
        if self._redis_ready and self._redis_client is not None:
            try:
                self._redis_client.setex(key, ttl_seconds, json.dumps(value))
                return
            except Exception:
                self._redis_ready = False

        expires_at = time.time() + ttl_seconds
        with self._lock:
            self._memory_store[key] = _MemoryEntry(value=value, expires_at=expires_at)

    def delete_prefix(self, prefix: str) -> int:
        deleted = 0

        if self._redis_ready and self._redis_client is not None:
            try:
                keys = self._redis_client.keys(f"{prefix}*")
                if keys:
                    deleted += int(self._redis_client.delete(*keys))
            except Exception:
                self._redis_ready = False

        with self._lock:
            for key in list(self._memory_store.keys()):
                if key.startswith(prefix):
                    self._memory_store.pop(key, None)
                    deleted += 1

        return deleted


def build_data_cache_key(path: str, params: Dict[str, Any]) -> str:
    """Deterministic cache key for /data endpoint responses."""
    canonical = {k: v for k, v in sorted(params.items()) if v is not None}
    blob = json.dumps({"path": path, "params": canonical}, sort_keys=True)
    digest = sha256(blob.encode("utf-8")).hexdigest()
    return f"udc:data:{digest}"


def build_assistant_cache_key(params: Dict[str, Any]) -> str:
    """Deterministic cache key for /assistant/query responses."""
    canonical = {k: v for k, v in sorted(params.items()) if v is not None}
    blob = json.dumps({"type": "assistant", "params": canonical}, sort_keys=True)
    digest = sha256(blob.encode("utf-8")).hexdigest()
    return f"udc:assistant:{digest}"


cache_service = CacheService()
