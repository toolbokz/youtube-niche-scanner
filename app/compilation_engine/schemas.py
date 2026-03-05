"""Pydantic schemas for the Compilation Video Intelligence engine."""
from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ── Enums ─────────────────────────────────────────────────────────────────────

class SegmentType(str, Enum):
    """Role a segment plays inside the compilation timeline."""
    INTRO_HOOK = "intro_hook"
    REVEAL = "reveal"
    SURPRISE = "surprise"
    EDUCATIONAL = "educational"
    DRAMATIC = "dramatic"
    PAYOFF = "payoff"
    OUTRO_CTA = "outro_cta"
    TRANSITION = "transition"


class EnergyLevel(str, Enum):
    """Pacing energy for a segment."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CLIMAX = "climax"


# ── Source Video ──────────────────────────────────────────────────────────────

class CompilationSourceVideo(BaseModel):
    """A candidate source video suitable for inclusion in a compilation."""
    video_id: str = ""
    title: str = ""
    channel_name: str = ""
    view_count: int = 0
    duration_seconds: int = 0
    published_date: str = ""
    url: str = ""
    engagement_score: float = 0.0
    relevance_score: float = 0.0
    compilation_fit_notes: str = ""


# ── Segment ───────────────────────────────────────────────────────────────────

class CompilationSegment(BaseModel):
    """Recommended clip to extract from a source video."""
    source_video_id: str = ""
    source_video_title: str = ""
    timestamp_start: str = "0:00"
    timestamp_end: str = "0:30"
    duration_seconds: int = 30
    segment_theme: str = ""
    energy_level: EnergyLevel = EnergyLevel.MEDIUM
    why_include: str = ""


# ── Structure Item ────────────────────────────────────────────────────────────

class CompilationStructureItem(BaseModel):
    """One slot in the compiled video timeline."""
    position: int = 0
    segment_type: SegmentType = SegmentType.REVEAL
    segment: CompilationSegment | None = None
    duration_seconds: int = 30
    notes: str = ""


# ── Editing Guidance ──────────────────────────────────────────────────────────

class EditingGuidance(BaseModel):
    """Post-production editing recommendations."""
    transition_style: str = "smooth crossfade"
    text_overlays: list[str] = Field(default_factory=list)
    sound_effects: list[str] = Field(default_factory=list)
    background_music_style: str = ""
    pacing_notes: str = ""
    color_grading_tips: str = ""
    audio_mixing_tips: str = ""


# ── Final Video Concept ──────────────────────────────────────────────────────

class FinalVideoConcept(BaseModel):
    """The finished compilation video concept."""
    title: str = ""
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    target_audience: str = ""
    emotional_hook: str = ""
    watch_time_strategy: str = ""
    estimated_duration_minutes: float = 10.0
    thumbnail_idea: str = ""


# ── Top-level Compilation Strategy ────────────────────────────────────────────

class CompilationStrategy(BaseModel):
    """Complete compilation video strategy for a niche."""
    niche: str = ""
    source_videos: list[CompilationSourceVideo] = Field(default_factory=list)
    recommended_segments: list[CompilationSegment] = Field(default_factory=list)
    video_structure: list[CompilationStructureItem] = Field(default_factory=list)
    editing_guidance: EditingGuidance = Field(default_factory=EditingGuidance)
    final_video_concept: FinalVideoConcept = Field(default_factory=FinalVideoConcept)
    ai_refinements: dict[str, Any] = Field(default_factory=dict)
    compilation_score: float = 0.0
    total_source_videos_found: int = 0
