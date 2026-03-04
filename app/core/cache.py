"""Multi-tier cache: in-memory LRU → optional Redis → disk (orjson).

Performance characteristics
---------------------------
- Memory hits:  ~0.001 ms  (dict lookup)
- Redis hits:   ~0.5 ms    (localhost TCP)
- Disk hits:    ~2 ms      (orjson parse from SSD)
- Full miss:    ~0 ms overhead before the real I/O
"""
from __future__ import annotations

import asyncio
import hashlib
import time
from collections import OrderedDict
from pathlib import Path
from typing import Any

try:
    import orjson

    def _dumps(obj: Any) -> bytes:
        return orjson.dumps(obj, option=orjson.OPT_NON_STR_KEYS | orjson.OPT_SERIALIZE_NUMPY)

    def _loads(raw: bytes | str) -> Any:
        return orjson.loads(raw)
except ImportError:
    import json as _json

    def _dumps(obj: Any) -> bytes:  # type: ignore[misc]
        return _json.dumps(obj, default=str).encode()

    def _loads(raw: bytes | str) -> Any:  # type: ignore[misc]
        return _json.loads(raw)

from app.core.logging import get_logger

logger = get_logger(__name__)

# ── Tier-1: LRU memory cache ────────────────────────────────────────────────

_MAX_MEMORY_ITEMS = 4096


class _LRUDict(OrderedDict):
    """Bounded ordered-dict that evicts LRU entries."""

    def __init__(self, maxsize: int = _MAX_MEMORY_ITEMS) -> None:
        super().__init__()
        self._maxsize = maxsize

    def __setitem__(self, key: str, value: Any) -> None:
        if key in self:
            self.move_to_end(key)
        super().__setitem__(key, value)
        while len(self) > self._maxsize:
            self.popitem(last=False)

    def __getitem__(self, key: str) -> Any:
        self.move_to_end(key)
        return super().__getitem__(key)


# ── Tier-2: Optional Redis wrapper ──────────────────────────────────────────

class _RedisLayer:
    """Thin async Redis wrapper — degrades gracefully if unreachable."""

    def __init__(self, url: str = "redis://localhost:6379/0") -> None:
        self._url = url
        self._pool: Any = None
        self._available: bool | None = None

    async def _get_pool(self) -> Any:
        if self._pool is not None:
            return self._pool
        try:
            import redis.asyncio as aioredis
            self._pool = aioredis.from_url(
                self._url, decode_responses=False, socket_connect_timeout=1,
            )
            await self._pool.ping()
            self._available = True
            logger.info("redis_connected", url=self._url)
            return self._pool
        except Exception:
            self._available = False
            return None

    @property
    def available(self) -> bool:
        return self._available is True

    async def get(self, key: str) -> bytes | None:
        pool = await self._get_pool()
        if pool is None:
            return None
        try:
            return await pool.get(key)  # type: ignore[return-value]
        except Exception:
            return None

    async def set(self, key: str, value: bytes, ttl_seconds: int) -> None:
        pool = await self._get_pool()
        if pool is None:
            return
        try:
            await pool.set(key, value, ex=ttl_seconds)
        except Exception:
            pass

    async def delete(self, key: str) -> None:
        pool = await self._get_pool()
        if pool is None:
            return
        try:
            await pool.delete(key)
        except Exception:
            pass


# ── Main cache class ─────────────────────────────────────────────────────────

class LocalCache:
    """Multi-tier cache: LRU memory → optional Redis → disk (orjson)."""

    def __init__(
        self,
        cache_dir: str = "data/cache",
        default_ttl_hours: int = 24,
        redis_url: str | None = None,
        memory_max_items: int = _MAX_MEMORY_ITEMS,
    ) -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.default_ttl_seconds = default_ttl_hours * 3600
        self._memory = _LRUDict(maxsize=memory_max_items)
        self._redis = _RedisLayer(redis_url) if redis_url else None
        self._hits = {"memory": 0, "redis": 0, "disk": 0, "miss": 0}

    def _make_key(self, namespace: str, identifier: str) -> str:
        raw = f"{namespace}:{identifier}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def _cache_path(self, key: str) -> Path:
        # Shard into 256 sub-dirs to avoid huge flat directories
        return self.cache_dir / key[:2] / f"{key}.bin"

    # ── Sync get (memory + disk) — used by connectors ────────────────

    def get(self, namespace: str, identifier: str, ttl_hours: int | None = None) -> Any | None:
        """Retrieve cached value if not expired (sync: memory → disk)."""
        key = self._make_key(namespace, identifier)
        ttl = (ttl_hours * 3600) if ttl_hours else self.default_ttl_seconds
        now = time.time()

        # Tier-1: memory
        if key in self._memory:
            ts, value = self._memory[key]
            if now - ts < ttl:
                self._hits["memory"] += 1
                return value
            del self._memory[key]

        # Tier-3: disk
        path = self._cache_path(key)
        if path.exists():
            try:
                raw = path.read_bytes()
                data = _loads(raw)
                if now - data["t"] < ttl:
                    self._memory[key] = (data["t"], data["v"])
                    self._hits["disk"] += 1
                    return data["v"]
                path.unlink(missing_ok=True)
            except Exception:
                path.unlink(missing_ok=True)

        self._hits["miss"] += 1
        return None

    # ── Async get (memory → Redis → disk) ────────────────────────────

    async def aget(self, namespace: str, identifier: str, ttl_hours: int | None = None) -> Any | None:
        """Async retrieve: memory → Redis → disk."""
        key = self._make_key(namespace, identifier)
        ttl = (ttl_hours * 3600) if ttl_hours else self.default_ttl_seconds
        now = time.time()

        # Tier-1: memory
        if key in self._memory:
            ts, value = self._memory[key]
            if now - ts < ttl:
                self._hits["memory"] += 1
                return value
            del self._memory[key]

        # Tier-2: Redis
        if self._redis:
            raw = await self._redis.get(f"gs:{key}")
            if raw is not None:
                try:
                    data = _loads(raw)
                    if now - data["t"] < ttl:
                        self._memory[key] = (data["t"], data["v"])
                        self._hits["redis"] += 1
                        return data["v"]
                except Exception:
                    pass

        # Tier-3: disk
        path = self._cache_path(key)
        if path.exists():
            try:
                raw_bytes = path.read_bytes()
                data = _loads(raw_bytes)
                if now - data["t"] < ttl:
                    self._memory[key] = (data["t"], data["v"])
                    self._hits["disk"] += 1
                    # Backfill Redis
                    if self._redis:
                        payload = _dumps(data)
                        asyncio.create_task(self._redis.set(f"gs:{key}", payload, int(ttl)))
                    return data["v"]
                path.unlink(missing_ok=True)
            except Exception:
                path.unlink(missing_ok=True)

        self._hits["miss"] += 1
        return None

    def set(self, namespace: str, identifier: str, value: Any, ttl_hours: int | None = None) -> None:
        """Store value in cache (sync: memory + disk)."""
        key = self._make_key(namespace, identifier)
        ts = time.time()

        # Tier-1: memory
        self._memory[key] = (ts, value)

        # Tier-3: disk
        path = self._cache_path(key)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(_dumps({"t": ts, "v": value}))
        except Exception as e:
            logger.warning("cache_write_error", error=str(e), key=key[:16])

    async def aset(self, namespace: str, identifier: str, value: Any, ttl_hours: int | None = None) -> None:
        """Async store: memory + Redis + disk."""
        key = self._make_key(namespace, identifier)
        ts = time.time()
        ttl = (ttl_hours * 3600) if ttl_hours else self.default_ttl_seconds
        payload = _dumps({"t": ts, "v": value})

        # Tier-1: memory
        self._memory[key] = (ts, value)

        # Tier-2: Redis (fire and forget)
        if self._redis:
            asyncio.create_task(self._redis.set(f"gs:{key}", payload, int(ttl)))

        # Tier-3: disk
        path = self._cache_path(key)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
        except Exception as e:
            logger.warning("cache_write_error", error=str(e), key=key[:16])

    def invalidate(self, namespace: str, identifier: str) -> None:
        """Remove a cached entry from all tiers."""
        key = self._make_key(namespace, identifier)
        self._memory.pop(key, None)
        self._cache_path(key).unlink(missing_ok=True)
        if self._redis:
            asyncio.create_task(self._redis.delete(f"gs:{key}"))

    def clear_namespace(self, namespace: str) -> int:
        """Clear all entries (best-effort since keys are hashed)."""
        count = 0
        for subdir in self.cache_dir.iterdir():
            if subdir.is_dir():
                for path in subdir.glob("*.bin"):
                    path.unlink(missing_ok=True)
                    count += 1
        # Also clear legacy .json files
        for path in self.cache_dir.glob("*.json"):
            path.unlink(missing_ok=True)
            count += 1
        self._memory.clear()
        return count

    def stats(self) -> dict[str, Any]:
        """Return cache statistics with hit-rate breakdown."""
        total_files = 0
        total_size = 0
        for subdir in self.cache_dir.iterdir():
            if subdir.is_dir():
                for f in subdir.glob("*.bin"):
                    total_files += 1
                    total_size += f.stat().st_size
        # Also count legacy .json
        for f in self.cache_dir.glob("*.json"):
            total_files += 1
            total_size += f.stat().st_size

        total_hits = sum(self._hits.values())
        hit_rate = (
            round((total_hits - self._hits["miss"]) / total_hits * 100, 1)
            if total_hits > 0 else 0.0
        )
        return {
            "entries_on_disk": total_files,
            "entries_in_memory": len(self._memory),
            "total_disk_size_mb": round(total_size / (1024 * 1024), 2),
            "hit_counts": dict(self._hits),
            "hit_rate_pct": hit_rate,
            "redis_available": self._redis.available if self._redis else False,
        }


_cache_instance: LocalCache | None = None


def get_cache(
    cache_dir: str = "data/cache",
    ttl_hours: int = 24,
    redis_url: str | None = None,
) -> LocalCache:
    """Get or create the global cache instance."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = LocalCache(
            cache_dir=cache_dir,
            default_ttl_hours=ttl_hours,
            redis_url=redis_url,
        )
    return _cache_instance
