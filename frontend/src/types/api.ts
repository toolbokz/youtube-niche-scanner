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

// ── Compilation Video Intelligence ────────────────────────────────────────────

export interface CompilationSourceVideo {
    video_id: string;
    title: string;
    channel_name: string;
    view_count: number;
    duration_seconds: number;
    published_date: string;
    url: string;
    engagement_score: number;
    relevance_score: number;
    compilation_fit_notes: string;
}

export interface CompilationSegment {
    source_video_id: string;
    source_video_title: string;
    timestamp_start: string;
    timestamp_end: string;
    duration_seconds: number;
    segment_theme: string;
    energy_level: 'low' | 'medium' | 'high' | 'climax';
    why_include: string;
}

export interface CompilationStructureItem {
    position: number;
    segment_type: 'intro_hook' | 'reveal' | 'surprise' | 'educational' | 'dramatic' | 'payoff' | 'outro_cta' | 'transition';
    segment: CompilationSegment | null;
    duration_seconds: number;
    notes: string;
}

export interface EditingGuidance {
    transition_style: string;
    text_overlays: string[];
    sound_effects: string[];
    background_music_style: string;
    pacing_notes: string;
    color_grading_tips: string;
    audio_mixing_tips: string;
}

export interface FinalVideoConcept {
    title: string;
    description: string;
    tags: string[];
    target_audience: string;
    emotional_hook: string;
    watch_time_strategy: string;
    estimated_duration_minutes: number;
    thumbnail_idea: string;
}

export interface CompilationStrategy {
    niche: string;
    source_videos: CompilationSourceVideo[];
    recommended_segments: CompilationSegment[];
    video_structure: CompilationStructureItem[];
    editing_guidance: EditingGuidance;
    final_video_concept: FinalVideoConcept;
    ai_refinements: Record<string, unknown>;
    compilation_score: number;
    total_source_videos_found: number;
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

// ── Video Factory Types ───────────────────────────────────────────────────────

export interface VideoFactoryStartRequest {
    niche: string;
    target_duration_minutes?: number;
    orientation?: 'landscape' | 'portrait';
    transition_style?: 'crossfade' | 'cut' | 'fade';
    use_gpu?: boolean;
    copyright_strict?: boolean;
    enable_voiceover?: boolean;
    enable_subtitles?: boolean;
    enable_thumbnail?: boolean;
    enable_background_music?: boolean;
    enable_transitions?: boolean;
}

export interface VideoFactoryStartResponse {
    status: string;
    job_id: string;
    niche: string;
    message: string;
    settings?: Record<string, unknown>;
}

export interface VideoFactoryClip {
    clip_id: string;
    source_video_id: string;
    duration_seconds: number;
    segment_type: string;
    energy_level: string;
    position: number;
    is_valid: boolean;
}

export interface VideoFactoryJobStatus {
    job_id: string;
    niche: string;
    status: string;
    progress_pct: number;
    current_stage: string;
    stages_completed: string[];
    error: string;
    created_at: string;
    updated_at: string;
    completed_at: string | null;
    output_files: {
        video: string;
        thumbnail: string;
        metadata: string;
    } | null;
    clips: VideoFactoryClip[] | null;
    strategy: {
        niche: string;
        source_videos_found: number;
        segments_recommended: number;
        compilation_score: number;
        title: string;
        description: string;
    } | null;
    metadata: {
        title: string;
        description: string;
        tags: string[];
        hashtags: string[];
    } | null;
    copyright_report: {
        is_safe: boolean;
        issues: Array<{
            severity: string;
            message: string;
            recommendation: string;
        }>;
        unique_sources: number;
    } | null;
    timeline_info: {
        entries: number;
        total_duration: number;
        target_duration: number;
    } | null;
    settings: {
        target_duration_minutes: number;
        orientation: string;
        transition_style: string;
        enable_voiceover: boolean;
        enable_subtitles: boolean;
        enable_thumbnail: boolean;
        enable_background_music: boolean;
        enable_transitions: boolean;
    } | null;
}

export interface VideoFactoryPreview {
    job_id: string;
    niche: string;
    status: 'ready' | 'unavailable';
    stream_url: string | null;
    download_url: string | null;
    thumbnail_url: string | null;
    video_size_mb: number;
    metadata: {
        title: string;
        description: string;
        tags: string[];
        hashtags: string[];
    } | null;
    timeline_info: {
        entries: number;
        total_duration: number;
        target_duration: number;
    } | null;
    clips_used: number;
    copyright_safe: boolean;
    settings: Record<string, unknown> | null;
    created_at: string;
    completed_at: string | null;
}

export interface VideoFactoryJobSummary {
    job_id: string;
    niche: string;
    status: string;
    progress_pct: number;
    current_stage: string;
    created_at: string;
    error: string;
}

// ═══════════════════════════════════════════════════════════════════════════════
//  Video Editor Types
// ═══════════════════════════════════════════════════════════════════════════════

export interface EditorClip {
    clip_id: string;
    source_video_id: string;
    source_file_path: string;
    start_seconds: number;
    end_seconds: number;
    duration_seconds: number;
    position: number;
    segment_type: string;
    energy_level: string;
    label: string;
    trim_start: number | null;
    trim_end: number | null;
    is_valid?: boolean;
    width?: number;
    height?: number;
    file_size_mb?: number;
}

export interface EditorTransition {
    type: 'cut' | 'fade' | 'crossdissolve' | 'zoom';
    duration_seconds: number;
    after_clip_index: number;
}

export interface EditorMarker {
    id: string;
    timestamp: number;
    label: string;
    marker_type: 'note' | 'transition' | 'text' | 'sfx';
    color: string;
}

export interface EditorTextOverlay {
    id: string;
    text: string;
    start_seconds: number;
    end_seconds: number;
    font_size: number;
    color: string;
    position: 'top' | 'center' | 'bottom' | 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right';
    background_opacity: number;
}

export interface EditorTimeline {
    clips: EditorClip[];
    transitions: EditorTransition[];
    markers: EditorMarker[];
    text_overlays: EditorTextOverlay[];
    orientation: 'horizontal' | 'vertical';
    resolution: '720p' | '1080p' | '1440p' | '4k';
    target_duration_seconds: number;
    max_scene_duration: number | null;
    background_audio: 'none' | 'ambient' | 'energetic';
}

export interface EditorClipsResponse {
    job_id: string;
    niche: string;
    clips: EditorClip[];
    timeline: Array<{
        position: number;
        clip_id: string;
        clip_file_path: string;
        source_video_id: string;
        start_seconds: number;
        end_seconds: number;
        duration_seconds: number;
        segment_type: string;
        energy_level: string;
        transition: string;
    }>;
    total_duration: number;
    settings: Record<string, unknown> | null;
}

export interface EditorRenderRequest {
    job_id: string;
    is_preview: boolean;
    clips: EditorClip[];
    transitions: EditorTransition[];
    markers: EditorMarker[];
    text_overlays: EditorTextOverlay[];
    orientation: string;
    resolution: string;
    target_duration_seconds: number;
    max_scene_duration: number | null;
    background_audio: string;
}

export interface EditorRenderResponse {
    render_id: string;
    job_id: string;
    type: 'preview' | 'final';
    status: string;
}

export interface EditorRenderStatus {
    render_id: string;
    job_id: string;
    type: string;
    status: 'queued' | 'rendering' | 'completed' | 'failed';
    progress_pct: number;
    output_path: string | null;
    error: string | null;
}

export interface EditorTimelineSaveResponse {
    status: string;
    job_id: string;
    clips_count: number;
    file: string;
}

export interface EditorTimelineLoadResponse {
    job_id: string;
    found: boolean;
    timeline: EditorTimeline | null;
}

// ═══════════════════════════════════════════════════════════════════════════════
//  Persistence / History Types
// ═══════════════════════════════════════════════════════════════════════════════

export interface DiscoveryRun {
    id: number;
    seed_keywords: string[];
    status: string;
    total_keywords: number;
    total_niches: number;
    started_at: string | null;
    completed_at: string | null;
    report_path: string | null;
    metadata: Record<string, unknown>;
}

export interface PersistedNiche {
    id: number;
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
    created_at: string | null;
    updated_at: string | null;
}

export interface PersistedVideoIdea {
    id: number;
    niche: string;
    title: string;
    topic: string;
    angle: string;
    target_keywords: string[];
    blueprint: Record<string, unknown>;
    created_at: string | null;
}

export interface PersistedVideoStrategy {
    id: number;
    niche: string;
    keywords: string[];
    strategy: Record<string, unknown>;
    video_count: number;
    created_at: string | null;
}

export interface PersistedCompilationStrategy {
    id: number;
    niche: string;
    keywords: string[];
    strategy: Record<string, unknown>;
    compilation_score: number;
    total_source_videos: number;
    created_at: string | null;
}