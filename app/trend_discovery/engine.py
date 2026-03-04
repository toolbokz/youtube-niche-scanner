"""Trend Discovery Engine - detects rising topics across multiple signals."""
from __future__ import annotations

from typing import Any

from app.config import get_settings
from app.connectors.google_trends import GoogleTrendsConnector
from app.connectors.reddit import RedditConnector
from app.connectors.youtube_autocomplete import YouTubeAutocompleteConnector
from app.connectors.youtube_search import YouTubeSearchConnector
from app.core.logging import get_logger
from app.core.models import TrendData, TrendDirection, RedditSignal

logger = get_logger(__name__)


class TrendDiscoveryEngine:
    """Discovers emerging and high-demand YouTube topics using multiple signals."""

    def __init__(
        self,
        trends_connector: GoogleTrendsConnector,
        reddit_connector: RedditConnector,
        yt_autocomplete: YouTubeAutocompleteConnector,
        yt_search: YouTubeSearchConnector,
    ) -> None:
        self.trends = trends_connector
        self.reddit = reddit_connector
        self.yt_autocomplete = yt_autocomplete
        self.yt_search = yt_search

    async def analyze_keyword(self, keyword: str) -> dict[str, Any]:
        """Compute a comprehensive trend analysis for a single keyword."""
        # 1. Google Trends momentum
        trend_data = await self.trends.get_trend(keyword)

        # 2. Reddit signals
        reddit_signal = await self.reddit.get_signal(keyword)

        # 3. YouTube autocomplete expansion frequency (proxy for demand)
        autocomplete = await self.yt_autocomplete.get_suggestions(keyword)
        autocomplete_count = len(autocomplete.suggestions)

        # 4. YouTube recent upload velocity
        search_results = await self.yt_search.search(keyword, max_results=20)
        upload_velocity = self._estimate_upload_velocity(search_results)

        # 5. Calculate composite Trend Momentum Score
        momentum_score = self._calculate_trend_momentum(
            trend_data=trend_data,
            reddit_signal=reddit_signal,
            autocomplete_count=autocomplete_count,
            upload_velocity=upload_velocity,
        )

        result = {
            "keyword": keyword,
            "trend_momentum_score": round(momentum_score, 1),
            "google_trends_momentum": round(trend_data.momentum_score, 1),
            "google_trends_direction": trend_data.direction.value,
            "reddit_posts_7d": reddit_signal.post_count_7d,
            "reddit_spike": reddit_signal.spike_detected,
            "autocomplete_suggestions": autocomplete_count,
            "upload_velocity": round(upload_velocity, 2),
            "related_queries": trend_data.related_queries[:10],
            "autocomplete_keywords": autocomplete.suggestions[:10],
        }

        logger.info(
            "trend_analyzed",
            keyword=keyword,
            momentum=result["trend_momentum_score"],
        )

        return result

    async def discover_trends(self, seed_keywords: list[str]) -> list[dict[str, Any]]:
        """Analyze multiple keywords and return sorted by momentum."""
        results: list[dict[str, Any]] = []
        for keyword in seed_keywords:
            analysis = await self.analyze_keyword(keyword)
            results.append(analysis)

        # Sort by trend momentum score descending
        results.sort(key=lambda x: x["trend_momentum_score"], reverse=True)
        return results

    def _estimate_upload_velocity(self, results: list[Any]) -> float:
        """Estimate how many videos are being uploaded on this topic recently.

        Higher upload velocity means more competition but also more demand.
        """
        if not results:
            return 0.0

        # Use result count as a proxy
        # More results with recent videos = higher velocity
        total_videos = len(results)

        # Estimate based on count — a proper implementation would check dates
        return min(100.0, total_videos * 5.0)

    def _calculate_trend_momentum(
        self,
        trend_data: TrendData,
        reddit_signal: RedditSignal,
        autocomplete_count: int,
        upload_velocity: float,
    ) -> float:
        """Calculate composite Trend Momentum Score (0-100).

        Weights:
          - Google Trends momentum: 35%
          - Reddit signal: 20%
          - Autocomplete expansion: 20%
          - Upload velocity: 25%
        """
        # Google Trends component (already 0-100)
        gt_score = trend_data.momentum_score

        # Reddit component
        reddit_score = 0.0
        if reddit_signal.spike_detected:
            reddit_score += 40.0
        reddit_score += min(30.0, reddit_signal.post_count_7d * 0.3)
        reddit_score += min(20.0, reddit_signal.avg_score * 0.1)
        reddit_score += min(10.0, reddit_signal.avg_comments * 0.2)
        reddit_score = min(100.0, reddit_score)

        # Autocomplete component (more suggestions = more demand)
        ac_score = min(100.0, autocomplete_count * 8.0)

        # Upload velocity component
        uv_score = min(100.0, upload_velocity)

        # Weighted composite
        composite = (
            gt_score * 0.35
            + reddit_score * 0.20
            + ac_score * 0.20
            + uv_score * 0.25
        )

        return max(0.0, min(100.0, composite))
