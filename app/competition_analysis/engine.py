"""Competition Analysis Engine - evaluates niche saturation."""
from __future__ import annotations

import statistics
from datetime import datetime
from typing import Any

from app.connectors.youtube_search import YouTubeSearchConnector
from app.core.logging import get_logger
from app.core.models import CompetitionMetrics, SearchResult

logger = get_logger(__name__)


class CompetitionAnalysisEngine:
    """Analyze competition saturation for each niche."""

    def __init__(self, yt_search: YouTubeSearchConnector, sample_size: int = 20) -> None:
        self.yt_search = yt_search
        self.sample_size = sample_size

    async def analyze_niche(self, niche_name: str, keywords: list[str]) -> CompetitionMetrics:
        """Analyze competition for a niche using its keywords concurrently."""
        import asyncio
        sample_keywords = keywords[:5]

        # Search all keywords in parallel
        tasks = [
            self.yt_search.search(keyword, max_results=self.sample_size)
            for keyword in sample_keywords
        ]
        results_raw = await asyncio.gather(*tasks, return_exceptions=True)

        all_results: list[SearchResult] = []
        for r in results_raw:
            if not isinstance(r, BaseException):
                all_results.extend(r)

        if not all_results:
            return CompetitionMetrics(niche=niche_name, competition_score=50.0)

        # Calculate metrics
        metrics = self._compute_metrics(niche_name, all_results)

        logger.info(
            "competition_analyzed",
            niche=niche_name,
            score=round(metrics.competition_score, 1),
            videos_analyzed=len(all_results),
        )

        return metrics

    def _compute_metrics(
        self, niche_name: str, results: list[SearchResult]
    ) -> CompetitionMetrics:
        """Compute competition metrics from search results."""
        views = [r.view_count for r in results if r.view_count and r.view_count > 0]
        subscribers = [
            r.channel_subscribers
            for r in results
            if r.channel_subscribers and r.channel_subscribers > 0
        ]
        durations = [r.duration_seconds for r in results if r.duration_seconds and r.duration_seconds > 0]

        # Average views
        avg_views = statistics.mean(views) if views else 0.0
        median_views = statistics.median(views) if views else 0.0

        # Average subscriber count
        avg_subs = statistics.mean(subscribers) if subscribers else 0.0

        # Content saturation (proxy: how many unique channels)
        unique_channels = len(set(r.channel_name for r in results if r.channel_name))
        saturation = min(100.0, unique_channels * 5.0)

        # Production quality proxy (based on video duration)
        avg_duration = statistics.mean(durations) if durations else 0.0
        production_quality = self._estimate_production_quality(avg_duration, avg_views)

        # Competition Score calculation
        # Lower is better for new creators
        # High views + high subs + high saturation = high competition
        competition_score = self._calculate_competition_score(
            avg_views=avg_views,
            avg_subs=avg_subs,
            saturation=saturation,
            production_quality=production_quality,
        )

        return CompetitionMetrics(
            niche=niche_name,
            avg_views_top20=round(avg_views, 0),
            median_views_top20=round(median_views, 0),
            avg_subscriber_count=round(avg_subs, 0),
            upload_frequency_per_week=0.0,  # Requires time series analysis
            content_saturation=round(saturation, 1),
            avg_video_age_days=0.0,  # Requires date parsing
            production_quality_proxy=round(production_quality, 1),
            competition_score=round(competition_score, 1),
        )

    @staticmethod
    def _estimate_production_quality(avg_duration: float, avg_views: float) -> float:
        """Estimate production quality from duration and views."""
        # Longer videos with more views suggest higher production value
        duration_score = min(50.0, avg_duration / 60.0 * 5.0)  # Up to 50 for 10+ min
        views_score = min(50.0, (avg_views / 100_000) * 50.0)  # Up to 50 for 100k+ avg
        return min(100.0, duration_score + views_score)

    @staticmethod
    def _calculate_competition_score(
        avg_views: float,
        avg_subs: float,
        saturation: float,
        production_quality: float,
    ) -> float:
        """Calculate competition score 0-100 (higher = more competitive).

        For niche ranking, we INVERT this so low competition = high opportunity.
        """
        # Normalize each factor to 0-100
        views_score = min(100.0, (avg_views / 500_000) * 100.0)
        subs_score = min(100.0, (avg_subs / 1_000_000) * 100.0)

        # Weighted combination
        score = (
            views_score * 0.30
            + subs_score * 0.25
            + saturation * 0.25
            + production_quality * 0.20
        )

        return max(0.0, min(100.0, score))

    async def analyze_batch(
        self, niches: dict[str, list[str]]
    ) -> dict[str, CompetitionMetrics]:
        """Analyze competition for multiple niches."""
        results: dict[str, CompetitionMetrics] = {}
        for niche_name, keywords in niches.items():
            metrics = await self.analyze_niche(niche_name, keywords)
            results[niche_name] = metrics
        return results
