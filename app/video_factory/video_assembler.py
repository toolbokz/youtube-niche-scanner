"""Video Factory — Video Assembler (Compilation Pipeline).

Assembles a final compilation video from real extracted clip segments
using ffmpeg's concat demuxer.  **No slides, text panels, or
placeholder footage** — only real video clips are used.

**Optimised single-pass encoding architecture:**

1. Clips are extracted with stream copy (no encoding)
2. Timeline is built from validated clips
3. The **only encoding step** happens here — concat + encode in one pass
4. GPU acceleration is auto-detected and used when available
"""
from __future__ import annotations

import asyncio
import os
from pathlib import Path

from app.core.logging import get_logger
from app.video_factory.models import (
    AssemblyConfig,
    AssemblyResult,
    CompilationTimeline,
    CompilationTimelineEntry,
    ExtractedClipInfo,
    VideoSettings,
)

logger = get_logger(__name__)


class CompilationAssembler:
    """Assemble a compilation video from real extracted clips.

    Parameters
    ----------
    settings : VideoSettings
        User-configurable settings (resolution, orientation, etc.).
    config : AssemblyConfig, optional
        Lower-level assembly config (fps, codec opts).
    encoder : str
        Encoder to use — e.g. ``h264_nvenc``, ``h264_qsv``, ``libx264``.
        Defaults to ``libx264`` (CPU).
    cpu_preset : str
        x264 preset for CPU encoding (``veryfast`` recommended).
    gpu_preset : str
        NVENC preset for GPU encoding.
    crf : int
        Constant Rate Factor for CPU encoding quality.
    """

    def __init__(
        self,
        settings: VideoSettings | None = None,
        config: AssemblyConfig | None = None,
        encoder: str = "libx264",
        cpu_preset: str = "veryfast",
        gpu_preset: str = "fast",
        crf: int = 20,
    ) -> None:
        self.settings = settings or VideoSettings()
        self.config = config or AssemblyConfig(
            resolution=self.settings.resolution,
            use_gpu=self.settings.use_gpu,
        )
        self.encoder = encoder
        self.cpu_preset = cpu_preset
        self.gpu_preset = gpu_preset
        self.crf = crf

    # ── Timeline Building ──────────────────────────────────────────────

    def build_timeline(
        self,
        clips: list[ExtractedClipInfo],
    ) -> CompilationTimeline:
        """Build a compilation timeline from validated extracted clips.

        Clips are ordered by their ``position`` field.  The total
        duration is capped to the target duration from settings.

        Parameters
        ----------
        clips : list[ExtractedClipInfo]
            Validated extracted clips (only valid ones should be passed).

        Returns
        -------
        CompilationTimeline
        """
        target_seconds = self.settings.target_duration_minutes * 60
        sorted_clips = sorted(clips, key=lambda c: c.position)

        entries: list[CompilationTimelineEntry] = []
        cumulative_duration = 0.0

        for clip in sorted_clips:
            if not clip.is_valid:
                continue
            if not clip.file_path or not os.path.exists(clip.file_path):
                logger.warning("clip_missing_in_timeline", clip_id=clip.clip_id)
                continue

            remaining = target_seconds - cumulative_duration
            if remaining <= 0:
                logger.info("target_duration_reached", target=target_seconds)
                break

            clip_dur = min(clip.duration_seconds, remaining)

            # Determine transition
            if len(entries) == 0:
                transition = "fade_in"
            elif cumulative_duration + clip_dur >= target_seconds - 1:
                transition = "fade_out"
            else:
                transition = self.settings.transition_style

            entries.append(CompilationTimelineEntry(
                position=len(entries),
                clip_id=clip.clip_id,
                clip_file_path=clip.file_path,
                source_video_id=clip.source_video_id,
                start_seconds=clip.start_seconds,
                end_seconds=clip.end_seconds,
                duration_seconds=round(clip_dur, 3),
                segment_type=clip.segment_type,
                energy_level=clip.energy_level,
                transition=transition,
            ))
            cumulative_duration += clip_dur

        timeline = CompilationTimeline(
            entries=entries,
            total_duration_seconds=round(cumulative_duration, 3),
            target_duration_seconds=float(target_seconds),
        )

        logger.info(
            "compilation_timeline_built",
            entries=len(entries),
            total_duration=timeline.total_duration_seconds,
            target_duration=target_seconds,
        )
        return timeline

    # ── Video Assembly — Single-pass encoding ──────────────────────────

    async def assemble(
        self,
        timeline: CompilationTimeline,
        output_dir: str,
    ) -> AssemblyResult:
        """Assemble the final compilation video from timeline clips.

        Uses ffmpeg concat demuxer to join stream-copied clips and
        encode the final video in a **single pass**.

        Parameters
        ----------
        timeline : CompilationTimeline
            The ordered compilation timeline.
        output_dir : str
            Directory for the output video.

        Returns
        -------
        AssemblyResult

        Raises
        ------
        RuntimeError
            If assembly fails and no video is produced.
        """
        if not timeline.entries:
            raise RuntimeError("Cannot assemble video: timeline has no entries")

        os.makedirs(output_dir, exist_ok=True)
        draft_path = os.path.join(output_dir, "draft_video.mp4")

        # Write the concat demuxer input file
        concat_file = os.path.join(output_dir, "_concat_list.txt")
        self._write_concat_file(timeline, concat_file)

        # Run single-pass encoding
        success = await self._encode_final(concat_file, draft_path)

        if not success:
            raise RuntimeError(
                "Video assembly failed: ffmpeg concat could not produce output. "
                "Check that all clip files exist and are valid MP4s."
            )

        file_size = os.path.getsize(draft_path) / (1024 * 1024) if os.path.exists(draft_path) else 0

        result = AssemblyResult(
            draft_video_path=draft_path,
            duration_seconds=timeline.total_duration_seconds,
            file_size_mb=round(file_size, 2),
            resolution=self.config.resolution,
            fps=self.config.fps,
            clips_used=len(timeline.entries),
        )

        logger.info(
            "video_assembly_done",
            path=draft_path,
            size_mb=result.file_size_mb,
            duration=result.duration_seconds,
            clips=result.clips_used,
            encoder=self.encoder,
        )
        return result

    # ── Internal helpers ───────────────────────────────────────────────

    @staticmethod
    def _write_concat_file(
        timeline: CompilationTimeline,
        concat_path: str,
    ) -> None:
        """Write the ffmpeg concat demuxer file.

        Each line references an absolute path to a clip file.
        """
        lines: list[str] = []
        for entry in timeline.entries:
            abs_path = os.path.abspath(entry.clip_file_path)
            # ffmpeg concat format: file 'path'
            # Escape single quotes in paths
            escaped = abs_path.replace("'", "'\\''")
            lines.append(f"file '{escaped}'")

        with open(concat_path, "w") as f:
            f.write("\n".join(lines) + "\n")

        logger.debug("concat_file_written", path=concat_path, entries=len(lines))

    def _build_encoder_args(self) -> list[str]:
        """Build encoder-specific FFmpeg arguments.

        Returns the codec/preset/quality args for one encoding pass.
        """
        is_gpu = self.encoder != "libx264"

        if is_gpu:
            # GPU encoder (NVENC / QSV / VideoToolbox)
            args = [
                "-c:v", self.encoder,
                "-preset", self.gpu_preset,
                "-c:a", "aac", "-b:a", "192k",
            ]
            # NVENC-specific quality settings
            if self.encoder == "h264_nvenc":
                args.extend(["-rc", "vbr", "-cq", str(self.crf)])
        else:
            # CPU encoder
            args = [
                "-c:v", "libx264",
                "-preset", self.cpu_preset,
                "-crf", str(self.crf),
                "-c:a", "aac", "-b:a", "192k",
            ]

        # Resolution scaling/padding for uniform output
        w, h = self.config.resolution.split("x")
        scale_filter = (
            f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
            f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=black,"
            f"setsar=1"
        )
        args.extend(["-vf", scale_filter])

        return args

    async def _encode_final(
        self,
        concat_file: str,
        output_path: str,
    ) -> bool:
        """Run the single-pass final encode.

        Tries the configured encoder first, then falls back through
        GPU → CPU if the primary encoder fails.
        """
        # Primary attempt with configured encoder
        encoder_args = self._build_encoder_args()
        success = await self._run_concat_cmd(concat_file, output_path, encoder_args)
        if success:
            return True

        # If GPU encoder failed, fall back to CPU
        if self.encoder != "libx264":
            logger.info(
                "gpu_encoder_failed_fallback_to_cpu",
                primary=self.encoder,
            )
            self.encoder = "libx264"
            fallback_args = self._build_encoder_args()
            success = await self._run_concat_cmd(concat_file, output_path, fallback_args)
            if success:
                return True

        return False

    async def _run_concat_cmd(
        self,
        concat_file: str,
        output_path: str,
        codec_args: list[str],
    ) -> bool:
        """Execute a single ffmpeg concat command."""
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_file,
            *codec_args,
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            output_path,
        ]

        logger.debug("ffmpeg_concat_cmd", cmd=" ".join(cmd))

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr_bytes = await proc.communicate()

            if proc.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                return True

            stderr_text = stderr_bytes.decode(errors="replace")[-300:]
            logger.warning("ffmpeg_concat_failed", rc=proc.returncode, stderr=stderr_text)
            return False

        except Exception as exc:
            logger.warning("ffmpeg_concat_error", error=str(exc))
            return False
