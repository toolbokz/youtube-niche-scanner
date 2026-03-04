"""Topic Velocity Engine — measures how quickly content volume is growing.

A topic with rapidly accelerating upload volume is a strong growth signal:
    Week 1: 10 uploads → Week 2: 30 uploads → Week 3: 80 uploads

The engine computes a Topic Velocity Score (0–100) that integrates into
the niche ranking formula.
"""
from __future__ import annotations

import re
from typing import Any

from app.connectors.youtube_search import YouTubeSearchConnector
from app.core.logging import get_logger
from app.core.models import (
    SearchResult,
    TopicVelocityResult,
    WeeklyUploadVolume,
)

logger = get_logger(__name__)


class TopicVelocityEngine:
    """Measure and score the growth rate of content uploads for a topic."""

    def __init__(self, yt_search: YouTubeSearchConnector) -> None:
        self.yt_search = yt_search

    async def analyze_niche(
        self,
        niche: str,
        keywords: list[str],
    ) -> TopicVelocityResult:
        """Analyze upload velocity for a niche over recent weeks.

        Steps:
          1. Search YouTube for niche keywords.
          2. Bucket results by approximate age (week buckets).
          3. Calculate upload growth rate and acceleration.
          4. Produce a velocity score.
        """
        all_results: list[SearchResult] = []
        seen_ids: set[str] = set()

        search_keywords = [niche] + keywords[:3]
        search_keywords = list(dict.fromkeys(search_keywords))[:4]

        for kw in search_keywords:
            try:
                results = await self.yt_search.search(kw, max_results=20)
                for r in results:
                    if r.video_id and r.video_id not in seen_ids:
                        seen_ids.add(r.video_id)
                        all_results.append(r)
            except Exception as e:
                logger.warning("velocity_search_error", keyword=kw, error=str(e))

        # Bucket into weekly volumes
        weekly = self._bucket_by_week(all_results)

        # Calculate growth rate
        growth_rate = self._calculate_growth_rate(weekly)
        acceleration = self._calculate_acceleration(weekly)
        velocity_score = self._compute_velocity_score(growth_rate, acceleration, weekly)

        result = TopicVelocityResult(
            niche=niche,
            weekly_volumes=weekly,
            growth_rate=round(growth_rate, 2),
            acceleration=round(acceleration, 2),
            velocity_score=round(velocity_score, 1),
        )

        logger.info(
            "topic_velocity_analyzed",
            niche=niche,
            growth_rate=result.growth_rate,
            velocity_score=result.velocity_score,
        )
        return result

    async def analyze_batch(
        self,
        niche_keywords: dict[str, list[str]],
    ) -> dict[str, TopicVelocityResult]:
        """Analyze velocity for multiple niches."""
        results: dict[str, TopicVelocityResult] = {}
        for niche, keywords in niche_keywords.items():
            results[niche] = await self.analyze_niche(niche, keywords)
        return results

    def _bucket_by_week(
        self, results: list[SearchResult],
    ) -> list[WeeklyUploadVolume]:
        """Group search results into weekly time buckets by published date.

        Week 0 = most recent, Week 1 = 1 week ago, etc.
        Uses heuristic parsing of YouTube's relative date strings.
        """
        # 5 week buckets (0 = this week … 4 = 4+ weeks ago)
        buckets: dict[int, int] = {i: 0 for i in range(5)}

        for video in results:
            age_days = self._parse_age_days(video.published_date)
            if age_days is None:
                continue

            week_index = min(age_days // 7, 4)
            buckets[week_index] = buckets.get(week_index, 0) + 1

        # Convert to model — oldest first
        volumes: list[WeeklyUploadVolume] = []
        for i in range(4, -1, -1):
            label = "This week" if i == 0 else f"{i} week{'s' if i > 1 else ''} ago"
            volumes.append(WeeklyUploadVolume(
                week_label=label,
                upload_count=buckets[i],
            ))

        return volumes

    @staticmethod
    def _calculate_growth_rate(weekly: list[WeeklyUploadVolume]) -> float:
        """Growth rate: ratio of most-recent week to oldest week.

        > 1.0 means volume is growing; > 2.0 means doubling.
        """
        if len(weekly) < 2:
            return 0.0

        oldest = weekly[0].upload_count   # Oldest bucket
        newest = weekly[-1].upload_count  # Most recent bucket

        if oldest == 0:
            return float(newest) if newest > 0 else 0.0

        return newest / oldest

    @staticmethod
    def _calculate_acceleration(weekly: list[WeeklyUploadVolume]) -> float:
        """Second derivative: is the growth itself accelerating?

        Positive acceleration = explosive trend.
        """
        counts = [w.upload_count for w in weekly]
        if len(counts) < 3:
            return 0.0

        # First derivatives (week-over-week deltas)
        deltas = [counts[i + 1] - counts[i] for i in range(len(counts) - 1)]

        # Second derivatives (acceleration)
        accels = [deltas[i + 1] - deltas[i] for i in range(len(deltas) - 1)]

        return sum(accels) / len(accels) if accels else 0.0

    @staticmethod
    def _compute_velocity_score(
        growth_rate: float,
        acceleration: float,
        weekly: list[WeeklyUploadVolume],
    ) -> float:
        """Convert raw metrics into a 0–100 Topic Velocity Score.

        Components:
          - Growth rate (40 %): 2× growth → ~40 pts
          - Acceleration (30 %): positive accel → up to 30 pts
          - Absolute recent volume (30 %): more uploads = more activity
        """
        # Growth component (capped at 40)
        if growth_rate <= 0:
            growth_component = 0.0
        else:
            growth_component = min(40.0, growth_rate * 20.0)

        # Acceleration component (capped at 30)
        accel_component = max(0.0, min(30.0, acceleration * 5.0))

        # Volume component: most-recent week absolute count (capped at 30)
        recent_volume = weekly[-1].upload_count if weekly else 0
        volume_component = min(30.0, recent_volume * 3.0)

        return min(100.0, growth_component + accel_component + volume_component)

    @staticmethod
    def _parse_age_days(published_text: str) -> int | None:
        """Heuristic: parse YouTube relative date strings."""
        if not published_text:
            return None

        text = published_text.lower().strip()
        patterns: list[tuple[str, int]] = [
            (r"(\d+)\s*hour", 0),
            (r"(\d+)\s*day", 1),
            (r"(\d+)\s*week", 7),
            (r"(\d+)\s*month", 30),
            (r"(\d+)\s*year", 365),
        ]

        for pattern, multiplier in patterns:
            match = re.search(pattern, text)
            if match:
                count = int(match.group(1))
                return 0 if multiplier == 0 else count * multiplier

        if "yesterday" in text:
            return 1

        return None
