"""Core Pydantic models for the Growth Strategist platform."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ── Enums ──────────────────────────────────────────────────────────────────────

class TrendDirection(str, Enum):
    RISING = "rising"
    STABLE = "stable"
    DECLINING = "declining"
    BREAKOUT = "breakout"


class FacelessFormat(str, Enum):
    STOCK_FOOTAGE = "stock_footage"
    BROLL_VOICEOVER = "broll_voiceover"
    ANIMATED_EXPLAINER = "animated_explainer"
    SCREEN_RECORDING = "screen_recording"
    SLIDESHOW = "slideshow"
    DATA_VISUALIZATION = "data_visualization"


# ── Connector Result Models ────────────────────────────────────────────────────

class AutocompleteResult(BaseModel):
    """YouTube / Google autocomplete result."""
    query: str
    suggestions: list[str] = Field(default_factory=list)
    source: str = "youtube"
    collected_at: datetime = Field(default_factory=datetime.utcnow)


class SearchResult(BaseModel):
    """Single YouTube search result."""
    title: str = ""
    channel_name: str = ""
    video_id: str = ""
    view_count: int = 0
    channel_subscribers: int = 0
    duration_seconds: int = 0
    published_date: str = ""
    description: str = ""


class TrendData(BaseModel):
    """Google Trends data for a keyword."""
    keyword: str
    interest_over_time: list[float] = Field(default_factory=list)
    direction: TrendDirection = TrendDirection.STABLE
    momentum_score: float = 50.0
    related_queries: list[str] = Field(default_factory=list)
    source: str = "google_trends"


class RedditSignal(BaseModel):
    """Reddit discussion signal for trend detection."""
    keyword: str = ""
    subreddits: list[str] = Field(default_factory=list)
    post_count_24h: int = 0
    post_count_7d: int = 0
    avg_score: float = 0.0
    avg_comments: float = 0.0
    spike_detected: bool = False


# ── Analysis Models ────────────────────────────────────────────────────────────

class KeywordCluster(BaseModel):
    """A cluster of semantically related keywords."""
    cluster_id: int = 0
    name: str = ""
    keywords: list[str] = Field(default_factory=list)
    seed_keyword: str = ""
    size: int = 0


class CompetitionMetrics(BaseModel):
    """Competition analysis metrics for a niche."""
    niche: str = ""
    avg_views_top20: float = 0.0
    median_views_top20: float = 0.0
    avg_subscriber_count: float = 0.0
    upload_frequency_per_week: float = 0.0
    content_saturation: float = 0.0
    avg_video_age_days: float = 0.0
    production_quality_proxy: float = 0.0
    competition_score: float = 50.0


class ViralityMetrics(BaseModel):
    """Virality prediction metrics for a niche."""
    niche: str = ""
    curiosity_gap: float = 0.0
    emotional_trigger: float = 0.0
    shock_factor: float = 0.0
    information_asymmetry: float = 0.0
    novelty_score: float = 0.0
    relatability: float = 0.0
    virality_probability: float = 0.0


class CTRMetrics(BaseModel):
    """Click-through rate prediction metrics."""
    niche: str = ""
    title_curiosity: float = 0.0
    title_length_score: float = 0.0
    power_words_score: float = 0.0
    numbers_lists_score: float = 0.0
    pattern_interrupt_score: float = 0.0
    visual_concept_score: float = 0.0
    ctr_potential: float = 0.0


class FacelessViability(BaseModel):
    """Faceless content viability assessment."""
    niche: str = ""
    stock_footage_score: float = 0.0
    broll_voiceover_score: float = 0.0
    animated_explainer_score: float = 0.0
    screen_recording_score: float = 0.0
    slideshow_score: float = 0.0
    data_visualization_score: float = 0.0
    best_formats: list[FacelessFormat] = Field(default_factory=list)
    faceless_viability_score: float = 0.0


# ── Scoring & Ranking Models ──────────────────────────────────────────────────

class NicheScore(BaseModel):
    """Composite niche score with all ranking dimensions."""
    niche: str
    demand_score: float = 0.0
    competition_score: float = 0.0
    trend_momentum: float = 0.0
    virality_score: float = 0.0
    ctr_potential: float = 0.0
    faceless_viability: float = 0.0
    viral_opportunity_score: float = 0.0
    topic_velocity_score: float = 0.0
    overall_score: float = 0.0
    rank: int = 0
    keywords: list[str] = Field(default_factory=list)


# ── Strategy & Blueprint Models ───────────────────────────────────────────────

class VideoIdea(BaseModel):
    """A single video idea with metadata."""
    title: str = ""
    topic: str = ""
    angle: str = ""
    target_keywords: list[str] = Field(default_factory=list)
    estimated_views: str = ""
    difficulty: str = "medium"


class ThumbnailConcept(BaseModel):
    """Thumbnail design concept."""
    emotion_trigger: str = ""
    contrast_strategy: str = ""
    visual_focal_point: str = ""
    text_overlay: str = ""
    color_palette: list[str] = Field(default_factory=list)
    layout_concept: str = ""


class ScriptStructure(BaseModel):
    """Video script structure outline."""
    hook: str = ""
    retention_pattern_interrupt: str = ""
    story_progression: str = ""
    mid_video_curiosity_loop: str = ""
    final_payoff: str = ""
    cta_placement: str = ""


class ProductionPlan(BaseModel):
    """Visual production plan for a video."""
    stock_footage_sources: list[str] = Field(default_factory=list)
    motion_graphics_ideas: list[str] = Field(default_factory=list)
    animation_suggestions: list[str] = Field(default_factory=list)
    on_screen_text_strategies: list[str] = Field(default_factory=list)
    editing_rhythm: str = ""


class LowCostProduction(BaseModel):
    """Low-cost production methods and tools."""
    stock_footage_libraries: list[str] = Field(default_factory=list)
    creative_commons_sources: list[str] = Field(default_factory=list)
    public_domain_sources: list[str] = Field(default_factory=list)
    ai_voiceover_tools: list[str] = Field(default_factory=list)
    screen_recording_tools: list[str] = Field(default_factory=list)
    animation_tools: list[str] = Field(default_factory=list)
    estimated_cost_per_video: str = ""


class SEODescription(BaseModel):
    """SEO-optimized YouTube video description."""
    intro_paragraph: str = ""
    keyword_block: list[str] = Field(default_factory=list)
    chapters: list[str] = Field(default_factory=list)
    cta_structure: str = ""
    affiliate_positioning: str = ""


class MonetizationStrategy(BaseModel):
    """Monetization strategy for a niche."""
    affiliate_products: list[str] = Field(default_factory=list)
    sponsorship_categories: list[str] = Field(default_factory=list)
    digital_products: list[str] = Field(default_factory=list)
    lead_magnets: list[str] = Field(default_factory=list)
    expansion_strategy: str = ""


class VideoBlueprint(BaseModel):
    """Complete video production blueprint."""
    video_idea: VideoIdea = Field(default_factory=VideoIdea)
    title_formulas: list[str] = Field(default_factory=list)
    curiosity_gap_headline: str = ""
    keyword_optimized_title: str = ""
    alternative_titles: list[str] = Field(default_factory=list)
    thumbnail: ThumbnailConcept = Field(default_factory=ThumbnailConcept)
    script_structure: ScriptStructure = Field(default_factory=ScriptStructure)
    production_plan: ProductionPlan = Field(default_factory=ProductionPlan)
    low_cost_production: LowCostProduction = Field(default_factory=LowCostProduction)
    seo_description: SEODescription = Field(default_factory=SEODescription)
    monetization: MonetizationStrategy = Field(default_factory=MonetizationStrategy)


# ── Channel & Audience Models ─────────────────────────────────────────────────

class AudiencePersona(BaseModel):
    """Target audience persona for a channel."""
    age_range: str = ""
    interests: list[str] = Field(default_factory=list)
    pain_points: list[str] = Field(default_factory=list)
    content_preferences: list[str] = Field(default_factory=list)


class ChannelConcept(BaseModel):
    """Complete channel concept for a niche."""
    niche: str = ""
    channel_name_ideas: list[str] = Field(default_factory=list)
    positioning: str = ""
    audience: AudiencePersona | None = None
    posting_cadence: str = ""
    estimated_rpm: float = 0.0
    time_to_monetization_months: int = 0


# ── Report Model ──────────────────────────────────────────────────────────────

class NicheReport(BaseModel):
    """Full niche discovery report."""
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    seed_keywords: list[str] = Field(default_factory=list)
    top_niches: list[NicheScore] = Field(default_factory=list)
    channel_concepts: list[ChannelConcept] = Field(default_factory=list)
    video_blueprints: dict[str, list[VideoBlueprint]] = Field(default_factory=dict)
    viral_opportunities: dict[str, list["ViralOpportunity"]] = Field(default_factory=dict)
    topic_velocities: dict[str, "TopicVelocityResult"] = Field(default_factory=dict)
    thumbnail_patterns: dict[str, "ThumbnailPatternResult"] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


# ── Viral Opportunity Models ──────────────────────────────────────────────────

class ViralOpportunity(BaseModel):
    """A single viral opportunity — small channel with outsized views."""
    video_title: str = ""
    video_id: str = ""
    channel_name: str = ""
    channel_subscribers: int = 0
    video_views: int = 0
    video_age_days: int = 0
    views_to_sub_ratio: float = 0.0
    opportunity_score: float = 0.0


class ViralOpportunityResult(BaseModel):
    """Aggregated viral opportunity analysis for a niche."""
    niche: str = ""
    opportunities: list[ViralOpportunity] = Field(default_factory=list)
    avg_opportunity_score: float = 0.0
    anomaly_count: int = 0
    viral_opportunity_score: float = 0.0


# ── Topic Velocity Models ─────────────────────────────────────────────────────

class WeeklyUploadVolume(BaseModel):
    """Upload volume for a single week."""
    week_label: str = ""
    upload_count: int = 0


class TopicVelocityResult(BaseModel):
    """Topic velocity analysis showing content growth rate."""
    niche: str = ""
    weekly_volumes: list[WeeklyUploadVolume] = Field(default_factory=list)
    growth_rate: float = 0.0
    acceleration: float = 0.0
    velocity_score: float = 0.0


# ── Thumbnail Pattern Models ──────────────────────────────────────────────────

class ThumbnailSignals(BaseModel):
    """Visual signals extracted from a single thumbnail."""
    video_id: str = ""
    video_title: str = ""
    dominant_colors: list[str] = Field(default_factory=list)
    has_text: bool = False
    text_coverage_pct: float = 0.0
    has_face: bool = False
    contrast_level: float = 0.0
    brightness: float = 0.0
    saturation: float = 0.0
    visual_clutter_score: float = 0.0


class ThumbnailStyleGroup(BaseModel):
    """A cluster of thumbnails sharing similar visual style."""
    group_id: int = 0
    style_label: str = ""
    count: int = 0
    avg_views: float = 0.0
    dominant_colors: list[str] = Field(default_factory=list)
    text_prevalence: float = 0.0
    face_prevalence: float = 0.0
    avg_contrast: float = 0.0


class ThumbnailPatternResult(BaseModel):
    """Complete thumbnail pattern analysis for a niche."""
    niche: str = ""
    total_analyzed: int = 0
    signals: list[ThumbnailSignals] = Field(default_factory=list)
    style_groups: list[ThumbnailStyleGroup] = Field(default_factory=list)
    insight: str = ""
    recommendations: list[str] = Field(default_factory=list)


# ── Discovery Engine Models ───────────────────────────────────────────────────

class DiscoverySource(BaseModel):
    """A single topic discovered from an automatic source."""
    topic: str = ""
    source: str = ""
    score: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)
