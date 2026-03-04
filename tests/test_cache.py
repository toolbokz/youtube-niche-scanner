"""Tests for the cache subsystem."""
from __future__ import annotations

import tempfile
from pathlib import Path

from app.core.cache import LocalCache


def test_cache_set_get() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = LocalCache(cache_dir=tmpdir, default_ttl_hours=1)
        cache.set("test", "key1", {"data": "value"})
        result = cache.get("test", "key1")
        assert result == {"data": "value"}


def test_cache_miss() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = LocalCache(cache_dir=tmpdir, default_ttl_hours=1)
        result = cache.get("test", "nonexistent")
        assert result is None


def test_cache_invalidate() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = LocalCache(cache_dir=tmpdir, default_ttl_hours=1)
        cache.set("test", "key1", "data")
        cache.invalidate("test", "key1")
        result = cache.get("test", "key1")
        assert result is None


def test_cache_stats() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = LocalCache(cache_dir=tmpdir, default_ttl_hours=1)
        cache.set("test", "key1", "data1")
        cache.set("test", "key2", "data2")
        stats = cache.stats()
        assert stats["entries_on_disk"] == 2
        assert stats["entries_in_memory"] == 2


def test_cache_clear() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = LocalCache(cache_dir=tmpdir, default_ttl_hours=1)
        cache.set("test", "key1", "data1")
        cache.set("test", "key2", "data2")
        count = cache.clear_namespace("test")
        assert count == 2
        assert cache.get("test", "key1") is None
