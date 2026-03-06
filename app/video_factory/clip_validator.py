"""Video Factory — Clip Validator.

Validates extracted video clips to ensure they are usable in the
final compilation.  Checks include: file existence, minimum duration,
video stream presence, audio stream presence, and resolution conformity.
"""
from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)

# Minimum clip duration to be considered valid (seconds)
_MIN_DURATION = 0.5

# Minimum file size in bytes (a valid clip must be > 10 KB)
_MIN_FILE_SIZE = 10 * 1024


@dataclass
class ClipValidation:
    """Validation result for a single clip."""

    clip_id: str
    file_path: str
    is_valid: bool = True
    has_video: bool = False
    has_audio: bool = False
    duration_seconds: float = 0.0
    width: int = 0
    height: int = 0
    codec: str = ""
    file_size_bytes: int = 0
    errors: list[str] | None = None

    def __post_init__(self) -> None:
        if self.errors is None:
            self.errors = []


class ClipValidator:
    """Validate extracted clips before assembly.

    Parameters
    ----------
    min_duration : float
        Minimum acceptable clip duration.
    require_audio : bool
        Whether clips must have an audio track.
    target_resolution : str
        Expected resolution (e.g. '1920x1080'). Clips that don't
        match trigger a warning but are still considered valid.
    """

    def __init__(
        self,
        min_duration: float = _MIN_DURATION,
        require_audio: bool = False,
        target_resolution: str = "1920x1080",
    ) -> None:
        self.min_duration = min_duration
        self.require_audio = require_audio
        self.target_w, self.target_h = (
            int(x) for x in target_resolution.split("x")
        )

    async def validate_clips(
        self,
        clip_paths: list[dict[str, str]],
    ) -> list[ClipValidation]:
        """Validate a batch of clips.

        Parameters
        ----------
        clip_paths : list[dict]
            Each dict must have ``clip_id`` and ``file_path``.

        Returns
        -------
        list[ClipValidation]
            Validation results for every clip.

        Raises
        ------
        RuntimeError
            If no clips pass validation.
        """
        results: list[ClipValidation] = []

        # Validate clips in parallel (bounded to avoid fd exhaustion)
        sem = asyncio.Semaphore(8)

        async def _bounded_validate(item: dict[str, str]) -> ClipValidation:
            async with sem:
                return await self._validate_single(item["clip_id"], item["file_path"])

        results = await asyncio.gather(*[_bounded_validate(item) for item in clip_paths])

        for val in results:
            if val.is_valid:
                logger.debug("clip_valid", clip_id=val.clip_id, duration=val.duration_seconds)
            else:
                logger.warning("clip_invalid", clip_id=val.clip_id, errors=val.errors)

        valid_count = sum(1 for r in results if r.is_valid)
        if valid_count == 0:
            raise RuntimeError(
                f"All {len(results)} clips failed validation. "
                f"Errors: {[r.errors for r in results]}"
            )

        logger.info(
            "clip_validation_complete",
            total=len(results),
            valid=valid_count,
            invalid=len(results) - valid_count,
        )
        return results

    async def _validate_single(self, clip_id: str, file_path: str) -> ClipValidation:
        """Validate a single clip file."""
        val = ClipValidation(clip_id=clip_id, file_path=file_path)

        # Check file existence
        if not os.path.exists(file_path):
            val.is_valid = False
            val.errors.append(f"File does not exist: {file_path}")
            return val

        # Check file size
        val.file_size_bytes = os.path.getsize(file_path)
        if val.file_size_bytes < _MIN_FILE_SIZE:
            val.is_valid = False
            val.errors.append(
                f"File too small ({val.file_size_bytes} bytes < {_MIN_FILE_SIZE} bytes)"
            )
            return val

        # Probe with ffprobe
        probe = await self._ffprobe(file_path)
        if not probe:
            val.is_valid = False
            val.errors.append("ffprobe failed to read file")
            return val

        streams = probe.get("streams", [])
        video_streams = [s for s in streams if s.get("codec_type") == "video"]
        audio_streams = [s for s in streams if s.get("codec_type") == "audio"]

        # Check video stream
        val.has_video = len(video_streams) > 0
        if not val.has_video:
            val.is_valid = False
            val.errors.append("No video stream found")
            return val

        vs = video_streams[0]
        val.width = int(vs.get("width", 0))
        val.height = int(vs.get("height", 0))
        val.codec = vs.get("codec_name", "unknown")
        val.duration_seconds = float(vs.get("duration", 0))

        # Fall back to format duration if stream duration is 0
        if val.duration_seconds <= 0:
            fmt = probe.get("format", {})
            val.duration_seconds = float(fmt.get("duration", 0))

        # Check audio stream
        val.has_audio = len(audio_streams) > 0
        if self.require_audio and not val.has_audio:
            val.is_valid = False
            val.errors.append("No audio stream found (required)")

        # Check minimum duration
        if val.duration_seconds < self.min_duration:
            val.is_valid = False
            val.errors.append(
                f"Duration too short ({val.duration_seconds:.2f}s < {self.min_duration}s)"
            )

        # Check resolution match (warning only)
        if val.width > 0 and val.height > 0:
            if val.width != self.target_w or val.height != self.target_h:
                val.errors.append(
                    f"Resolution mismatch: {val.width}x{val.height} "
                    f"(expected {self.target_w}x{self.target_h}) — "
                    f"clip will still be used"
                )
                # Don't mark as invalid — the assembler handles scaling

        return val

    @staticmethod
    async def _ffprobe(file_path: str) -> dict[str, Any] | None:
        """Run ffprobe and return JSON output."""
        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            file_path,
        ]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            stdout_bytes, _ = await asyncio.wait_for(
                proc.communicate(), timeout=30.0,
            )
            if proc.returncode == 0 and stdout_bytes:
                return json.loads(stdout_bytes.decode())
        except Exception:
            pass
        return None
