"""Viral Opportunity Detector — identifies high-opportunity niches.

Finds topics where **small channels** (< 50 k subs) are achieving
**outsized view counts** (> 500 k views) on videos younger than 60 days.
Repeated anomalies in a niche signal strong opportunity.
"""
from __future__ import annotations

import re

from app.connectors.youtube_search import YouTubeSearchConnector
from app.core.logging import get_logger
from app.core.models import (
    SearchResult,
    ViralOpportunity,
    ViralOpportunityResult,
)

logger = get_logger(__name__)

# Thresholds
_MAX_SUBSCRIBERS = 50_000
_MIN_VIEWS = 500_000
_MAX_AGE_DAYS = 60


class ViralOpportunityDetector:
    """Detect niches where small channels achieve viral view counts."""

    def __init__(self, yt_search: YouTubeSearchConnector) -> None:
        self.yt_search = yt_search

    async def analyze_niche(
        self,
        niche: str,
        keywords: list[str],
        max_results_per_keyword: int = 15,
    ) -> ViralOpportunityResult:
        """Analyze a niche for viral opportunities.

        Steps:
          1. Search YouTube for each keyword.
          2. Filter videos matching the anomaly criteria.
          3. Calculate per-video and aggregate scores.
        """
        all_results: list[SearchResult] = []
        seen_ids: set[str] = set()

        # Search with a few representative keywords to gather data
        search_keywords = [niche] + keywords[:4]
        search_keywords = list(dict.fromkeys(search_keywords))[:5]

        for kw in search_keywords:
            try:
                results = await self.yt_search.search(kw, max_results=max_results_per_keyword)
                for r in results:
                    if r.video_id and r.video_id not in seen_ids:
                        seen_ids.add(r.video_id)
                        all_results.append(r)
            except Exception as e:
                logger.warning("viral_search_error", keyword=kw, error=str(e))

        # Identify viral anomalies
        opportunities = self._detect_anomalies(all_results)

        # Calculate aggregate score
        if opportunities:
            avg_score = sum(o.opportunity_score for o in opportunities) / len(opportunities)
            # More anomalies = stronger signal (diminishing returns)
            anomaly_bonus = min(40.0, len(opportunities) * 10.0)
            viral_score = min(100.0, avg_score * 0.6 + anomaly_bonus)
        else:
            avg_score = 0.0
            viral_score = 0.0

        result = ViralOpportunityResult(
            niche=niche,
            opportunities=opportunities,
            avg_opportunity_score=round(avg_score, 1),
            anomaly_count=len(opportunities),
            viral_opportunity_score=round(viral_score, 1),
        )

        logger.info(
            "viral_opportunity_analyzed",
            niche=niche,
            anomalies=len(opportunities),
            score=result.viral_opportunity_score,
        )
        return result

    async def analyze_batch(
        self,
        niche_keywords: dict[str, list[str]],
    ) -> dict[str, ViralOpportunityResult]:
        """Analyze multiple niches for viral opportunities."""
        results: dict[str, ViralOpportunityResult] = {}
        for niche, keywords in niche_keywords.items():
            results[niche] = await self.analyze_niche(niche, keywords)
        return results

    def _detect_anomalies(
        self, results: list[SearchResult],
    ) -> list[ViralOpportunity]:
        """Filter search results for small-channel viral anomalies."""
        opportunities: list[ViralOpportunity] = []

        for video in results:
            subs = video.channel_subscribers
            views = video.view_count
            age_days = self._estimate_age_days(video.published_date)

            # Apply thresholds
            if subs > 0 and subs < _MAX_SUBSCRIBERS and views > _MIN_VIEWS:
                if age_days is not None and age_days <= _MAX_AGE_DAYS:
                    ratio = views / max(subs, 1)
                    score = self._calculate_opportunity_score(views, subs, age_days)

                    opportunities.append(ViralOpportunity(
                        video_title=video.title,
                        video_id=video.video_id,
                        channel_name=video.channel_name,
                        channel_subscribers=subs,
                        video_views=views,
                        video_age_days=age_days,
                        views_to_sub_ratio=round(ratio, 1),
                        opportunity_score=round(score, 1),
                    ))

            # Relaxed threshold: even modest views on tiny channels matter
            elif subs > 0 and subs < 10_000 and views > 100_000:
                if age_days is not None and age_days <= _MAX_AGE_DAYS:
                    ratio = views / max(subs, 1)
                    score = self._calculate_opportunity_score(views, subs, age_days) * 0.7
                    opportunities.append(ViralOpportunity(
                        video_title=video.title,
                        video_id=video.video_id,
                        channel_name=video.channel_name,
                        channel_subscribers=subs,
                        video_views=views,
                        video_age_days=age_days,
                        views_to_sub_ratio=round(ratio, 1),
                        opportunity_score=round(score, 1),
                    ))

        # Sort by opportunity score
        opportunities.sort(key=lambda o: o.opportunity_score, reverse=True)
        return opportunities[:20]  # Cap to top 20

    @staticmethod
    def _calculate_opportunity_score(
        views: int, subs: int, age_days: int,
    ) -> float:
        """Calculate a 0–100 opportunity score for a single video.

        Factors:
          - Views-to-subscriber ratio (higher = more anomalous)
          - Recency (newer = more relevant)
          - Absolute view count (higher = more validated)
        """
        ratio = views / max(subs, 1)

        # Ratio component: 10× is great, 100× is exceptional
        ratio_score = min(40.0, ratio * 0.4)

        # Recency: videos within 7 days score highest
        recency_score = max(0.0, 30.0 - (age_days * 0.5))

        # View volume: > 1M views is very strong
        volume_score = min(30.0, (views / 1_000_000) * 30.0)

        return min(100.0, ratio_score + recency_score + volume_score)

    @staticmethod
    def _estimate_age_days(published_text: str) -> int | None:
        """Heuristic: parse relative date strings like '2 weeks ago'.

        Returns estimated days, or None if unparseable.
        """
        if not published_text:
            return None

        text = published_text.lower().strip()

        # Try common patterns
        patterns: list[tuple[str, int]] = [
            (r"(\d+)\s*hour", 0),      # within a day
            (r"(\d+)\s*day", 1),
            (r"(\d+)\s*week", 7),
            (r"(\d+)\s*month", 30),
            (r"(\d+)\s*year", 365),
        ]

        for pattern, multiplier in patterns:
            match = re.search(pattern, text)
            if match:
                count = int(match.group(1))
                if multiplier == 0:
                    return 0  # Same day
                return count * multiplier

        # "Streamed X ago" variants
        if "yesterday" in text:
            return 1

        return None
