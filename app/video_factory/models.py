"""Video Factory — Pydantic models for the video production pipeline.

Supports the **compilation pipeline** that downloads real YouTube
source videos, extracts segments, validates clips, and assembles
them into a final compilation video.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ── Job states ─────────────────────────────────────────────────────────────────

class JobStatus(str, Enum):
    QUEUED = "queued"
    # Compilation pipeline stages
    FETCHING_STRATEGY = "fetching_strategy"
    DOWNLOADING_VIDEOS = "downloading_videos"
    EXTRACTING_SEGMENTS = "extracting_segments"
    VALIDATING_CLIPS = "validating_clips"
    COPYRIGHT_CHECK = "copyright_check"
    BUILDING_TIMELINE = "building_timeline"
    ASSEMBLING_VIDEO = "assembling_video"
    GENERATING_THUMBNAIL = "generating_thumbnail"
    GENERATING_METADATA = "generating_metadata"
    CLEANING_TEMP = "cleaning_temp"
    COMPLETED = "completed"
    FAILED = "failed"


# ── Video Settings ─────────────────────────────────────────────────────────────

class VideoOrientation(str, Enum):
    LANDSCAPE = "landscape"     # 16:9 — 1920×1080
    PORTRAIT = "portrait"       # 9:16 — 1080×1920


class VideoSettings(BaseModel):
    """User-configurable video production settings."""
    target_duration_minutes: int = 8          # 3 | 5 | 8 | 10
    orientation: VideoOrientation = VideoOrientation.LANDSCAPE
    max_source_resolution: int = 1080
    transition_style: str = "crossfade"       # crossfade | cut | fade
    transition_duration: float = 0.5
    use_gpu: bool = True
    reencode_clips: bool = True               # True for uniform quality
    include_audio_from_clips: bool = True
    copyright_strict: bool = False

    # Extended settings for CI → VF workflow
    enable_voiceover: bool = False
    enable_subtitles: bool = False
    enable_thumbnail: bool = True
    enable_background_music: bool = False
    enable_transitions: bool = True

    @property
    def resolution(self) -> str:
        if self.orientation == VideoOrientation.PORTRAIT:
            return "1080x1920"
        return "1920x1080"

    @property
    def width(self) -> int:
        return int(self.resolution.split("x")[0])

    @property
    def height(self) -> int:
        return int(self.resolution.split("x")[1])


# ── Download Results ───────────────────────────────────────────────────────────

class DownloadedVideoInfo(BaseModel):
    """Info about a single downloaded source video."""
    video_id: str = ""
    title: str = ""
    file_path: str = ""
    duration_seconds: float = 0.0
    width: int = 0
    height: int = 0
    file_size_mb: float = 0.0


class DownloadStageResult(BaseModel):
    """Result from the video downloading stage."""
    downloaded: list[DownloadedVideoInfo] = Field(default_factory=list)
    failed: list[dict[str, str]] = Field(default_factory=list)
    source_dir: str = ""
    total_size_mb: float = 0.0


# ── Extracted Clips ────────────────────────────────────────────────────────────

class ExtractedClipInfo(BaseModel):
    """Info about a single extracted clip."""
    clip_id: str = ""
    source_video_id: str = ""
    file_path: str = ""
    start_seconds: float = 0.0
    end_seconds: float = 0.0
    duration_seconds: float = 0.0
    segment_type: str = ""
    energy_level: str = "medium"
    position: int = 0
    width: int = 0
    height: int = 0
    file_size_mb: float = 0.0
    is_valid: bool = True


class ExtractionStageResult(BaseModel):
    """Result from the segment extraction stage."""
    clips: list[ExtractedClipInfo] = Field(default_factory=list)
    failed: list[dict[str, str]] = Field(default_factory=list)
    clips_dir: str = ""
    total_duration_seconds: float = 0.0
    total_size_mb: float = 0.0


# ── Copyright Report ──────────────────────────────────────────────────────────

class CopyrightIssueInfo(BaseModel):
    """A single copyright concern."""
    severity: str = "warning"
    source_video_id: str = ""
    clip_id: str = ""
    message: str = ""
    recommendation: str = ""


class CopyrightReportInfo(BaseModel):
    """Copyright analysis result."""
    is_safe: bool = True
    issues: list[CopyrightIssueInfo] = Field(default_factory=list)
    unique_sources: int = 0
    source_usage: dict[str, float] = Field(default_factory=dict)


# ── Compilation Timeline ──────────────────────────────────────────────────────

class CompilationTimelineEntry(BaseModel):
    """A single entry in the compilation video timeline."""
    position: int = 0
    clip_id: str = ""
    clip_file_path: str = ""
    source_video_id: str = ""
    start_seconds: float = 0.0
    end_seconds: float = 0.0
    duration_seconds: float = 0.0
    segment_type: str = ""
    energy_level: str = "medium"
    transition: str = "crossfade"


class CompilationTimeline(BaseModel):
    """Complete compilation video timeline — ordered list of real clips."""
    entries: list[CompilationTimelineEntry] = Field(default_factory=list)
    total_duration_seconds: float = 0.0
    target_duration_seconds: float = 0.0


# ── Assembly ───────────────────────────────────────────────────────────────────

class AssemblyConfig(BaseModel):
    """Configuration for video assembly."""
    resolution: str = "1920x1080"
    fps: int = 30
    background_music_path: str = ""
    background_music_volume: float = 0.15
    transition_duration: float = 0.5
    text_font: str = "Arial"
    text_color: str = "#FFFFFF"
    text_bg_color: str = "#000000AA"
    embed_subtitles: bool = False
    use_gpu: bool = True


class AssemblyResult(BaseModel):
    """Result from video assembly."""
    draft_video_path: str = ""
    duration_seconds: float = 0.0
    file_size_mb: float = 0.0
    resolution: str = ""
    fps: int = 30
    clips_used: int = 0


# ── Thumbnail ──────────────────────────────────────────────────────────────────

class ThumbnailConcept(BaseModel):
    """AI-generated thumbnail concept."""
    visual_concept: str = ""
    text_overlay: str = ""
    color_scheme: list[str] = Field(default_factory=list)
    layout_structure: str = ""
    emotion_trigger: str = ""
    contrast_strategy: str = ""


class ThumbnailResult(BaseModel):
    """Result from thumbnail generation."""
    thumbnail_path: str = ""
    concept: ThumbnailConcept = Field(default_factory=ThumbnailConcept)
    width: int = 1280
    height: int = 720


# ── Metadata ──────────────────────────────────────────────────────────────────

class VideoMetadata(BaseModel):
    """Complete YouTube publishing metadata."""
    title: str = ""
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    hashtags: list[str] = Field(default_factory=list)
    chapters: list[dict[str, str]] = Field(default_factory=list)
    category: str = "Entertainment"
    language: str = "en"
    seo_keywords: list[str] = Field(default_factory=list)


# ── Final Output ───────────────────────────────────────────────────────────────

class VideoFactoryOutput(BaseModel):
    """Final output from the compilation video pipeline."""
    job_id: str = ""
    niche: str = ""
    # Strategy
    strategy_summary: dict[str, Any] = Field(default_factory=dict)
    # Downloads
    downloads: DownloadStageResult = Field(default_factory=DownloadStageResult)
    # Extraction
    extraction: ExtractionStageResult = Field(default_factory=ExtractionStageResult)
    # Copyright
    copyright_report: CopyrightReportInfo = Field(default_factory=CopyrightReportInfo)
    # Timeline
    timeline: CompilationTimeline = Field(default_factory=CompilationTimeline)
    # Assembly
    assembly: AssemblyResult = Field(default_factory=AssemblyResult)
    # Thumbnail
    thumbnail: ThumbnailResult = Field(default_factory=ThumbnailResult)
    # Metadata
    metadata: VideoMetadata = Field(default_factory=VideoMetadata)
    # Output paths
    output_dir: str = ""
    video_path: str = ""
    thumbnail_path: str = ""
    metadata_path: str = ""
    # Status
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    status: JobStatus = JobStatus.QUEUED
    error: str = ""
    # Settings used
    settings: VideoSettings = Field(default_factory=VideoSettings)


# ── Job Model ──────────────────────────────────────────────────────────────────

class FactoryJob(BaseModel):
    """Tracks a video factory job."""
    job_id: str = ""
    niche: str = ""
    status: JobStatus = JobStatus.QUEUED
    progress_pct: float = 0.0
    current_stage: str = ""
    stages_completed: list[str] = Field(default_factory=list)
    output: VideoFactoryOutput | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    error: str = ""
    config: dict[str, Any] = Field(default_factory=dict)
    settings: VideoSettings = Field(default_factory=VideoSettings)


# (These models are defined above — VideoSettings, Download/Extraction/Copyright/
#  Timeline/Assembly/Thumbnail/Metadata/VideoFactoryOutput/FactoryJob)
