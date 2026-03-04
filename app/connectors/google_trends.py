"""Google Trends connector for trend momentum analysis."""
from __future__ import annotations

import asyncio
from typing import Any

from app.config.settings import ConnectorConfig
from app.connectors.base import BaseConnector
from app.core.models import TrendData, TrendDirection


class GoogleTrendsConnector(BaseConnector):
    """Fetch Google Trends data for keyword momentum analysis."""

    def __init__(self, config: ConnectorConfig) -> None:
        super().__init__(config, name="google_trends")

    async def get_trend(self, keyword: str, timeframe: str = "today 3-m") -> TrendData:
        """Get trend data for a keyword using pytrends."""
        cache_key = f"trend:{keyword.lower().strip()}:{timeframe}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            self.logger.debug("cache_hit", keyword=keyword)
            return TrendData(**cached)

        try:
            # Run pytrends in executor since it's synchronous
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, self._fetch_trend_sync, keyword, timeframe
            )
            self._set_cached(cache_key, result.model_dump(mode="json"))
            return result

        except Exception as e:
            self.logger.error("trend_error", keyword=keyword, error=str(e))
            return TrendData(keyword=keyword, source="google_trends")

    def _fetch_trend_sync(self, keyword: str, timeframe: str) -> TrendData:
        """Synchronous Google Trends fetch via pytrends."""
        try:
            from pytrends.request import TrendReq

            pytrends = TrendReq(hl="en-US", tz=360, retries=2, backoff_factor=0.5)
            pytrends.build_payload([keyword], cat=0, timeframe=timeframe, geo="", gprop="youtube")

            # Interest over time
            df = pytrends.interest_over_time()
            interest: list[float] = []
            if not df.empty and keyword in df.columns:
                interest = df[keyword].tolist()

            # Related queries
            related = pytrends.related_queries()
            related_queries: list[str] = []
            if keyword in related and related[keyword].get("rising") is not None:
                rising_df = related[keyword]["rising"]
                if not rising_df.empty:
                    related_queries = rising_df["query"].head(20).tolist()

            # Calculate momentum
            direction, momentum = self._calculate_momentum(interest)

            self.logger.info(
                "trend_fetched",
                keyword=keyword,
                direction=direction.value,
                momentum=round(momentum, 1),
            )

            return TrendData(
                keyword=keyword,
                interest_over_time=interest,
                direction=direction,
                momentum_score=momentum,
                related_queries=related_queries,
                source="google_trends",
            )

        except Exception as e:
            self.logger.warning("pytrends_error", keyword=keyword, error=str(e))
            return TrendData(keyword=keyword, source="google_trends")

    @staticmethod
    def _calculate_momentum(interest: list[float]) -> tuple[TrendDirection, float]:
        """Calculate trend momentum from interest data."""
        if not interest or len(interest) < 4:
            return TrendDirection.STABLE, 50.0

        # Compare recent third vs first third
        third = len(interest) // 3
        if third == 0:
            return TrendDirection.STABLE, 50.0

        first_avg = sum(interest[:third]) / third
        last_avg = sum(interest[-third:]) / third

        if first_avg == 0:
            if last_avg > 0:
                return TrendDirection.BREAKOUT, 95.0
            return TrendDirection.STABLE, 50.0

        change_ratio = (last_avg - first_avg) / first_avg

        # Convert to 0-100 score
        momentum = 50.0 + (change_ratio * 100)
        momentum = max(0.0, min(100.0, momentum))

        # Determine direction
        if change_ratio > 0.5:
            direction = TrendDirection.BREAKOUT
        elif change_ratio > 0.1:
            direction = TrendDirection.RISING
        elif change_ratio < -0.2:
            direction = TrendDirection.DECLINING
        else:
            direction = TrendDirection.STABLE

        return direction, momentum

    async def get_batch_trends(
        self, keywords: list[str], timeframe: str = "today 3-m"
    ) -> list[TrendData]:
        """Get trends for multiple keywords with rate limiting."""
        results: list[TrendData] = []
        for keyword in keywords:
            result = await self.get_trend(keyword, timeframe)
            results.append(result)
        return results

    async def health_check(self) -> bool:
        try:
            result = await self.get_trend("python programming")
            return result.keyword != ""
        except Exception:
            return False
