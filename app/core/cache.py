"""Local disk cache to minimize API calls."""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)


class LocalCache:
    """File-based cache with TTL support using diskcache."""

    def __init__(self, cache_dir: str = "data/cache", default_ttl_hours: int = 24) -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.default_ttl_seconds = default_ttl_hours * 3600
        self._memory: dict[str, tuple[float, Any]] = {}

    def _make_key(self, namespace: str, identifier: str) -> str:
        raw = f"{namespace}:{identifier}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def _cache_path(self, key: str) -> Path:
        return self.cache_dir / f"{key}.json"

    def get(self, namespace: str, identifier: str, ttl_hours: int | None = None) -> Any | None:
        """Retrieve cached value if not expired."""
        key = self._make_key(namespace, identifier)
        ttl = (ttl_hours * 3600) if ttl_hours else self.default_ttl_seconds

        # Check memory cache first
        if key in self._memory:
            ts, value = self._memory[key]
            if time.time() - ts < ttl:
                return value
            del self._memory[key]

        # Check disk cache
        path = self._cache_path(key)
        if path.exists():
            try:
                data = json.loads(path.read_text())
                if time.time() - data["timestamp"] < ttl:
                    self._memory[key] = (data["timestamp"], data["value"])
                    return data["value"]
                path.unlink(missing_ok=True)
            except (json.JSONDecodeError, KeyError):
                path.unlink(missing_ok=True)

        return None

    def set(self, namespace: str, identifier: str, value: Any) -> None:
        """Store value in cache."""
        key = self._make_key(namespace, identifier)
        ts = time.time()

        # Memory cache
        self._memory[key] = (ts, value)

        # Disk cache
        path = self._cache_path(key)
        try:
            path.write_text(json.dumps({"timestamp": ts, "value": value}, default=str))
        except Exception as e:
            logger.warning("cache_write_error", error=str(e), key=key)

    def invalidate(self, namespace: str, identifier: str) -> None:
        """Remove a cached entry."""
        key = self._make_key(namespace, identifier)
        self._memory.pop(key, None)
        self._cache_path(key).unlink(missing_ok=True)

    def clear_namespace(self, namespace: str) -> int:
        """Clear all entries (best-effort since keys are hashed)."""
        count = 0
        for path in self.cache_dir.glob("*.json"):
            path.unlink(missing_ok=True)
            count += 1
        self._memory.clear()
        return count

    def stats(self) -> dict[str, Any]:
        """Return cache statistics."""
        files = list(self.cache_dir.glob("*.json"))
        total_size = sum(f.stat().st_size for f in files)
        return {
            "entries_on_disk": len(files),
            "entries_in_memory": len(self._memory),
            "total_disk_size_mb": round(total_size / (1024 * 1024), 2),
        }


_cache_instance: LocalCache | None = None


def get_cache(cache_dir: str = "data/cache", ttl_hours: int = 24) -> LocalCache:
    """Get or create the global cache instance."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = LocalCache(cache_dir=cache_dir, default_ttl_hours=ttl_hours)
    return _cache_instance
