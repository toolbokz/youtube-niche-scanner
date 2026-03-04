"""YouTube search result scraper for competition data."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any
from urllib.parse import quote_plus

from bs4 import BeautifulSoup
import json

from app.config.settings import ConnectorConfig
from app.connectors.base import BaseConnector
from app.core.models import SearchResult


class YouTubeSearchConnector(BaseConnector):
    """Scrape YouTube search results for competition analysis."""

    def __init__(self, config: ConnectorConfig) -> None:
        super().__init__(config, name="youtube_search")

    async def search(self, query: str, max_results: int = 20) -> list[SearchResult]:
        """Search YouTube and parse results."""
        cache_key = f"search:{query.lower().strip()}:{max_results}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            self.logger.debug("cache_hit", query=query)
            return [SearchResult(**r) for r in cached]

        try:
            url = f"https://www.youtube.com/results?search_query={quote_plus(query)}"
            raw_html = await self._fetch(url)
            results = self._parse_search_results(raw_html, max_results)

            self._set_cached(cache_key, [r.model_dump(mode="json") for r in results])
            self.logger.info("search_completed", query=query, results=len(results))
            return results

        except Exception as e:
            self.logger.error("search_error", query=query, error=str(e))
            return []

    def _parse_search_results(self, html: str, max_results: int) -> list[SearchResult]:
        """Parse YouTube search page HTML for video data."""
        results: list[SearchResult] = []

        try:
            # Extract ytInitialData JSON from HTML
            match = re.search(r"var ytInitialData = ({.*?});</script>", html, re.DOTALL)
            if not match:
                match = re.search(r"ytInitialData\s*=\s*({.*?});\s*</script>", html, re.DOTALL)

            if not match:
                self.logger.warning("no_initial_data_found")
                return results

            data = json.loads(match.group(1))
            contents = (
                data.get("contents", {})
                .get("twoColumnSearchResultsRenderer", {})
                .get("primaryContents", {})
                .get("sectionListRenderer", {})
                .get("contents", [])
            )

            for section in contents:
                items = (
                    section.get("itemSectionRenderer", {})
                    .get("contents", [])
                )
                for item in items:
                    video = item.get("videoRenderer")
                    if not video:
                        continue

                    result = self._parse_video_renderer(video)
                    if result:
                        results.append(result)
                    if len(results) >= max_results:
                        break
                if len(results) >= max_results:
                    break

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            self.logger.warning("parse_error", error=str(e))

        return results

    def _parse_video_renderer(self, video: dict[str, Any]) -> SearchResult | None:
        """Parse a single video renderer object."""
        try:
            title = ""
            title_runs = video.get("title", {}).get("runs", [])
            if title_runs:
                title = title_runs[0].get("text", "")

            channel_name = ""
            channel_runs = video.get("ownerText", {}).get("runs", [])
            if channel_runs:
                channel_name = channel_runs[0].get("text", "")

            video_id = video.get("videoId", "")

            # Parse view count
            view_count = 0
            view_text = video.get("viewCountText", {}).get("simpleText", "")
            if view_text:
                view_count = self._parse_count(view_text)

            # Parse published date
            published_text = video.get("publishedTimeText", {}).get("simpleText", "")

            # Parse duration
            duration_text = video.get("lengthText", {}).get("simpleText", "")
            duration_seconds = self._parse_duration(duration_text)

            return SearchResult(
                title=title,
                channel_name=channel_name,
                view_count=view_count,
                video_id=video_id,
                duration_seconds=duration_seconds,
                published_date=published_text,
            )
        except Exception:
            return None

    @staticmethod
    def _parse_count(text: str) -> int:
        """Parse view/subscriber count text like '1.2M views'."""
        text = text.lower().replace(",", "").replace(" views", "").replace(" view", "").strip()
        multipliers = {"k": 1_000, "m": 1_000_000, "b": 1_000_000_000}
        for suffix, mult in multipliers.items():
            if text.endswith(suffix):
                try:
                    return int(float(text[:-1]) * mult)
                except ValueError:
                    return 0
        try:
            return int(text)
        except ValueError:
            return 0

    @staticmethod
    def _parse_duration(text: str) -> int:
        """Parse duration like '12:34' or '1:23:45' to seconds."""
        if not text:
            return 0
        parts = text.split(":")
        try:
            if len(parts) == 3:
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            elif len(parts) == 2:
                return int(parts[0]) * 60 + int(parts[1])
            return int(parts[0])
        except ValueError:
            return 0

    async def health_check(self) -> bool:
        try:
            results = await self.search("python tutorial", max_results=3)
            return len(results) > 0
        except Exception:
            return False
