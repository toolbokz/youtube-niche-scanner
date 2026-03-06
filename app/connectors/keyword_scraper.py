"""Keyword expansion scraper using multiple sources."""
from __future__ import annotations

from urllib.parse import quote_plus

from app.config.settings import ConnectorConfig
from app.connectors.base import BaseConnector


class KeywordScraperConnector(BaseConnector):
    """Scrape keyword suggestions from multiple free sources."""

    def __init__(self, config: ConnectorConfig) -> None:
        super().__init__(config, name="keyword_scraper")

    async def google_autocomplete(self, query: str) -> list[str]:
        """Get Google autocomplete suggestions."""
        cache_key = f"google_ac:{query.lower().strip()}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        try:
            url = "https://suggestqueries.google.com/complete/search"
            params = {"client": "firefox", "q": query, "hl": "en"}
            data = await self._fetch_json(url, params=params)

            suggestions: list[str] = []
            if isinstance(data, list) and len(data) > 1:
                suggestions = [s for s in data[1] if isinstance(s, str)]

            self._set_cached(cache_key, suggestions)
            return suggestions

        except Exception as e:
            self.logger.warning("google_ac_error", query=query, error=str(e))
            return []

    async def bing_autocomplete(self, query: str) -> list[str]:
        """Get Bing autocomplete suggestions."""
        cache_key = f"bing_ac:{query.lower().strip()}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        try:
            url = f"https://api.bing.com/osjson.aspx?query={quote_plus(query)}"
            data = await self._fetch_json(url)

            suggestions: list[str] = []
            if isinstance(data, list) and len(data) > 1:
                suggestions = [s for s in data[1] if isinstance(s, str)]

            self._set_cached(cache_key, suggestions)
            return suggestions

        except Exception as e:
            self.logger.warning("bing_ac_error", query=query, error=str(e))
            return []

    async def expand_all_sources(self, query: str) -> list[str]:
        """Get suggestions from all available sources concurrently."""
        import asyncio
        google_task = self.google_autocomplete(query)
        bing_task = self.bing_autocomplete(query)
        google, bing = await asyncio.gather(google_task, bing_task, return_exceptions=True)

        all_suggestions: set[str] = set()
        if not isinstance(google, BaseException):
            all_suggestions.update(google)
        if not isinstance(bing, BaseException):
            all_suggestions.update(bing)

        all_suggestions.discard(query.lower())
        return sorted(all_suggestions)

    async def health_check(self) -> bool:
        try:
            results = await self.google_autocomplete("test")
            return len(results) > 0
        except Exception:
            return False
