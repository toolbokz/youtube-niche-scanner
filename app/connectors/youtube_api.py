"""YouTube Data API v3 connector (optional, requires API key)."""
from __future__ import annotations

from typing import Any

from app.config.settings import ConnectorConfig
from app.connectors.base import BaseConnector
from app.core.models import SearchResult


YT_API_BASE = "https://www.googleapis.com/youtube/v3"


class YouTubeDataAPIConnector(BaseConnector):
    """Optional YouTube Data API v3 connector for enriched data."""

    def __init__(self, config: ConnectorConfig) -> None:
        super().__init__(config, name="youtube_data_api")
        self.api_key = config.api_key

    async def search_videos(
        self, query: str, max_results: int = 20, order: str = "relevance"
    ) -> list[SearchResult]:
        """Search videos via YouTube Data API."""
        if not self.api_key:
            self.logger.warning("no_api_key_configured")
            return []

        cache_key = f"api_search:{query}:{max_results}:{order}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return [SearchResult(**r) for r in cached]

        try:
            params = {
                "part": "snippet",
                "q": query,
                "type": "video",
                "maxResults": min(max_results, 50),
                "order": order,
                "key": self.api_key,
            }
            data = await self._fetch_json(f"{YT_API_BASE}/search", params=params)
            video_ids = [item["id"]["videoId"] for item in data.get("items", []) if "videoId" in item.get("id", {})]

            if not video_ids:
                return []

            # Fetch video statistics
            results = await self._get_video_details(video_ids)
            self._set_cached(cache_key, [r.model_dump(mode="json") for r in results])
            return results

        except Exception as e:
            self.logger.error("api_search_error", query=query, error=str(e))
            return []

    async def _get_video_details(self, video_ids: list[str]) -> list[SearchResult]:
        """Fetch detailed video info including statistics."""
        results: list[SearchResult] = []
        params = {
            "part": "snippet,statistics,contentDetails",
            "id": ",".join(video_ids),
            "key": self.api_key,
        }

        try:
            data = await self._fetch_json(f"{YT_API_BASE}/videos", params=params)
            for item in data.get("items", []):
                snippet = item.get("snippet", {})
                stats = item.get("statistics", {})

                results.append(SearchResult(
                    title=snippet.get("title", ""),
                    channel_name=snippet.get("channelTitle", ""),
                    view_count=int(stats.get("viewCount", 0)),
                    like_count=int(stats.get("likeCount", 0)),
                    comment_count=int(stats.get("commentCount", 0)),
                    video_id=item.get("id", ""),
                    published_at=snippet.get("publishedAt"),
                ))
        except Exception as e:
            self.logger.error("video_details_error", error=str(e))

        return results

    async def get_channel_stats(self, channel_id: str) -> dict[str, Any]:
        """Fetch channel statistics."""
        if not self.api_key:
            return {}

        cache_key = f"channel:{channel_id}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        try:
            params = {
                "part": "statistics,snippet",
                "id": channel_id,
                "key": self.api_key,
            }
            data = await self._fetch_json(f"{YT_API_BASE}/channels", params=params)
            items = data.get("items", [])
            if items:
                result = {
                    "subscriber_count": int(items[0].get("statistics", {}).get("subscriberCount", 0)),
                    "video_count": int(items[0].get("statistics", {}).get("videoCount", 0)),
                    "view_count": int(items[0].get("statistics", {}).get("viewCount", 0)),
                    "title": items[0].get("snippet", {}).get("title", ""),
                }
                self._set_cached(cache_key, result)
                return result
        except Exception as e:
            self.logger.error("channel_stats_error", error=str(e))

        return {}

    async def health_check(self) -> bool:
        if not self.api_key:
            return False
        try:
            results = await self.search_videos("test", max_results=1)
            return len(results) > 0
        except Exception:
            return False
