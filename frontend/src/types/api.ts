// ── API Types ─────────────────────────────────────────────────────────────────
// These types mirror the Pydantic model_dump(mode="json") output from the
// Python backend (app/core/models.py).  Keep them in sync.

export interface HealthResponse {
    status: string;
    version: string;
}

export interface NicheScore {
    niche: string;
    keywords: string[];
    demand_score: number;
    competition_score: number;
    trend_momentum: number;
    virality_score: number;
    ctr_potential: number;
    faceless_viability: number;
    viral_opportunity_score: number;
    topic_velocity_score: number;
    overall_score: number;
    rank: number;
}

// ── Channel & Audience ────────────────────────────────────────────────────────

export interface AudiencePersona {
    age_range: string;
    interests: string[];
    pain_points: string[];
    content_preferences: string[];
}

export interface ChannelConcept {
    niche: string;
    channel_name_ideas: string[];
    positioning: string;
    audience: AudiencePersona | null;
    posting_cadence: string;
    estimated_rpm: number;
    time_to_monetization_months: number;
}

// ── Video Blueprint (deeply nested) ──────────────────────────────────────────

export interface VideoIdea {
    title: string;
    topic: string;
    angle: string;
    target_keywords: string[];
    estimated_views: string;
    difficulty: string;
}

export interface ThumbnailConcept {
    emotion_trigger: string;
    contrast_strategy: string;
    visual_focal_point: string;
    text_overlay: string;
    color_palette: string[];
    layout_concept: string;
}

export interface ScriptStructure {
    hook: string;
    retention_pattern_interrupt: string;
    story_progression: string;
    mid_video_curiosity_loop: string;
    final_payoff: string;
    cta_placement: string;
}

export interface ProductionPlan {
    stock_footage_sources: string[];
    motion_graphics_ideas: string[];
    animation_suggestions: string[];
    on_screen_text_strategies: string[];
    editing_rhythm: string;
}

export interface LowCostProduction {
    stock_footage_libraries: string[];
    creative_commons_sources: string[];
    public_domain_sources: string[];
    ai_voiceover_tools: string[];
    screen_recording_tools: string[];
    animation_tools: string[];
    estimated_cost_per_video: string;
}

export interface SEODescription {
    intro_paragraph: string;
    keyword_block: string[];
    chapters: string[];
    cta_structure: string;
    affiliate_positioning: string;
}

export interface MonetizationStrategy {
    affiliate_products: string[];
    sponsorship_categories: string[];
    digital_products: string[];
    lead_magnets: string[];
    expansion_strategy: string;
}

export interface VideoBlueprint {
    video_idea: VideoIdea;
    title_formulas: string[];
    curiosity_gap_headline: string;
    keyword_optimized_title: string;
    alternative_titles: string[];
    thumbnail: ThumbnailConcept;
    script_structure: ScriptStructure;
    production_plan: ProductionPlan;
    low_cost_production: LowCostProduction;
    seo_description: SEODescription;
    monetization: MonetizationStrategy;
}

// ── Viral Opportunity ─────────────────────────────────────────────────────────

export interface ViralOpportunity {
    video_title: string;
    video_id: string;
    channel_name: string;
    channel_subscribers: number;
    video_views: number;
    video_age_days: number;
    views_to_sub_ratio: number;
    opportunity_score: number;
}

// ── Topic Velocity ────────────────────────────────────────────────────────────

export interface WeeklyUploadVolume {
    week_label: string;
    upload_count: number;
}

export interface TopicVelocityResult {
    niche: string;
    weekly_volumes: WeeklyUploadVolume[];
    growth_rate: number;
    acceleration: number;
    velocity_score: number;
}

// ── Thumbnail Patterns ────────────────────────────────────────────────────────

export interface ThumbnailSignals {
    video_id: string;
    video_title: string;
    dominant_colors: string[];
    has_text: boolean;
    text_coverage_pct: number;
    has_face: boolean;
    contrast_level: number;
    brightness: number;
    saturation: number;
    visual_clutter_score: number;
}

export interface ThumbnailStyleGroup {
    group_id: number;
    style_label: string;
    count: number;
    avg_views: number;
    dominant_colors: string[];
    text_prevalence: number;
    face_prevalence: number;
    avg_contrast: number;
    characteristics?: string[];
}

export interface ThumbnailPatternResult {
    niche: string;
    total_analyzed: number;
    signals: ThumbnailSignals[];
    style_groups: ThumbnailStyleGroup[];
    insight: string;
    recommendations: string[];
}

// ── API Response Envelope ─────────────────────────────────────────────────────

export interface AnalyzeResponse {
    status: string;
    seed_keywords: string[];
    top_niches: NicheScore[];
    channel_concepts: ChannelConcept[];
    video_blueprints: Record<string, VideoBlueprint[]>;
    viral_opportunities: Record<string, ViralOpportunity[]>;
    topic_velocities: Record<string, TopicVelocityResult>;
    thumbnail_patterns: Record<string, ThumbnailPatternResult>;
    ai_insights: Record<string, unknown>;
    metadata: Record<string, unknown>;
}

export interface ReportSummary {
    filename: string;
    seed_keywords: string[];
    niche_count: number;
    metadata: Record<string, unknown>;
    created: number;
}

export interface ReportDetail {
    status: string;
    report: AnalyzeResponse;
}

export interface AnalyzeRequest {
    seed_keywords: string[];
    top_n?: number;
    videos_per_niche?: number;
}

export interface DiscoverRequest {
    deep?: boolean;
    max_seeds?: number;
    top_n?: number;
    videos_per_niche?: number;
}
