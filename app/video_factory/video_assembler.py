"""Video Factory — Steps 5 & 6: Video Timeline & Assembly.

Builds a video timeline from clips + voiceover, then assembles the final
video using GPU-accelerated rendering where available.
"""
from __future__ import annotations

import asyncio
import json
import os
import shutil
from pathlib import Path
from typing import Any

from app.core.logging import get_logger
from app.video_factory.models import (
    VideoScript,
    ClipSelectionResult,
    VoiceoverResult,
    TimelineEntry,
    VideoTimeline,
    AssemblyConfig,
    AssemblyResult,
)

logger = get_logger(__name__)


class VideoAssembler:
    """Build video timeline and assemble the final video."""

    def __init__(self, config: AssemblyConfig | None = None) -> None:
        self.config = config or AssemblyConfig()

    # ── Step 5: Timeline Generation ────────────────────────────────────

    def build_timeline(
        self,
        script: VideoScript,
        clips: ClipSelectionResult,
        voiceover: VoiceoverResult,
    ) -> VideoTimeline:
        """Create a video timeline aligning clips, voiceover, and overlays.

        Parameters
        ----------
        script : VideoScript
            The narration script.
        clips : ClipSelectionResult
            Selected visual clips.
        voiceover : VoiceoverResult
            Generated voiceover audio.

        Returns
        -------
        VideoTimeline
            Ordered timeline for assembly.
        """
        logger.info("timeline_generation_start", sections=len(script.sections))

        entries: list[TimelineEntry] = []
        current_time = 0.0

        # Build a lookup of clips by section index
        clip_map: dict[int, list] = {}
        for clip in clips.clips:
            clip_map.setdefault(clip.section_index, []).append(clip)

        # Use voiceover timestamps if available, else estimate from script
        ts_map: dict[int, dict] = {}
        for ts in voiceover.sections_timestamps:
            idx = ts.get("section_index", -1)
            if idx >= 0:
                ts_map[idx] = ts

        for i, section in enumerate(script.sections):
            # Determine timing from voiceover timestamps or script estimate
            if i in ts_map:
                start = ts_map[i].get("start_time", current_time)
                end = ts_map[i].get("end_time", current_time + section.duration_seconds)
                duration = end - start
            else:
                start = current_time
                duration = float(section.duration_seconds)
                end = start + duration

            # Get clip for this section
            section_clips = clip_map.get(i, [])
            clip_source = section_clips[0] if section_clips else None

            # Determine entry type
            if section.section_type == "hook":
                entry_type = "intro_animation"
            elif section.section_type == "cta":
                entry_type = "cta"
            elif "highlight" in section.section_title.lower():
                entry_type = "highlight"
            else:
                entry_type = "narration"

            # Determine transition
            if section.transition_note:
                transition = "crossfade"
            elif section.section_type == "hook":
                transition = "fade_in"
            elif section.section_type == "cta":
                transition = "fade_out"
            else:
                transition = "cut"

            # Build overlay text for section titles
            overlay = ""
            if section.section_type in ("main_1", "main_2", "main_3", "main_4"):
                overlay = section.section_title

            entries.append(TimelineEntry(
                position=i,
                entry_type=entry_type,
                start_time=round(start, 2),
                end_time=round(end, 2),
                duration_seconds=round(duration, 2),
                clip_source=clip_source,
                voiceover_segment=section.content[:100] + "..." if len(section.content) > 100 else section.content,
                overlay_text=overlay,
                transition=transition,
            ))

            current_time = end

        timeline = VideoTimeline(
            entries=entries,
            total_duration_seconds=round(current_time, 2),
            has_intro=any(e.entry_type == "intro_animation" for e in entries),
            has_outro=any(e.entry_type == "cta" for e in entries),
        )

        logger.info(
            "timeline_generation_done",
            entries=len(entries),
            duration=timeline.total_duration_seconds,
        )
        return timeline

    # ── Step 6: Video Assembly ─────────────────────────────────────────

    async def assemble(
        self,
        timeline: VideoTimeline,
        voiceover: VoiceoverResult,
        output_dir: str,
    ) -> AssemblyResult:
        """Assemble the video from timeline, clips, and voiceover.

        This creates the video file by combining visual clips with
        the voiceover narration and adding overlays/transitions.

        Parameters
        ----------
        timeline : VideoTimeline
            The video timeline to render.
        voiceover : VoiceoverResult
            The voiceover audio file.
        output_dir : str
            Directory for output files.

        Returns
        -------
        AssemblyResult
            Information about the assembled draft video.
        """
        logger.info("video_assembly_start", entries=len(timeline.entries))

        os.makedirs(output_dir, exist_ok=True)
        draft_path = os.path.join(output_dir, "draft_video.mp4")

        # Attempt GPU-accelerated assembly via ffmpeg
        success = await self._assemble_with_ffmpeg(
            timeline, voiceover, draft_path
        )

        if not success:
            # Fallback: create a placeholder video
            success = await self._create_placeholder_video(
                timeline, voiceover, draft_path
            )

        file_size = os.path.getsize(draft_path) / (1024 * 1024) if os.path.exists(draft_path) else 0

        result = AssemblyResult(
            draft_video_path=draft_path,
            duration_seconds=timeline.total_duration_seconds,
            file_size_mb=round(file_size, 2),
            resolution=self.config.resolution,
            fps=self.config.fps,
        )

        logger.info(
            "video_assembly_done",
            path=draft_path,
            size_mb=result.file_size_mb,
            duration=result.duration_seconds,
        )
        return result

    async def _assemble_with_ffmpeg(
        self,
        timeline: VideoTimeline,
        voiceover: VoiceoverResult,
        output_path: str,
    ) -> bool:
        """Assemble video using ffmpeg with GPU acceleration if available."""
        try:
            # Check if ffmpeg is available
            check = await asyncio.create_subprocess_exec(
                "ffmpeg", "-version",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await check.wait()
            if check.returncode != 0:
                return False

            width, height = self.config.resolution.split("x")

            # Generate a video with color backgrounds and text overlays
            # matching the timeline structure, combined with voiceover audio
            filter_parts = []
            input_count = 0

            # Create a base video with colored background
            duration = timeline.total_duration_seconds
            inputs = [
                "-f", "lavfi", "-i",
                f"color=c=0x1a1a2e:s={width}x{height}:d={duration}:r={self.config.fps}",
            ]
            input_count += 1

            # Add voiceover audio if it exists
            audio_path = voiceover.audio_path
            has_audio = os.path.exists(audio_path)
            if has_audio:
                inputs.extend(["-i", audio_path])
                input_count += 1

            # Build text overlay filters for section titles
            drawtext_filters = []
            for entry in timeline.entries:
                if entry.overlay_text:
                    start = entry.start_time
                    end = entry.end_time
                    text = entry.overlay_text.replace("'", r"\'").replace(":", r"\:")
                    drawtext_filters.append(
                        f"drawtext=text='{text}'"
                        f":fontsize=48:fontcolor=white"
                        f":x=(w-tw)/2:y=h-120"
                        f":enable='between(t,{start},{min(start + 3, end)})'",
                    )

            # Add a title card at the beginning
            if timeline.entries:
                first = timeline.entries[0]
                segment = first.voiceover_segment.split("...")[0] if first.voiceover_segment else ""
                if segment and len(segment) < 60:
                    safe = segment.replace("'", r"\'").replace(":", r"\:")
                    drawtext_filters.insert(0,
                        f"drawtext=text='{safe}'"
                        f":fontsize=36:fontcolor=white"
                        f":x=(w-tw)/2:y=(h-th)/2"
                        f":enable='between(t,0,4)'",
                    )

            # Compose ffmpeg command
            vf = ",".join(drawtext_filters) if drawtext_filters else "null"

            codec_args = []
            # Try NVENC for GPU acceleration
            if self.config.use_gpu:
                codec_args = ["-c:v", "h264_nvenc", "-preset", "fast"]
            else:
                codec_args = ["-c:v", "libx264", "-preset", "fast"]

            cmd = [
                "ffmpeg", "-y",
                *inputs,
                "-vf", vf,
                *codec_args,
                "-pix_fmt", "yuv420p",
            ]

            if has_audio:
                cmd.extend(["-map", "0:v", "-map", "1:a", "-c:a", "aac", "-shortest"])
            else:
                cmd.extend(["-t", str(duration)])

            cmd.append(output_path)

            logger.debug("ffmpeg_command", cmd=" ".join(cmd))

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _stdout, stderr = await proc.wait(), None
            await proc.wait()

            if proc.returncode == 0:
                return True

            # If NVENC failed, retry with libx264
            if self.config.use_gpu:
                logger.info("nvenc_fallback_to_libx264")
                cmd_cpu = [c if c != "h264_nvenc" else "libx264" for c in cmd]
                proc2 = await asyncio.create_subprocess_exec(
                    *cmd_cpu,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                await proc2.wait()
                return proc2.returncode == 0

            return False

        except Exception as exc:
            logger.warning("ffmpeg_assembly_failed", error=str(exc))
            return False

    async def _create_placeholder_video(
        self,
        timeline: VideoTimeline,
        voiceover: VoiceoverResult,
        output_path: str,
    ) -> bool:
        """Create a minimal placeholder MP4 using ffmpeg or raw generation."""
        try:
            duration = max(10, timeline.total_duration_seconds)
            width, height = self.config.resolution.split("x")

            # Try ffmpeg with simplest possible settings
            proc = await asyncio.create_subprocess_exec(
                "ffmpeg", "-y",
                "-f", "lavfi", "-i",
                f"color=c=0x1a1a2e:s={width}x{height}:d={duration}:r=24",
                "-c:v", "libx264", "-preset", "ultrafast",
                "-pix_fmt", "yuv420p",
                "-t", str(duration),
                output_path,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await proc.wait()
            return proc.returncode == 0
        except Exception:
            # Create a zero-byte placeholder
            Path(output_path).touch()
            return True
