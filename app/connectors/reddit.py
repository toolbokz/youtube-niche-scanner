"""Reddit trend signal connector."""
from __future__ import annotations

import json
from typing import Any
from urllib.parse import quote_plus

from app.config.settings import ConnectorConfig
from app.connectors.base import BaseConnector
from app.core.models import RedditSignal


class RedditConnector(BaseConnector):
    """Fetch Reddit signals for trend detection using public JSON API."""

    def __init__(self, config: ConnectorConfig) -> None:
        super().__init__(config, name="reddit")

    async def get_signal(self, keyword: str) -> RedditSignal:
        """Get Reddit discussion metrics for a keyword."""
        cache_key = f"signal:{keyword.lower().strip()}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            self.logger.debug("cache_hit", keyword=keyword)
            return RedditSignal(**cached)

        try:
            signal = await self._fetch_reddit_data(keyword)
            self._set_cached(cache_key, signal.model_dump(mode="json"))
            return signal

        except Exception as e:
            self.logger.error("reddit_error", keyword=keyword, error=str(e))
            return RedditSignal(keyword=keyword)

    async def _fetch_reddit_data(self, keyword: str) -> RedditSignal:
        """Search Reddit for keyword mentions and calculate signal."""
        encoded = quote_plus(keyword)

        # Search recent posts (week)
        url_week = f"https://www.reddit.com/search.json?q={encoded}&sort=new&t=week&limit=100"
        # Search recent posts (day)
        url_day = f"https://www.reddit.com/search.json?q={encoded}&sort=new&t=day&limit=100"

        try:
            week_data = await self._fetch_json(url_week)
            await self._rate_limit()  # Extra rate limit for Reddit
            day_data = await self._fetch_json(url_day)
        except Exception as e:
            self.logger.warning("reddit_fetch_failed", keyword=keyword, error=str(e))
            return RedditSignal(keyword=keyword)

        week_posts = self._extract_posts(week_data)
        day_posts = self._extract_posts(day_data)

        # Extract unique subreddits
        subreddits = list(set(p.get("subreddit", "") for p in week_posts if p.get("subreddit")))

        # Calculate metrics
        avg_score = 0.0
        avg_comments = 0.0
        if week_posts:
            avg_score = sum(p.get("score", 0) for p in week_posts) / len(week_posts)
            avg_comments = sum(p.get("num_comments", 0) for p in week_posts) / len(week_posts)

        # Detect spike: if day posts > 20% of week posts, it's spiking
        spike_detected = len(day_posts) > max(1, len(week_posts) * 0.2) if week_posts else False

        signal = RedditSignal(
            keyword=keyword,
            subreddits=subreddits[:20],
            post_count_24h=len(day_posts),
            post_count_7d=len(week_posts),
            avg_score=round(avg_score, 1),
            avg_comments=round(avg_comments, 1),
            spike_detected=spike_detected,
        )

        self.logger.info(
            "reddit_signal",
            keyword=keyword,
            posts_7d=signal.post_count_7d,
            spike=signal.spike_detected,
        )

        return signal

    @staticmethod
    def _extract_posts(data: Any) -> list[dict[str, Any]]:
        """Extract post data from Reddit JSON response."""
        posts: list[dict[str, Any]] = []
        try:
            children = data.get("data", {}).get("children", [])
            for child in children:
                post = child.get("data", {})
                if post:
                    posts.append(post)
        except (AttributeError, TypeError):
            pass
        return posts

    async def get_batch_signals(self, keywords: list[str]) -> list[RedditSignal]:
        """Get Reddit signals for multiple keywords concurrently."""
        import asyncio
        tasks = [self.get_signal(kw) for kw in keywords]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [
            r for r in results
            if not isinstance(r, BaseException)
        ]

    async def health_check(self) -> bool:
        try:
            signal = await self.get_signal("technology")
            return signal.post_count_7d > 0
        except Exception:
            return False
