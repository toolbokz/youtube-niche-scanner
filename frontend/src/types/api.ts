// ── API Types ─────────────────────────────────────────────────────────────────

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

export interface ChannelConcept {
    niche: string;
    positioning: string;
    target_audience: string;
    posting_cadence: string;
    estimated_rpm: number;
    time_to_monetization_months: number;
    audience_persona?: AudiencePersona;
}

export interface AudiencePersona {
    age_range: string;
    interests: string[];
    pain_points: string[];
    platforms: string[];
}

export interface VideoBlueprint {
    title: string;
    topic: string;
    angle: string;
    target_keywords: string[];
    ctr_score: number;
    thumbnail_concept?: ThumbnailConcept;
    script_structure?: ScriptStructure;
    production_plan?: ProductionPlan;
    seo_description?: string;
    monetization_strategy?: MonetizationStrategy;
}

export interface ThumbnailConcept {
    style: string;
    primary_color: string;
    text_overlay: string;
    emotion: string;
    contrast_level: string;
}

export interface ScriptStructure {
    hook: string;
    intro: string;
    sections: string[];
    cta: string;
    outro: string;
}

export interface ProductionPlan {
    format: string;
    estimated_duration_minutes: number;
    equipment_needed: string[];
    editing_complexity: string;
}

export interface MonetizationStrategy {
    primary_revenue: string;
    secondary_revenue: string[];
    estimated_rpm: number;
    affiliate_opportunities: string[];
}

export interface ViralOpportunity {
    channel_name: string;
    channel_subscribers: number;
    video_title: string;
    video_views: number;
    video_id: string;
    upload_date: string;
    opportunity_score: number;
    subscriber_view_ratio: number;
}

export interface TopicVelocityResult {
    niche: string;
    weekly_volumes: WeeklyVolume[];
    growth_rate: number;
    acceleration: number;
    velocity_score: number;
}

export interface WeeklyVolume {
    week: string;
    volume: number;
}

export interface ThumbnailPattern {
    niche: string;
    total_analyzed: number;
    style_groups: ThumbnailStyleGroup[];
    dominant_colors: ColorInfo[];
    face_frequency: number;
    text_usage: number;
    avg_contrast: number;
}

export interface ThumbnailStyleGroup {
    style_label: string;
    count: number;
    avg_views: number;
    characteristics: string[];
}

export interface ColorInfo {
    color: string;
    hex: string;
    frequency: number;
}

export interface AnalyzeResponse {
    status: string;
    seed_keywords: string[];
    top_niches: NicheScore[];
    channel_concepts: ChannelConcept[];
    video_blueprints: Record<string, VideoBlueprint[]>;
    viral_opportunities: Record<string, ViralOpportunity[]>;
    topic_velocities: Record<string, TopicVelocityResult>;
    thumbnail_patterns: Record<string, ThumbnailPattern>;
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
