"""Async HTTP client for the Growth Strategist FastAPI backend."""
from __future__ import annotations

from typing import Any

import httpx

_DEFAULT_BASE = "http://localhost:8000"
_TIMEOUT = httpx.Timeout(300.0, connect=10.0)  # Long timeout for pipeline runs


class APIClient:
    """Thin wrapper around the FastAPI backend endpoints."""

    def __init__(self, base_url: str = _DEFAULT_BASE) -> None:
        self.base_url = base_url.rstrip("/")

    # ── helpers ────────────────────────────────────────────────────────

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    # ── endpoints ─────────────────────────────────────────────────────

    def health(self) -> dict[str, Any]:
        """GET /health — returns {status, version}."""
        try:
            with httpx.Client(timeout=_TIMEOUT) as c:
                r = c.get(self._url("/health"))
                r.raise_for_status()
                return r.json()
        except Exception as exc:
            return {"status": "error", "detail": str(exc)}

    def analyze(
        self,
        seed_keywords: list[str],
        top_n: int = 10,
        videos_per_niche: int = 10,
    ) -> dict[str, Any]:
        """POST /analyze — run the full pipeline."""
        payload = {
            "seed_keywords": seed_keywords,
            "top_n": top_n,
            "videos_per_niche": videos_per_niche,
        }
        with httpx.Client(timeout=_TIMEOUT) as c:
            r = c.post(self._url("/analyze"), json=payload)
            r.raise_for_status()
            return r.json()

    def discover(
        self,
        deep: bool = False,
        max_seeds: int = 20,
        top_n: int = 20,
        videos_per_niche: int = 10,
    ) -> dict[str, Any]:
        """POST /discover — automatic niche discovery."""
        payload = {
            "deep": deep,
            "max_seeds": max_seeds,
            "top_n": top_n,
            "videos_per_niche": videos_per_niche,
        }
        with httpx.Client(timeout=_TIMEOUT) as c:
            r = c.post(self._url("/discover"), json=payload)
            r.raise_for_status()
            return r.json()

    def cache_stats(self) -> dict[str, Any]:
        """GET /cache/stats — cache statistics."""
        try:
            with httpx.Client(timeout=_TIMEOUT) as c:
                r = c.get(self._url("/cache/stats"))
                r.raise_for_status()
                return r.json()
        except Exception as exc:
            return {"error": str(exc)}
