"""YouTube autocomplete connector for keyword discovery."""
from __future__ import annotations

import json
from typing import Any

from app.config.settings import ConnectorConfig
from app.connectors.base import BaseConnector
from app.core.models import AutocompleteResult


YOUTUBE_AUTOCOMPLETE_URL = "https://suggestqueries-clients6.youtube.com/complete/search"


class YouTubeAutocompleteConnector(BaseConnector):
    """Scrape YouTube's autocomplete API for keyword suggestions."""

    def __init__(self, config: ConnectorConfig) -> None:
        super().__init__(config, name="youtube_autocomplete")

    async def get_suggestions(self, query: str) -> AutocompleteResult:
        """Get autocomplete suggestions for a query."""
        cache_key = f"suggestions:{query.lower().strip()}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            self.logger.debug("cache_hit", query=query)
            return AutocompleteResult(**cached)

        try:
            params = {
                "client": "youtube",
                "q": query,
                "ds": "yt",
                "hl": "en",
                "gl": "us",
            }
            raw = await self._fetch(YOUTUBE_AUTOCOMPLETE_URL, params=params)
            suggestions = self._parse_response(raw)

            result = AutocompleteResult(
                query=query,
                suggestions=suggestions,
                source="youtube_autocomplete",
            )
            self._set_cached(cache_key, result.model_dump(mode="json"))
            self.logger.info("suggestions_fetched", query=query, count=len(suggestions))
            return result

        except Exception as e:
            self.logger.error("suggestion_error", query=query, error=str(e))
            return AutocompleteResult(query=query, suggestions=[], source="youtube_autocomplete")

    def _parse_response(self, raw: str) -> list[str]:
        """Parse JSONP response from YouTube autocomplete."""
        try:
            # Response is JSONP: window.google.ac.h(...)
            start = raw.index("(") + 1
            end = raw.rindex(")")
            data = json.loads(raw[start:end])
            if isinstance(data, list) and len(data) > 1:
                return [item[0] for item in data[1] if isinstance(item, list) and item]
        except (ValueError, json.JSONDecodeError, IndexError):
            pass
        return []

    async def expand_keyword(self, seed: str, prefixes: bool = True) -> list[str]:
        """Expand a seed keyword using autocomplete with alphabet prefixes."""
        all_suggestions: list[str] = []

        # Direct suggestions
        result = await self.get_suggestions(seed)
        all_suggestions.extend(result.suggestions)

        if prefixes:
            # Expand with a-z prefixes
            for char in "abcdefghijklmnopqrstuvwxyz":
                result = await self.get_suggestions(f"{seed} {char}")
                all_suggestions.extend(result.suggestions)

        # Deduplicate while preserving order
        seen: set[str] = set()
        unique: list[str] = []
        for s in all_suggestions:
            lower = s.lower().strip()
            if lower not in seen and lower != seed.lower().strip():
                seen.add(lower)
                unique.append(s)

        self.logger.info("keyword_expanded", seed=seed, total=len(unique))
        return unique

    async def health_check(self) -> bool:
        try:
            result = await self.get_suggestions("test")
            return len(result.suggestions) > 0
        except Exception:
            return False
