"""Keyword Expansion Engine - expands seeds and groups into clusters."""
from __future__ import annotations

from typing import Any

from app.connectors.youtube_autocomplete import YouTubeAutocompleteConnector
from app.connectors.keyword_scraper import KeywordScraperConnector
from app.core.logging import get_logger
from app.core.models import KeywordCluster

logger = get_logger(__name__)


class KeywordExpansionEngine:
    """Expand seed keywords using multiple sources and cluster them."""

    def __init__(
        self,
        yt_autocomplete: YouTubeAutocompleteConnector,
        keyword_scraper: KeywordScraperConnector,
    ) -> None:
        self.yt_autocomplete = yt_autocomplete
        self.keyword_scraper = keyword_scraper

    async def expand_seed(self, seed: str, use_prefixes: bool = True) -> list[str]:
        """Expand a single seed keyword using all sources."""
        all_keywords: set[str] = set()

        # YouTube autocomplete expansion
        yt_suggestions = await self.yt_autocomplete.expand_keyword(seed, prefixes=use_prefixes)
        all_keywords.update(yt_suggestions)

        # Multi-source keyword suggestions
        multi_suggestions = await self.keyword_scraper.expand_all_sources(seed)
        all_keywords.update(multi_suggestions)

        # Add question-based expansions
        question_prefixes = ["how to", "what is", "why", "best", "top", "vs"]
        for prefix in question_prefixes:
            yt_q = await self.yt_autocomplete.get_suggestions(f"{prefix} {seed}")
            all_keywords.update(yt_q.suggestions)

        # Remove original seed
        all_keywords.discard(seed.lower())

        logger.info("seed_expanded", seed=seed, total_keywords=len(all_keywords))
        return sorted(all_keywords)

    async def expand_batch(
        self, seeds: list[str], use_prefixes: bool = False
    ) -> dict[str, list[str]]:
        """Expand multiple seed keywords."""
        results: dict[str, list[str]] = {}
        for seed in seeds:
            expanded = await self.expand_seed(seed, use_prefixes=use_prefixes)
            results[seed] = expanded
        return results
