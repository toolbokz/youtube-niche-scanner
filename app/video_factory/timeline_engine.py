"""Video Factory — Timeline Engine.

Interprets user-edited timelines from the Video Editor frontend,
applies clip trims, transitions, text overlays, and builds the
FFmpeg filter graph for final rendering.

This bridges the gap between the visual editor and the FFmpeg
rendering pipeline, translating UI state into concrete video
processing commands.
"""
from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass, field
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
#  Data Structures
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class TimelineClip:
    """A single clip on the editor timeline."""

    clip_id: str
    source_video_id: str
    source_file_path: str
    start_seconds: float
    end_seconds: float
    duration_seconds: float
    position: int
    segment_type: str = ""
    energy_level: str = "medium"
    label: str = ""
    # Trim overrides (user-adjusted in editor)
    trim_start: float | None = None
    trim_end: float | None = None

    @property
    def effective_start(self) -> float:
        return self.trim_start if self.trim_start is not None else self.start_seconds

    @property
    def effective_end(self) -> float:
        return self.trim_end if self.trim_end is not None else self.end_seconds

    @property
    def effective_duration(self) -> float:
        return max(0, self.effective_end - self.effective_start)


@dataclass
class TimelineTransition:
    """A transition between two clips."""

    type: str = "cut"  # cut | fade | crossdissolve | zoom
    duration_seconds: float = 0.5
    after_clip_index: int = 0


@dataclass
class TimelineMarker:
    """A marker on the timeline."""

    id: str = ""
    timestamp: float = 0.0
    label: str = ""
    marker_type: str = "note"  # note | transition | text | sfx
    color: str = "#3b82f6"


@dataclass
class TextOverlay:
    """A text overlay on a timeline range."""

    id: str = ""
    text: str = ""
    start_seconds: float = 0.0
    end_seconds: float = 0.0
    font_size: int = 48
    color: str = "#ffffff"
    position: str = "center"  # top | center | bottom | top-left | ...
    background_opacity: float = 0.5


@dataclass
class TimelineConfig:
    """Complete editor timeline configuration."""

    clips: list[TimelineClip] = field(default_factory=list)
    transitions: list[TimelineTransition] = field(default_factory=list)
    markers: list[TimelineMarker] = field(default_factory=list)
    text_overlays: list[TextOverlay] = field(default_factory=list)

    # Video settings
    orientation: str = "horizontal"  # horizontal | vertical
    resolution: str = "1080p"
    target_duration_seconds: float = 480.0
    max_scene_duration: float | None = None
    background_audio: str = "none"  # none | ambient | energetic

    # Rendering
    is_preview: bool = False

    @property
    def resolution_tuple(self) -> tuple[int, int]:
        """Return (width, height) for the selected resolution."""
        res_map = {
            "720p": (1280, 720),
            "1080p": (1920, 1080),
            "1440p": (2560, 1440),
            "4k": (3840, 2160),
        }
        w, h = res_map.get(self.resolution, (1920, 1080))
        if self.orientation == "vertical":
            return (h, w)
        return (w, h)

    @property
    def total_duration(self) -> float:
        return sum(c.effective_duration for c in self.clips)


# ═══════════════════════════════════════════════════════════════════════════════
#  Timeline Engine
# ═══════════════════════════════════════════════════════════════════════════════


class TimelineEngine:
    """Processes an editor timeline into FFmpeg rendering commands.

    Responsibilities:
    - Apply clip trims
    - Enforce max-scene-duration pacing
    - Auto-remove lowest-scoring clips if over target duration
    - Build FFmpeg concat/filter graph
    - Generate rendering commands
    """

    def __init__(self, output_dir: str = "data/video_factory") -> None:
        self.output_dir = output_dir

    # ── Timeline Validation & Processing ───────────────────────────────

    def process_timeline(self, config: TimelineConfig) -> TimelineConfig:
        """Process and validate a timeline configuration.

        Applies:
        1. Max scene duration enforcement
        2. Duration trimming (lowest-scoring clips removed if over target)
        3. Position re-indexing

        Returns a new processed TimelineConfig.
        """
        clips = list(config.clips)

        # 1. Enforce max scene duration
        if config.max_scene_duration and config.max_scene_duration > 0:
            clips = self._enforce_scene_pacing(clips, config.max_scene_duration)

        # 2. Trim to target duration
        if config.target_duration_seconds > 0:
            clips = self._trim_to_duration(clips, config.target_duration_seconds)

        # 3. Re-index positions
        for i, clip in enumerate(clips):
            clip.position = i

        return TimelineConfig(
            clips=clips,
            transitions=config.transitions,
            markers=config.markers,
            text_overlays=config.text_overlays,
            orientation=config.orientation,
            resolution=config.resolution,
            target_duration_seconds=config.target_duration_seconds,
            max_scene_duration=config.max_scene_duration,
            background_audio=config.background_audio,
            is_preview=config.is_preview,
        )

    def _enforce_scene_pacing(
        self,
        clips: list[TimelineClip],
        max_duration: float,
    ) -> list[TimelineClip]:
        """Trim clips that exceed the max scene duration."""
        result = []
        for clip in clips:
            if clip.effective_duration > max_duration:
                new_end = clip.effective_start + max_duration
                clip.trim_end = new_end
            result.append(clip)
        return result

    def _trim_to_duration(
        self,
        clips: list[TimelineClip],
        target: float,
    ) -> list[TimelineClip]:
        """Remove lowest-scoring clips if total exceeds target duration."""
        total = sum(c.effective_duration for c in clips)
        if total <= target:
            return clips

        # Score clips (higher energy / earlier position = higher score)
        energy_scores = {"climax": 4, "high": 3, "medium": 2, "low": 1}

        scored = sorted(
            clips,
            key=lambda c: energy_scores.get(c.energy_level, 1),
        )

        # Remove lowest-scoring clips until we're under target
        removed: set[str] = set()
        while total > target and scored:
            worst = scored.pop(0)
            total -= worst.effective_duration
            removed.add(worst.clip_id)

        return [c for c in clips if c.clip_id not in removed]

    # ── FFmpeg Command Generation ──────────────────────────────────────

    def build_concat_file(
        self,
        config: TimelineConfig,
        job_id: str,
    ) -> str:
        """Write an FFmpeg concat demuxer file from the timeline.

        Returns the path to the concat file.
        """
        job_dir = os.path.join(self.output_dir, job_id)
        os.makedirs(job_dir, exist_ok=True)
        concat_path = os.path.join(job_dir, "_editor_concat.txt")

        lines: list[str] = []
        for clip in config.clips:
            abs_path = os.path.abspath(clip.source_file_path)
            escaped = abs_path.replace("'", "'\\''")
            lines.append(f"file '{escaped}'")

            # If trimmed, add inpoint/outpoint
            if clip.trim_start is not None or clip.trim_end is not None:
                lines.append(f"inpoint {clip.effective_start:.3f}")
                lines.append(f"outpoint {clip.effective_end:.3f}")

        with open(concat_path, "w") as f:
            f.write("\n".join(lines) + "\n")

        logger.info("editor_concat_file_written", path=concat_path, clips=len(config.clips))
        return concat_path

    def build_filter_graph(self, config: TimelineConfig) -> str | None:
        """Build an FFmpeg filter graph for transitions and text overlays.

        Returns the filter_complex string, or None if no filters needed.
        """
        filters: list[str] = []
        w, h = config.resolution_tuple

        # Scale + pad for uniform resolution
        scale_filter = (
            f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
            f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=black,"
            f"setsar=1"
        )
        filters.append(f"[0:v]{scale_filter}[scaled]")

        # Text overlays
        last_label = "scaled"
        for i, overlay in enumerate(config.text_overlays):
            x, y = self._text_position(overlay.position, w, h)
            escaped_text = overlay.text.replace("'", "\\'").replace(":", "\\:")
            out_label = f"txt{i}"

            font_filter = (
                f"drawtext=text='{escaped_text}'"
                f":fontsize={overlay.font_size}"
                f":fontcolor={overlay.color}"
                f":x={x}:y={y}"
                f":enable='between(t,{overlay.start_seconds:.2f},{overlay.end_seconds:.2f})'"
                f":box=1:boxcolor=black@{overlay.background_opacity:.1f}"
                f":boxborderw=8"
            )
            filters.append(f"[{last_label}]{font_filter}[{out_label}]")
            last_label = out_label

        if len(filters) <= 1 and not config.text_overlays:
            return None  # Just scale — no complex filter needed

        return ";".join(filters)

    def build_render_command(
        self,
        config: TimelineConfig,
        concat_file: str,
        output_path: str,
        encoder: str = "libx264",
        cpu_preset: str = "veryfast",
        crf: int = 20,
    ) -> list[str]:
        """Build the complete FFmpeg render command.

        Parameters
        ----------
        config : TimelineConfig
            Processed timeline configuration.
        concat_file : str
            Path to the concat demuxer file.
        output_path : str
            Output video file path.
        encoder : str
            FFmpeg video encoder.
        cpu_preset : str
            Encoding speed preset.
        crf : int
            Quality setting.

        Returns
        -------
        list[str]
            The complete FFmpeg command as a list of arguments.
        """
        w, h = config.resolution_tuple
        is_preview = config.is_preview

        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_file,
        ]

        # Filter graph
        filter_graph = self.build_filter_graph(config)
        if filter_graph:
            cmd.extend(["-filter_complex", filter_graph])
            # Find the last output label
            last_label = filter_graph.split("[")[-1].rstrip("]")
            cmd.extend(["-map", f"[{last_label}]", "-map", "0:a?"])
        else:
            # Simple scale filter
            scale = (
                f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
                f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=black,"
                f"setsar=1"
            )
            cmd.extend(["-vf", scale])

        # Encoder settings
        if is_preview:
            # Low quality preview — fast
            cmd.extend([
                "-c:v", "libx264",
                "-preset", "ultrafast",
                "-crf", "28",
            ])
        else:
            cmd.extend([
                "-c:v", encoder,
                "-preset", cpu_preset,
                "-crf", str(crf),
            ])

        # Audio
        cmd.extend(["-c:a", "aac", "-b:a", "192k"])

        # Output settings
        cmd.extend([
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            output_path,
        ])

        return cmd

    async def render(
        self,
        config: TimelineConfig,
        job_id: str,
        encoder: str = "libx264",
        cpu_preset: str = "veryfast",
        crf: int = 20,
        on_progress: Any = None,
    ) -> str:
        """Render the timeline to a video file.

        Parameters
        ----------
        config : TimelineConfig
            The editor timeline to render.
        job_id : str
            Job ID for output directory.
        encoder : str
            FFmpeg encoder name.
        cpu_preset : str
            Encoding preset.
        crf : int
            Quality CRF value.
        on_progress : callable, optional
            Progress callback(pct: float).

        Returns
        -------
        str
            Path to the rendered video.

        Raises
        ------
        RuntimeError
            If rendering fails.
        """
        # Process the timeline
        processed = self.process_timeline(config)

        # Validate
        if not processed.clips:
            raise RuntimeError("Timeline has no clips to render")

        suffix = "_preview" if config.is_preview else "_final"
        job_dir = os.path.join(self.output_dir, job_id)
        os.makedirs(job_dir, exist_ok=True)
        output_path = os.path.join(job_dir, f"editor{suffix}.mp4")

        # Build concat file
        concat_file = self.build_concat_file(processed, job_id)

        # Build render command
        cmd = self.build_render_command(
            processed, concat_file, output_path,
            encoder=encoder, cpu_preset=cpu_preset, crf=crf,
        )

        logger.info("editor_render_start", job_id=job_id, cmd=" ".join(cmd))

        if on_progress:
            on_progress(10.0)

        # Execute
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr_bytes = await proc.communicate()

        if on_progress:
            on_progress(90.0)

        if proc.returncode != 0:
            stderr_text = stderr_bytes.decode(errors="replace")[-500:]
            raise RuntimeError(f"FFmpeg render failed (rc={proc.returncode}): {stderr_text}")

        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            raise RuntimeError("FFmpeg produced empty or missing output")

        file_size = os.path.getsize(output_path) / (1024 * 1024)
        logger.info(
            "editor_render_complete",
            job_id=job_id,
            path=output_path,
            size_mb=round(file_size, 2),
            preview=config.is_preview,
        )

        if on_progress:
            on_progress(100.0)

        return output_path

    # ── Helpers ────────────────────────────────────────────────────────────

    @staticmethod
    def _text_position(pos: str, w: int, h: int) -> tuple[str, str]:
        """Convert a named position to FFmpeg x/y expressions."""
        positions = {
            "top": ("(w-text_w)/2", "30"),
            "center": ("(w-text_w)/2", "(h-text_h)/2"),
            "bottom": ("(w-text_w)/2", "h-text_h-30"),
            "top-left": ("30", "30"),
            "top-right": ("w-text_w-30", "30"),
            "bottom-left": ("30", "h-text_h-30"),
            "bottom-right": ("w-text_w-30", "h-text_h-30"),
        }
        return positions.get(pos, ("(w-text_w)/2", "(h-text_h)/2"))

    @staticmethod
    def parse_timeline_payload(data: dict[str, Any]) -> TimelineConfig:
        """Parse a JSON payload from the frontend into a TimelineConfig.

        Parameters
        ----------
        data : dict
            The JSON body from the editor API endpoint.

        Returns
        -------
        TimelineConfig
        """
        clips = []
        for c in data.get("clips", []):
            clips.append(TimelineClip(
                clip_id=c.get("clip_id", ""),
                source_video_id=c.get("source_video_id", ""),
                source_file_path=c.get("source_file_path", ""),
                start_seconds=float(c.get("start_seconds", 0)),
                end_seconds=float(c.get("end_seconds", 0)),
                duration_seconds=float(c.get("duration_seconds", 0)),
                position=int(c.get("position", 0)),
                segment_type=c.get("segment_type", ""),
                energy_level=c.get("energy_level", "medium"),
                label=c.get("label", ""),
                trim_start=c.get("trim_start"),
                trim_end=c.get("trim_end"),
            ))

        transitions = []
        for t in data.get("transitions", []):
            transitions.append(TimelineTransition(
                type=t.get("type", "cut"),
                duration_seconds=float(t.get("duration_seconds", 0.5)),
                after_clip_index=int(t.get("after_clip_index", 0)),
            ))

        markers = []
        for m in data.get("markers", []):
            markers.append(TimelineMarker(
                id=m.get("id", ""),
                timestamp=float(m.get("timestamp", 0)),
                label=m.get("label", ""),
                marker_type=m.get("marker_type", "note"),
                color=m.get("color", "#3b82f6"),
            ))

        text_overlays = []
        for o in data.get("text_overlays", []):
            text_overlays.append(TextOverlay(
                id=o.get("id", ""),
                text=o.get("text", ""),
                start_seconds=float(o.get("start_seconds", 0)),
                end_seconds=float(o.get("end_seconds", 0)),
                font_size=int(o.get("font_size", 48)),
                color=o.get("color", "#ffffff"),
                position=o.get("position", "center"),
                background_opacity=float(o.get("background_opacity", 0.5)),
            ))

        return TimelineConfig(
            clips=clips,
            transitions=transitions,
            markers=markers,
            text_overlays=text_overlays,
            orientation=data.get("orientation", "horizontal"),
            resolution=data.get("resolution", "1080p"),
            target_duration_seconds=float(data.get("target_duration_seconds", 480)),
            max_scene_duration=data.get("max_scene_duration"),
            background_audio=data.get("background_audio", "none"),
            is_preview=data.get("is_preview", False),
        )
