"""Discovery Engine — auto-discovers trending niches from multiple sources.

This engine requires NO seed keywords. It gathers raw topic signals from
Google Trends, YouTube trending, Reddit rising posts, YouTube autocomplete
expansion, and other public sources, then feeds them into the existing
keyword-expansion → clustering → ranking pipeline.
"""
from __future__ import annotations

import asyncio
from typing import Any

from app.config import get_settings
from app.connectors.google_trends import GoogleTrendsConnector
from app.connectors.reddit import RedditConnector
from app.connectors.youtube_autocomplete import YouTubeAutocompleteConnector
from app.connectors.youtube_search import YouTubeSearchConnector
from app.core.logging import get_logger
from app.core.models import DiscoverySource

logger = get_logger(__name__)

# Broad seed categories to sample from when discovering fresh trends
_DISCOVERY_CATEGORIES: list[str] = [
    "how to make money online",
    "technology trends",
    "health and fitness tips",
    "personal finance investing",
    "artificial intelligence",
    "side hustle ideas",
    "productivity tips",
    "crypto blockchain",
    "weight loss diet",
    "programming tutorial",
    "travel budget",
    "cooking recipe",
    "home improvement diy",
    "mental health wellness",
    "gaming review",
    "science explained",
    "education study tips",
    "relationship advice",
    "beauty skincare routine",
    "cars electric vehicles",
]


class DiscoveryEngine:
    """Discovers trending topics from multiple sources without user input.

    Sources:
        1. Google Trends trending/rising queries
        2. YouTube autocomplete expansion from broad categories
        3. Reddit rising posts across popular subreddits
        4. YouTube search trending videos
    """

    def __init__(
        self,
        google_trends: GoogleTrendsConnector,
        reddit: RedditConnector,
        yt_autocomplete: YouTubeAutocompleteConnector,
        yt_search: YouTubeSearchConnector,
    ) -> None:
        self.google_trends = google_trends
        self.reddit = reddit
        self.yt_autocomplete = yt_autocomplete
        self.yt_search = yt_search

    async def discover_topics(
        self, max_seeds: int = 40, deep: bool = False,
    ) -> list[DiscoverySource]:
        """Discover seed topics automatically from multiple sources.

        Args:
            max_seeds: Maximum number of unique seed topics to return.
            deep: If True, cast a wider net (more categories, more sources).

        Returns:
            Deduplicated list of DiscoverySource objects ranked by score.
        """
        logger.info("discovery_started", deep=deep, max_seeds=max_seeds)

        categories = _DISCOVERY_CATEGORIES if deep else _DISCOVERY_CATEGORIES[:10]

        # Gather signals from all sources concurrently
        sources: list[DiscoverySource] = []

        # 1. Google Trends rising queries
        gt_sources = await self._discover_from_google_trends(categories)
        sources.extend(gt_sources)

        # 2. YouTube autocomplete expansion
        ac_sources = await self._discover_from_autocomplete(categories)
        sources.extend(ac_sources)

        # 3. Reddit rising topics
        reddit_sources = await self._discover_from_reddit(categories)
        sources.extend(reddit_sources)

        # 4. YouTube search (trending content titles)
        yt_sources = await self._discover_from_youtube_search(categories[:8])
        sources.extend(yt_sources)

        # Deduplicate and rank by score
        seen: set[str] = set()
        unique: list[DiscoverySource] = []
        for src in sorted(sources, key=lambda s: s.score, reverse=True):
            topic_lower = src.topic.lower().strip()
            if topic_lower and topic_lower not in seen and len(topic_lower) > 2:
                seen.add(topic_lower)
                unique.append(src)

        seeds = unique[:max_seeds]

        logger.info(
            "discovery_completed",
            raw_signals=len(sources),
            unique_seeds=len(seeds),
        )
        return seeds

    # ── Source: Google Trends ──────────────────────────────────────────

    async def _discover_from_google_trends(
        self, categories: list[str],
    ) -> list[DiscoverySource]:
        """Extract rising queries from Google Trends for each category."""
        results: list[DiscoverySource] = []

        for category in categories:
            try:
                trend = await self.google_trends.get_trend(category)
                for query in trend.related_queries[:10]:
                    results.append(DiscoverySource(
                        topic=query,
                        source="google_trends",
                        score=trend.momentum_score,
                        metadata={"parent": category, "direction": trend.direction.value},
                    ))
            except Exception as e:
                logger.warning("gt_discovery_error", category=category, error=str(e))

        logger.info("gt_discovered", topics=len(results))
        return results

    # ── Source: YouTube Autocomplete ──────────────────────────────────

    async def _discover_from_autocomplete(
        self, categories: list[str],
    ) -> list[DiscoverySource]:
        """Expand categories via autocomplete to find high-demand queries."""
        results: list[DiscoverySource] = []

        for category in categories:
            try:
                ac_result = await self.yt_autocomplete.get_suggestions(category)
                for suggestion in ac_result.suggestions[:8]:
                    results.append(DiscoverySource(
                        topic=suggestion,
                        source="youtube_autocomplete",
                        score=60.0,  # Baseline score — present in autocomplete = decent demand
                        metadata={"parent": category},
                    ))
            except Exception as e:
                logger.warning("ac_discovery_error", category=category, error=str(e))

        logger.info("ac_discovered", topics=len(results))
        return results

    # ── Source: Reddit Rising ─────────────────────────────────────────

    async def _discover_from_reddit(
        self, categories: list[str],
    ) -> list[DiscoverySource]:
        """Find topics seeing discussion spikes on Reddit."""
        results: list[DiscoverySource] = []

        # Use a subset to avoid excessive requests
        for category in categories[:8]:
            try:
                signal = await self.reddit.get_signal(category)
                if signal.spike_detected or signal.post_count_7d > 5:
                    score = 70.0 if signal.spike_detected else 50.0
                    score += min(20.0, signal.avg_score * 0.1)
                    results.append(DiscoverySource(
                        topic=category,
                        source="reddit",
                        score=min(100.0, score),
                        metadata={
                            "posts_7d": signal.post_count_7d,
                            "spike": signal.spike_detected,
                            "subreddits": signal.subreddits[:5],
                        },
                    ))
            except Exception as e:
                logger.warning("reddit_discovery_error", category=category, error=str(e))

        logger.info("reddit_discovered", topics=len(results))
        return results

    # ── Source: YouTube Search (trending titles) ──────────────────────

    async def _discover_from_youtube_search(
        self, categories: list[str],
    ) -> list[DiscoverySource]:
        """Extract fresh topic phrases from recent YouTube video titles."""
        results: list[DiscoverySource] = []

        for category in categories[:6]:
            try:
                search_results = await self.yt_search.search(category, max_results=10)
                for vid in search_results:
                    title = vid.title.strip()
                    if title and len(title) > 5:
                        # Score higher if the video has good views
                        view_score = min(30.0, vid.view_count / 100_000)
                        results.append(DiscoverySource(
                            topic=title,
                            source="youtube_search",
                            score=40.0 + view_score,
                            metadata={
                                "video_id": vid.video_id,
                                "views": vid.view_count,
                                "channel": vid.channel_name,
                            },
                        ))
            except Exception as e:
                logger.warning("yt_discovery_error", category=category, error=str(e))

        logger.info("yt_discovered", topics=len(results))
        return results
