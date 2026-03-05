"""Video Factory — Segment Extractor.

Extracts clip segments from downloaded source videos using ffmpeg.
Each segment is cut precisely at the timestamps recommended by the
Compilation Intelligence engine and saved as an individual MP4 file.
"""
from __future__ import annotations

import asyncio
import os
import re
from dataclasses import dataclass, field
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)

# Minimum acceptable clip duration in seconds
_MIN_CLIP_DURATION = 1.0

# Maximum single clip duration in seconds (5 minutes)
_MAX_CLIP_DURATION = 5 * 60


@dataclass
class ExtractedClip:
    """A single extracted clip from a source video."""

    clip_id: str
    source_video_id: str
    source_file_path: str
    clip_file_path: str
    start_seconds: float
    end_seconds: float
    duration_seconds: float
    segment_type: str = ""
    energy_level: str = "medium"
    position: int = 0
    width: int = 0
    height: int = 0
    file_size_mb: float = 0.0
    is_valid: bool = True
    validation_error: str = ""


@dataclass
class ExtractionResult:
    """Result of extracting all segments for a compilation job."""

    clips: list[ExtractedClip] = field(default_factory=list)
    failed: list[dict[str, str]] = field(default_factory=list)
    clips_dir: str = ""
    total_duration_seconds: float = 0.0
    total_size_mb: float = 0.0


def parse_timestamp(ts: str) -> float:
    """Convert a timestamp string like '2:12' or '1:05:30' to seconds.

    Also accepts raw numeric strings (e.g. '132.5').
    """
    ts = ts.strip()
    # Try raw float first
    if re.match(r"^\d+(\.\d+)?$", ts):
        return float(ts)
    parts = ts.split(":")
    parts = [float(p) for p in parts]
    if len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    if len(parts) == 2:
        return parts[0] * 60 + parts[1]
    return parts[0]


class SegmentExtractor:
    """Extract clips from downloaded source videos using ffmpeg.

    Parameters
    ----------
    output_base : str
        Root directory for job output.
    reencode : bool
        If True, re-encode clips to ensure consistent codec/format.
        If False, use stream copy for speed (may have imprecise cuts).
    target_resolution : str
        Target resolution e.g. '1920x1080'. Clips will be scaled/padded
        to match this resolution for uniform concatenation.
    """

    def __init__(
        self,
        output_base: str = "data/video_factory",
        reencode: bool = True,
        target_resolution: str = "1920x1080",
    ) -> None:
        self.output_base = output_base
        self.reencode = reencode
        self.target_resolution = target_resolution

    async def extract_segments(
        self,
        segments: list[dict[str, Any]],
        source_lookup: dict[str, str],
        job_id: str,
    ) -> ExtractionResult:
        """Extract all recommended segments from their source videos.

        Parameters
        ----------
        segments : list[dict]
            Each dict should have ``source_video_id``, ``timestamp_start``,
            ``timestamp_end``, and optionally ``segment_type``, ``energy_level``,
            ``position``.
        source_lookup : dict[str, str]
            Mapping of ``video_id`` → local file path for downloaded videos.
        job_id : str
            Job ID for directory namespacing.

        Returns
        -------
        ExtractionResult

        Raises
        ------
        RuntimeError
            If no clips could be extracted.
        """
        clips_dir = os.path.join(self.output_base, job_id, "clips")
        os.makedirs(clips_dir, exist_ok=True)

        result = ExtractionResult(clips_dir=clips_dir)

        for idx, seg in enumerate(segments):
            video_id = seg.get("source_video_id", "")
            source_path = source_lookup.get(video_id)

            if not source_path or not os.path.exists(source_path):
                result.failed.append({
                    "source_video_id": video_id,
                    "error": f"Source video file not found: {source_path}",
                })
                continue

            try:
                ts_start = parse_timestamp(str(seg.get("timestamp_start", "0:00")))
                ts_end = parse_timestamp(str(seg.get("timestamp_end", "0:30")))
            except (ValueError, IndexError) as exc:
                result.failed.append({
                    "source_video_id": video_id,
                    "error": f"Invalid timestamps: {exc}",
                })
                continue

            duration = ts_end - ts_start
            if duration < _MIN_CLIP_DURATION:
                result.failed.append({
                    "source_video_id": video_id,
                    "error": f"Clip too short ({duration:.1f}s < {_MIN_CLIP_DURATION}s)",
                })
                continue
            if duration > _MAX_CLIP_DURATION:
                logger.warning(
                    "clip_duration_capped",
                    video_id=video_id,
                    original=duration,
                    capped=_MAX_CLIP_DURATION,
                )
                ts_end = ts_start + _MAX_CLIP_DURATION
                duration = _MAX_CLIP_DURATION

            clip_id = f"clip_{idx:03d}"
            clip_path = os.path.join(clips_dir, f"{clip_id}.mp4")

            try:
                clip = await self._extract_single(
                    source_path=source_path,
                    output_path=clip_path,
                    start_seconds=ts_start,
                    end_seconds=ts_end,
                    clip_id=clip_id,
                    video_id=video_id,
                    segment_type=seg.get("segment_type", ""),
                    energy_level=seg.get("energy_level", "medium"),
                    position=seg.get("position", idx),
                )
                result.clips.append(clip)
                result.total_duration_seconds += clip.duration_seconds
                result.total_size_mb += clip.file_size_mb

                logger.info(
                    "clip_extracted",
                    clip_id=clip_id,
                    video_id=video_id,
                    duration=clip.duration_seconds,
                    start=ts_start,
                    end=ts_end,
                )
            except Exception as exc:
                result.failed.append({
                    "source_video_id": video_id,
                    "clip_id": clip_id,
                    "error": str(exc),
                })
                logger.warning(
                    "clip_extraction_failed",
                    clip_id=clip_id,
                    video_id=video_id,
                    error=str(exc),
                )

        if not result.clips:
            raise RuntimeError(
                f"Failed to extract any clips. "
                f"Attempted {len(segments)}, all failed: {result.failed}"
            )

        logger.info(
            "segment_extraction_complete",
            extracted=len(result.clips),
            failed=len(result.failed),
            total_duration=round(result.total_duration_seconds, 2),
            total_size_mb=round(result.total_size_mb, 2),
        )
        return result

    async def _extract_single(
        self,
        source_path: str,
        output_path: str,
        start_seconds: float,
        end_seconds: float,
        clip_id: str,
        video_id: str,
        segment_type: str = "",
        energy_level: str = "medium",
        position: int = 0,
    ) -> ExtractedClip:
        """Extract a single clip segment using ffmpeg.

        The clip is scaled/padded to the target resolution so all clips
        have uniform dimensions for concatenation.
        """
        width, height = self.target_resolution.split("x")
        duration = end_seconds - start_seconds

        if self.reencode:
            # Re-encode for precise cuts and uniform codec/resolution
            # Scale to fit within target while preserving aspect ratio, then pad
            scale_filter = (
                f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
                f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black,"
                f"setsar=1"
            )

            cmd = [
                "ffmpeg", "-y",
                "-ss", f"{start_seconds:.3f}",
                "-i", source_path,
                "-t", f"{duration:.3f}",
                "-vf", scale_filter,
                "-c:v", "libx264", "-preset", "fast",
                "-crf", "20",
                "-c:a", "aac", "-b:a", "192k",
                "-pix_fmt", "yuv420p",
                "-movflags", "+faststart",
                "-avoid_negative_ts", "make_zero",
                output_path,
            ]
        else:
            # Stream copy for speed (seeking may be less precise)
            cmd = [
                "ffmpeg", "-y",
                "-ss", f"{start_seconds:.3f}",
                "-i", source_path,
                "-t", f"{duration:.3f}",
                "-c", "copy",
                "-avoid_negative_ts", "make_zero",
                output_path,
            ]

        logger.debug("ffmpeg_extract_cmd", cmd=" ".join(cmd))

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr_bytes = await proc.communicate()

        if proc.returncode != 0:
            stderr_text = stderr_bytes.decode(errors="replace")[-500:]
            raise RuntimeError(f"ffmpeg extraction failed (rc={proc.returncode}): {stderr_text}")

        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            raise RuntimeError(f"ffmpeg produced empty or missing output: {output_path}")

        file_size = os.path.getsize(output_path) / (1024 * 1024)

        # Probe the output clip for metadata
        probe_data = await self._probe_clip(output_path)

        return ExtractedClip(
            clip_id=clip_id,
            source_video_id=video_id,
            source_file_path=source_path,
            clip_file_path=os.path.abspath(output_path),
            start_seconds=start_seconds,
            end_seconds=end_seconds,
            duration_seconds=round(duration, 3),
            segment_type=segment_type,
            energy_level=energy_level,
            position=position,
            width=probe_data.get("width", int(width)),
            height=probe_data.get("height", int(height)),
            file_size_mb=round(file_size, 2),
        )

    @staticmethod
    async def _probe_clip(file_path: str) -> dict[str, Any]:
        """Get video stream info using ffprobe."""
        cmd = [
            "ffprobe", "-v", "quiet",
            "-print_format", "json",
            "-show_streams",
            "-select_streams", "v:0",
            file_path,
        ]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            stdout_bytes, _ = await proc.communicate()
            if proc.returncode == 0:
                import json
                data = json.loads(stdout_bytes.decode())
                streams = data.get("streams", [])
                if streams:
                    s = streams[0]
                    return {
                        "width": int(s.get("width", 0)),
                        "height": int(s.get("height", 0)),
                        "duration": float(s.get("duration", 0)),
                    }
        except Exception:
            pass
        return {}
