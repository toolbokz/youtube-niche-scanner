"""Base connector with rate limiting, retries, caching, and structured logging."""
from __future__ import annotations

import asyncio
import time
from abc import ABC, abstractmethod
from typing import Any

import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from app.config.settings import ConnectorConfig
from app.core.cache import get_cache, LocalCache
from app.core.logging import get_logger


class BaseConnector(ABC):
    """Abstract base class for all data connectors."""

    def __init__(self, config: ConnectorConfig, name: str = "base") -> None:
        self.config = config
        self.name = name
        self.logger = get_logger(f"connector.{name}")
        self.cache: LocalCache = get_cache()
        self._last_request_time: float = 0.0
        self._lock = asyncio.Lock()
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.config.timeout_seconds),
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                    "Accept-Language": "en-US,en;q=0.9",
                },
                follow_redirects=True,
            )
        return self._client

    async def _rate_limit(self) -> None:
        """Enforce rate limiting between requests."""
        async with self._lock:
            now = time.time()
            min_interval = 1.0 / self.config.rate_limit_per_second
            elapsed = now - self._last_request_time
            if elapsed < min_interval:
                await asyncio.sleep(min_interval - elapsed)
            self._last_request_time = time.time()

    async def _fetch(self, url: str, params: dict[str, Any] | None = None) -> str:
        """HTTP GET with rate limiting."""
        await self._rate_limit()
        client = await self._get_client()
        self.logger.debug("http_request", url=url, params=params)
        response = await client.get(url, params=params)
        response.raise_for_status()
        return response.text

    async def _fetch_json(self, url: str, params: dict[str, Any] | None = None) -> Any:
        """HTTP GET returning parsed JSON."""
        await self._rate_limit()
        client = await self._get_client()
        self.logger.debug("http_request_json", url=url, params=params)
        response = await client.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def _cache_key(self, identifier: str) -> str:
        return f"{self.name}:{identifier}"

    def _get_cached(self, identifier: str) -> Any | None:
        if not self.config.enabled:
            return None
        return self.cache.get(self.name, identifier, ttl_hours=self.config.cache_ttl_hours)

    def _set_cached(self, identifier: str, value: Any) -> None:
        self.cache.set(self.name, identifier, value)

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    @abstractmethod
    async def health_check(self) -> bool:
        """Verify connector is operational."""
        ...
