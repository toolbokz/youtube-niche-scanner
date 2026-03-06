"""Video Factory — YouTube Video Downloader.

Downloads source videos from YouTube using yt-dlp for use in
compilation video assembly.  Downloads are stored per-job under
``data/video_factory/{job_id}/source_videos/``.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
from dataclasses import dataclass, field
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)

# Maximum allowed source video duration to prevent massive downloads (30 min)
_MAX_SOURCE_DURATION_S = 30 * 60

# Default maximum resolution height
_DEFAULT_MAX_HEIGHT = 1080


@dataclass
class DownloadedVideo:
    """Metadata for a single downloaded source video."""

    video_id: str
    title: str
    file_path: str
    duration_seconds: float
    width: int = 0
    height: int = 0
    fps: float = 0.0
    file_size_mb: float = 0.0
    format_note: str = ""


@dataclass
class DownloadResult:
    """Result of downloading all source videos for a compilation job."""

    downloaded: list[DownloadedVideo] = field(default_factory=list)
    failed: list[dict[str, str]] = field(default_factory=list)
    source_dir: str = ""
    total_size_mb: float = 0.0


def _parse_timestamp(ts: str) -> float:
    """Convert a timestamp string like '2:12' or '1:05:30' to seconds."""
    parts = ts.strip().split(":")
    parts = [float(p) for p in parts]
    if len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    if len(parts) == 2:
        return parts[0] * 60 + parts[1]
    return parts[0]


class YouTubeDownloader:
    """Download YouTube videos using yt-dlp.

    Parameters
    ----------
    max_height : int
        Maximum video height (e.g. 1080 for 1080p).
    output_base : str
        Root directory for downloaded files.
    """

    def __init__(
        self,
        max_height: int = _DEFAULT_MAX_HEIGHT,
        output_base: str = "data/video_factory",
    ) -> None:
        self.max_height = max_height
        self.output_base = output_base

    async def download_source_videos(
        self,
        source_videos: list[dict[str, Any]],
        job_id: str,
    ) -> DownloadResult:
        """Download all source videos required for a compilation.

        Parameters
        ----------
        source_videos : list[dict]
            Each dict must have at minimum ``video_id`` (or ``url``).
            Accepted keys mirror :class:`CompilationSourceVideo`.
        job_id : str
            The job ID — used for directory namespacing.

        Returns
        -------
        DownloadResult
            Contains paths to downloaded files and any failures.

        Raises
        ------
        RuntimeError
            If **no** source videos could be downloaded.
        """
        source_dir = os.path.join(self.output_base, job_id, "source_videos")
        os.makedirs(source_dir, exist_ok=True)

        result = DownloadResult(source_dir=source_dir)

        # Download videos in parallel (bounded to 3 concurrent)
        sem = asyncio.Semaphore(3)

        async def _bounded_download(src: dict[str, Any]) -> DownloadedVideo | dict[str, str]:
            video_id = src.get("video_id", "")
            url = src.get("url", "")
            if not url and video_id:
                url = f"https://www.youtube.com/watch?v={video_id}"
            if not url:
                return {"video_id": video_id, "error": "No URL or video_id"}

            async with sem:
                try:
                    dl = await self._download_single(
                        url=url,
                        video_id=video_id,
                        output_dir=source_dir,
                    )
                    logger.info(
                        "source_video_downloaded",
                        video_id=dl.video_id,
                        size_mb=dl.file_size_mb,
                        duration=dl.duration_seconds,
                    )
                    return dl
                except Exception as exc:
                    logger.warning("source_video_download_failed", video_id=video_id, error=str(exc))
                    return {"video_id": video_id, "url": url, "error": str(exc)}

        outcomes = await asyncio.gather(*[_bounded_download(src) for src in source_videos])

        for outcome in outcomes:
            if isinstance(outcome, DownloadedVideo):
                result.downloaded.append(outcome)
                result.total_size_mb += outcome.file_size_mb
            else:
                result.failed.append(outcome)

        if not result.downloaded:
            raise RuntimeError(
                f"Failed to download any source videos. "
                f"Attempted {len(source_videos)}, all failed: "
                f"{json.dumps(result.failed, indent=2)}"
            )

        logger.info(
            "source_videos_download_complete",
            downloaded=len(result.downloaded),
            failed=len(result.failed),
            total_size_mb=round(result.total_size_mb, 2),
        )
        return result

    async def _download_single(
        self,
        url: str,
        video_id: str,
        output_dir: str,
    ) -> DownloadedVideo:
        """Download a single video via yt-dlp subprocess.

        Uses yt-dlp CLI to download the best available video+audio
        up to ``self.max_height`` resolution.
        """
        # Determine output template
        safe_id = re.sub(r"[^a-zA-Z0-9_-]", "_", video_id) if video_id else "video"
        output_template = os.path.join(output_dir, f"{safe_id}.%(ext)s")

        # Build yt-dlp command
        # Format: best video up to max_height merged with best audio
        format_spec = (
            f"bestvideo[height<={self.max_height}]+bestaudio/best[height<={self.max_height}]/best"
        )

        cmd = [
            "yt-dlp",
            "--no-playlist",
            "--no-check-certificates",
            "--merge-output-format", "mp4",
            "-f", format_spec,
            "-o", output_template,
            "--write-info-json",
            "--no-overwrites",
            "--socket-timeout", "30",
            "--retries", "3",
            url,
        ]

        logger.debug("yt_dlp_command", cmd=" ".join(cmd))

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(), timeout=600.0,  # 10 min per video download
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            raise RuntimeError(f"yt-dlp download timed out after 600s for {video_id}")

        if proc.returncode != 0:
            stderr_text = stderr_bytes.decode(errors="replace")[-500:]
            raise RuntimeError(f"yt-dlp failed (rc={proc.returncode}): {stderr_text}")

        # Find the downloaded file
        downloaded_path = self._find_downloaded_file(output_dir, safe_id)
        if not downloaded_path:
            raise RuntimeError(f"yt-dlp completed but output file not found for {video_id}")

        # Read info JSON for metadata
        info = self._read_info_json(output_dir, safe_id)

        file_size = os.path.getsize(downloaded_path) / (1024 * 1024)

        return DownloadedVideo(
            video_id=video_id or info.get("id", safe_id),
            title=info.get("title", ""),
            file_path=os.path.abspath(downloaded_path),
            duration_seconds=float(info.get("duration", 0)),
            width=int(info.get("width", 0)),
            height=int(info.get("height", 0)),
            fps=float(info.get("fps", 0)),
            file_size_mb=round(file_size, 2),
            format_note=info.get("format_note", ""),
        )

    @staticmethod
    def _find_downloaded_file(output_dir: str, prefix: str) -> str | None:
        """Find the MP4 file matching the given prefix in the output dir."""
        for f in os.listdir(output_dir):
            if f.startswith(prefix) and f.endswith(".mp4"):
                return os.path.join(output_dir, f)
        # Fallback: any mp4 with the prefix
        for f in os.listdir(output_dir):
            if prefix in f and not f.endswith(".json"):
                return os.path.join(output_dir, f)
        return None

    @staticmethod
    def _read_info_json(output_dir: str, prefix: str) -> dict[str, Any]:
        """Read the yt-dlp info JSON for the downloaded video."""
        for f in os.listdir(output_dir):
            if f.startswith(prefix) and f.endswith(".info.json"):
                try:
                    with open(os.path.join(output_dir, f)) as fh:
                        return json.load(fh)
                except Exception:
                    return {}
        return {}


def _build_video_id_lookup(downloaded: list[DownloadedVideo]) -> dict[str, DownloadedVideo]:
    """Build a video_id → DownloadedVideo lookup map."""
    return {dv.video_id: dv for dv in downloaded}
