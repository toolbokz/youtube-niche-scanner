"""Video Factory — Pydantic models for the video production pipeline."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ── Job states ─────────────────────────────────────────────────────────────────

class JobStatus(str, Enum):
    QUEUED = "queued"
    GENERATING_CONCEPT = "generating_concept"
    GENERATING_SCRIPT = "generating_script"
    GENERATING_VOICEOVER = "generating_voiceover"
    SELECTING_CLIPS = "selecting_clips"
    EXTRACTING_CLIPS = "extracting_clips"
    ASSEMBLING_VIDEO = "assembling_video"
    GENERATING_SUBTITLES = "generating_subtitles"
    GENERATING_THUMBNAIL = "generating_thumbnail"
    GENERATING_METADATA = "generating_metadata"
    RENDERING = "rendering"
    COMPLETED = "completed"
    FAILED = "failed"


# ── Step 1: Concept ───────────────────────────────────────────────────────────

class VideoConcept(BaseModel):
    """Generated video concept."""
    title: str = ""
    concept: str = ""
    target_audience: str = ""
    engagement_hook: str = ""
    emotional_trigger: str = ""
    video_structure: list[str] = Field(default_factory=list)
    estimated_duration_minutes: int = 8
    niche: str = ""


# ── Step 2: Script ─────────────────────────────────────────────────────────────

class ScriptSection(BaseModel):
    """A single section of the video script."""
    section_type: str = ""          # hook, intro, main_1, main_2, ..., conclusion, cta
    section_title: str = ""
    content: str = ""
    duration_seconds: int = 0
    visual_notes: str = ""          # guidance for clip selection
    transition_note: str = ""


class VideoScript(BaseModel):
    """Complete video script."""
    title: str = ""
    sections: list[ScriptSection] = Field(default_factory=list)
    total_word_count: int = 0
    estimated_duration_seconds: int = 0
    target_audience: str = ""
    tone: str = "engaging"


# ── Step 3: Voiceover ─────────────────────────────────────────────────────────

class VoiceConfig(BaseModel):
    """Voiceover generation configuration."""
    provider: str = "google_tts"      # google_tts | elevenlabs | local
    voice_name: str = "en-US-Neural2-D"
    speaking_rate: float = 1.0
    pitch: float = 0.0
    elevenlabs_voice_id: str = ""
    elevenlabs_api_key: str = ""


class VoiceoverResult(BaseModel):
    """Result from voiceover generation."""
    audio_path: str = ""
    duration_seconds: float = 0.0
    provider: str = ""
    sample_rate: int = 24000
    sections_timestamps: list[dict[str, Any]] = Field(default_factory=list)


# ── Step 4: Clip Selection ─────────────────────────────────────────────────────

class ClipSource(BaseModel):
    """A source clip mapped to a script section."""
    section_index: int = 0
    section_title: str = ""
    source_type: str = ""            # youtube | stock | compilation
    source_url: str = ""
    source_video_id: str = ""
    start_time: float = 0.0
    end_time: float = 0.0
    duration_seconds: float = 0.0
    description: str = ""
    relevance_score: float = 0.0


class ClipSelectionResult(BaseModel):
    """Complete clip selection for the video."""
    clips: list[ClipSource] = Field(default_factory=list)
    total_clips: int = 0
    total_duration_seconds: float = 0.0
    coverage_pct: float = 0.0       # % of script sections covered


# ── Step 5: Timeline ──────────────────────────────────────────────────────────

class TimelineEntry(BaseModel):
    """Single entry in the video timeline."""
    position: int = 0
    entry_type: str = ""             # intro_animation, narration, highlight, cta
    start_time: float = 0.0
    end_time: float = 0.0
    duration_seconds: float = 0.0
    clip_source: ClipSource | None = None
    voiceover_segment: str = ""
    overlay_text: str = ""
    transition: str = "crossfade"


class VideoTimeline(BaseModel):
    """Complete video timeline."""
    entries: list[TimelineEntry] = Field(default_factory=list)
    total_duration_seconds: float = 0.0
    has_intro: bool = False
    has_outro: bool = False


# ── Step 6: Assembly ───────────────────────────────────────────────────────────

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
    embed_subtitles: bool = True
    use_gpu: bool = True


class AssemblyResult(BaseModel):
    """Result from video assembly."""
    draft_video_path: str = ""
    duration_seconds: float = 0.0
    file_size_mb: float = 0.0
    resolution: str = ""
    fps: int = 30


# ── Step 7: Subtitles ─────────────────────────────────────────────────────────

class SubtitleEntry(BaseModel):
    """Single subtitle entry."""
    index: int = 0
    start_time: float = 0.0
    end_time: float = 0.0
    text: str = ""


class SubtitleResult(BaseModel):
    """Result from subtitle generation."""
    srt_path: str = ""
    entries: list[SubtitleEntry] = Field(default_factory=list)
    total_entries: int = 0
    language: str = "en"


# ── Step 8: Thumbnail ─────────────────────────────────────────────────────────

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


# ── Step 9: Metadata ──────────────────────────────────────────────────────────

class VideoMetadata(BaseModel):
    """Complete YouTube publishing metadata."""
    title: str = ""
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    hashtags: list[str] = Field(default_factory=list)
    chapters: list[dict[str, str]] = Field(default_factory=list)   # [{"time": "0:00", "title": "Intro"}]
    category: str = "Education"
    language: str = "en"
    seo_keywords: list[str] = Field(default_factory=list)


# ── Final Output ───────────────────────────────────────────────────────────────

class VideoFactoryOutput(BaseModel):
    """Final output from the video factory pipeline."""
    job_id: str = ""
    niche: str = ""
    concept: VideoConcept = Field(default_factory=VideoConcept)
    script: VideoScript = Field(default_factory=VideoScript)
    voiceover: VoiceoverResult = Field(default_factory=VoiceoverResult)
    clip_selection: ClipSelectionResult = Field(default_factory=ClipSelectionResult)
    timeline: VideoTimeline = Field(default_factory=VideoTimeline)
    assembly: AssemblyResult = Field(default_factory=AssemblyResult)
    subtitles: SubtitleResult = Field(default_factory=SubtitleResult)
    thumbnail: ThumbnailResult = Field(default_factory=ThumbnailResult)
    metadata: VideoMetadata = Field(default_factory=VideoMetadata)
    output_dir: str = ""
    video_path: str = ""
    thumbnail_path: str = ""
    subtitles_path: str = ""
    metadata_path: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    status: JobStatus = JobStatus.QUEUED
    error: str = ""


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
