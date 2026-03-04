"""Keyword Expansion Engine — parallelised seed expansion."""
from __future__ import annotations

import asyncio
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
        """Expand a single seed keyword using all sources concurrently."""
        # Fire all expansion tasks in parallel
        yt_task = self.yt_autocomplete.expand_keyword(seed, prefixes=use_prefixes)
        multi_task = self.keyword_scraper.expand_all_sources(seed)

        # Question-based expansions — all prefixes in parallel
        question_prefixes = ["how to", "what is", "why", "best", "top", "vs"]
        question_tasks = [
            self.yt_autocomplete.get_suggestions(f"{prefix} {seed}")
            for prefix in question_prefixes
        ]

        results = await asyncio.gather(
            yt_task, multi_task, *question_tasks, return_exceptions=True,
        )

        all_keywords: set[str] = set()

        # YouTube autocomplete
        if not isinstance(results[0], BaseException):
            all_keywords.update(results[0])
        # Multi-source
        if not isinstance(results[1], BaseException):
            all_keywords.update(results[1])
        # Question expansions
        for r in results[2:]:
            if not isinstance(r, BaseException) and hasattr(r, "suggestions"):
                all_keywords.update(r.suggestions)

        all_keywords.discard(seed.lower())

        logger.info("seed_expanded", seed=seed, total_keywords=len(all_keywords))
        return sorted(all_keywords)

    async def expand_batch(
        self, seeds: list[str], use_prefixes: bool = False
    ) -> dict[str, list[str]]:
        """Expand multiple seed keywords concurrently."""
        tasks = [
            self.expand_seed(seed, use_prefixes=use_prefixes) for seed in seeds
        ]
        expanded_lists = await asyncio.gather(*tasks, return_exceptions=True)

        results: dict[str, list[str]] = {}
        for seed, expanded in zip(seeds, expanded_lists):
            if isinstance(expanded, BaseException):
                logger.warning("seed_expand_error", seed=seed, error=str(expanded))
                results[seed] = []
            else:
                results[seed] = expanded
        return results
