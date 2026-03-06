'use client';

import { useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { EmptyState, Spinner } from '@/components/ui/spinner';
import {
    Film,
    Play,
    Clock,
    Eye,
    Scissors,
    Music,
    Palette,
    ChevronDown,
    ChevronUp,
    Zap,
    Target,
    ExternalLink,
    AlertCircle,
    Factory,
    History,
} from 'lucide-react';
import type { CompilationStrategy, CompilationStructureItem } from '@/types';
import { getCompilationStrategy } from '@/services/api';
import { useCompilationStrategies } from '@/hooks/use-api';
import { formatScore } from '@/lib/utils';

// ── Helpers ───────────────────────────────────────────────────────────────────

function energyColor(level: string) {
    switch (level) {
        case 'climax': return 'bg-red-500';
        case 'high': return 'bg-orange-500';
        case 'medium': return 'bg-yellow-500';
        case 'low': return 'bg-blue-400';
        default: return 'bg-gray-400';
    }
}

function segmentTypeLabel(type: string) {
    return type.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

function formatViews(n: number) {
    if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
    if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
    return String(n);
}

// ── Page Component ────────────────────────────────────────────────────────────

export default function CompilationPage() {
    const router = useRouter();
    const [niche, setNiche] = useState('');
    const [strategy, setStrategy] = useState<CompilationStrategy | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(['timeline', 'sources']));
    const pastCompilations = useCompilationStrategies('', 20);

    const toggleSection = useCallback((id: string) => {
        setExpandedSections(prev => {
            const next = new Set(prev);
            if (next.has(id)) next.delete(id);
            else next.add(id);
            return next;
        });
    }, []);

    const handleAnalyze = useCallback(async () => {
        if (!niche.trim()) return;
        setLoading(true);
        setError(null);
        try {
            const res = await getCompilationStrategy(niche.trim());
            setStrategy(res.compilation_strategy);
        } catch (e: unknown) {
            setError(e instanceof Error ? e.message : 'Failed to generate compilation strategy');
        } finally {
            setLoading(false);
        }
    }, [niche]);

    return (
        <div className="space-y-6">
            {/* Header */}
            <div>
                <h1 className="text-3xl font-bold tracking-tight">Compilation Intelligence</h1>
                <p className="text-muted-foreground">
                    Discover the best source videos, clip segments, and editing strategy for compilation videos.
                </p>
            </div>

            {/* Search */}
            <Card>
                <CardContent className="pt-6">
                    <div className="flex gap-3">
                        <input
                            type="text"
                            value={niche}
                            onChange={e => setNiche(e.target.value)}
                            onKeyDown={e => e.key === 'Enter' && handleAnalyze()}
                            placeholder="Enter a niche (e.g. funny cats, tech fails, cooking hacks)"
                            className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                        />
                        <Button onClick={handleAnalyze} disabled={loading || !niche.trim()}>
                            {loading ? <Spinner className="mr-2 h-4 w-4" /> : <Film className="mr-2 h-4 w-4" />}
                            {loading ? 'Analyzing…' : 'Analyze'}
                        </Button>
                    </div>
                </CardContent>
            </Card>

            {/* Error */}
            {error && (
                <Card className="border-destructive">
                    <CardContent className="flex items-center gap-3 pt-6 text-destructive">
                        <AlertCircle className="h-5 w-5 shrink-0" />
                        <p className="text-sm">{error}</p>
                    </CardContent>
                </Card>
            )}

            {/* Loading */}
            {loading && (
                <div className="flex items-center justify-center py-12">
                    <Spinner className="h-8 w-8" />
                    <span className="ml-3 text-muted-foreground">Discovering source videos and building strategy…</span>
                </div>
            )}

            {/* Empty state */}
            {!loading && !strategy && !error && (
                <EmptyState
                    icon={Film}
                    title="No compilation strategy yet"
                    description="Enter a niche above to generate a compilation video strategy."
                />
            )}

            {/* Results */}
            {strategy && !loading && (
                <>
                    {/* Overview cards */}
                    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                        <Card>
                            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                                <CardTitle className="text-sm font-medium">Compilation Score</CardTitle>
                                <Target className="h-4 w-4 text-muted-foreground" />
                            </CardHeader>
                            <CardContent>
                                <div className="text-2xl font-bold">{formatScore(strategy.compilation_score)}</div>
                                <p className="text-xs text-muted-foreground">Overall quality score</p>
                            </CardContent>
                        </Card>
                        <Card>
                            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                                <CardTitle className="text-sm font-medium">Source Videos</CardTitle>
                                <Play className="h-4 w-4 text-muted-foreground" />
                            </CardHeader>
                            <CardContent>
                                <div className="text-2xl font-bold">{strategy.source_videos.length}</div>
                                <p className="text-xs text-muted-foreground">Found from {strategy.total_source_videos_found} candidates</p>
                            </CardContent>
                        </Card>
                        <Card>
                            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                                <CardTitle className="text-sm font-medium">Segments</CardTitle>
                                <Scissors className="h-4 w-4 text-muted-foreground" />
                            </CardHeader>
                            <CardContent>
                                <div className="text-2xl font-bold">{strategy.recommended_segments.length}</div>
                                <p className="text-xs text-muted-foreground">Recommended clip cuts</p>
                            </CardContent>
                        </Card>
                        <Card>
                            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                                <CardTitle className="text-sm font-medium">Duration</CardTitle>
                                <Clock className="h-4 w-4 text-muted-foreground" />
                            </CardHeader>
                            <CardContent>
                                <div className="text-2xl font-bold">
                                    ~{strategy.final_video_concept.estimated_duration_minutes} min
                                </div>
                                <p className="text-xs text-muted-foreground">Estimated final length</p>
                            </CardContent>
                        </Card>
                    </div>

                    {/* Create Video CTA */}
                    <Card className="border-primary/30 bg-primary/5">
                        <CardContent className="flex items-center justify-between pt-6">
                            <div className="space-y-1">
                                <h3 className="text-lg font-semibold">Ready to create this video?</h3>
                                <p className="text-sm text-muted-foreground">
                                    Use the Video Factory to automatically download clips, assemble, and produce a real compilation video.
                                </p>
                            </div>
                            <Button
                                size="lg"
                                onClick={() => router.push(`/video-factory?niche=${encodeURIComponent(strategy.niche)}`)}
                                className="shrink-0 ml-4"
                            >
                                <Factory className="mr-2 h-5 w-5" /> Create Video
                            </Button>
                        </CardContent>
                    </Card>

                    {/* Final Video Concept */}
                    <Card>
                        <CardHeader>
                            <CardTitle className="text-lg">Final Video Concept</CardTitle>
                            <CardDescription>{strategy.final_video_concept.title}</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <p className="text-sm text-muted-foreground">
                                {strategy.final_video_concept.description}
                            </p>
                            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                                <div>
                                    <p className="text-xs text-muted-foreground">Target Audience</p>
                                    <p className="text-sm font-medium">{strategy.final_video_concept.target_audience}</p>
                                </div>
                                <div>
                                    <p className="text-xs text-muted-foreground">Emotional Hook</p>
                                    <p className="text-sm font-medium">{strategy.final_video_concept.emotional_hook}</p>
                                </div>
                                <div>
                                    <p className="text-xs text-muted-foreground">Watch Time Strategy</p>
                                    <p className="text-sm font-medium">{strategy.final_video_concept.watch_time_strategy}</p>
                                </div>
                            </div>
                            {strategy.final_video_concept.thumbnail_idea && (
                                <div className="rounded-lg border p-3">
                                    <p className="text-xs text-muted-foreground mb-1">Thumbnail Idea</p>
                                    <p className="text-sm">{strategy.final_video_concept.thumbnail_idea}</p>
                                </div>
                            )}
                            {strategy.final_video_concept.tags.length > 0 && (
                                <div className="flex flex-wrap gap-1.5">
                                    {strategy.final_video_concept.tags.map(tag => (
                                        <Badge key={tag} variant="outline" className="text-xs">{tag}</Badge>
                                    ))}
                                </div>
                            )}
                        </CardContent>
                    </Card>

                    {/* Timeline */}
                    <Card>
                        <CardHeader
                            className="cursor-pointer"
                            onClick={() => toggleSection('timeline')}
                        >
                            <div className="flex items-center justify-between">
                                <CardTitle className="text-lg">Video Timeline</CardTitle>
                                {expandedSections.has('timeline') ? (
                                    <ChevronUp className="h-5 w-5 text-muted-foreground" />
                                ) : (
                                    <ChevronDown className="h-5 w-5 text-muted-foreground" />
                                )}
                            </div>
                            <CardDescription>
                                {strategy.video_structure.length} clips arranged by energy arc
                            </CardDescription>
                        </CardHeader>
                        {expandedSections.has('timeline') && (
                            <CardContent>
                                <div className="space-y-2">
                                    {strategy.video_structure.map((item: CompilationStructureItem) => (
                                        <div
                                            key={item.position}
                                            className="flex items-center gap-3 rounded-lg border p-3 transition-colors hover:bg-muted/50"
                                        >
                                            <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-bold text-primary">
                                                {item.position}
                                            </span>
                                            <div
                                                className={`h-3 w-3 shrink-0 rounded-full ${item.segment ? energyColor(item.segment.energy_level) : 'bg-gray-300'
                                                    }`}
                                                title={item.segment?.energy_level || 'empty'}
                                            />
                                            <div className="min-w-0 flex-1">
                                                <div className="flex items-center gap-2">
                                                    <Badge variant="secondary" className="text-[10px]">
                                                        {segmentTypeLabel(item.segment_type)}
                                                    </Badge>
                                                    <span className="text-xs text-muted-foreground">
                                                        {item.duration_seconds}s
                                                    </span>
                                                </div>
                                                {item.segment && (
                                                    <p className="mt-0.5 truncate text-sm text-muted-foreground">
                                                        {item.segment.source_video_title}
                                                        <span className="ml-2 text-xs">
                                                            [{item.segment.timestamp_start} – {item.segment.timestamp_end}]
                                                        </span>
                                                    </p>
                                                )}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </CardContent>
                        )}
                    </Card>

                    {/* Source Videos */}
                    <Card>
                        <CardHeader
                            className="cursor-pointer"
                            onClick={() => toggleSection('sources')}
                        >
                            <div className="flex items-center justify-between">
                                <CardTitle className="text-lg">Source Videos</CardTitle>
                                {expandedSections.has('sources') ? (
                                    <ChevronUp className="h-5 w-5 text-muted-foreground" />
                                ) : (
                                    <ChevronDown className="h-5 w-5 text-muted-foreground" />
                                )}
                            </div>
                            <CardDescription>
                                Top {strategy.source_videos.length} candidate source videos
                            </CardDescription>
                        </CardHeader>
                        {expandedSections.has('sources') && (
                            <CardContent>
                                <div className="space-y-3">
                                    {strategy.source_videos.map((video) => (
                                        <div
                                            key={video.video_id}
                                            className="flex items-start gap-3 rounded-lg border p-3"
                                        >
                                            <div className="min-w-0 flex-1">
                                                <p className="text-sm font-medium leading-tight">
                                                    {video.title}
                                                </p>
                                                <p className="mt-0.5 text-xs text-muted-foreground">
                                                    {video.channel_name}
                                                    {video.published_date ? ` · ${video.published_date}` : ''}
                                                </p>
                                                <div className="mt-1.5 flex flex-wrap items-center gap-3 text-xs">
                                                    <span className="flex items-center gap-1 text-muted-foreground">
                                                        <Eye className="h-3 w-3" />
                                                        {formatViews(video.view_count)}
                                                    </span>
                                                    <span className="flex items-center gap-1 text-muted-foreground">
                                                        <Clock className="h-3 w-3" />
                                                        {Math.round(video.duration_seconds / 60)} min
                                                    </span>
                                                    <span className="flex items-center gap-1 text-muted-foreground">
                                                        <Zap className="h-3 w-3" />
                                                        {video.engagement_score}/100
                                                    </span>
                                                </div>
                                            </div>
                                            {video.url && (
                                                <a
                                                    href={video.url}
                                                    target="_blank"
                                                    rel="noopener noreferrer"
                                                    className="shrink-0 text-muted-foreground hover:text-primary transition-colors"
                                                >
                                                    <ExternalLink className="h-4 w-4" />
                                                </a>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            </CardContent>
                        )}
                    </Card>

                    {/* Editing Guidance */}
                    <Card>
                        <CardHeader
                            className="cursor-pointer"
                            onClick={() => toggleSection('editing')}
                        >
                            <div className="flex items-center justify-between">
                                <CardTitle className="text-lg">Editing Guidance</CardTitle>
                                {expandedSections.has('editing') ? (
                                    <ChevronUp className="h-5 w-5 text-muted-foreground" />
                                ) : (
                                    <ChevronDown className="h-5 w-5 text-muted-foreground" />
                                )}
                            </div>
                        </CardHeader>
                        {expandedSections.has('editing') && (
                            <CardContent className="space-y-4">
                                <div className="grid gap-4 sm:grid-cols-2">
                                    <div className="flex items-start gap-3">
                                        <Scissors className="mt-0.5 h-4 w-4 text-muted-foreground shrink-0" />
                                        <div>
                                            <p className="text-xs text-muted-foreground">Transitions</p>
                                            <p className="text-sm">{strategy.editing_guidance.transition_style}</p>
                                        </div>
                                    </div>
                                    <div className="flex items-start gap-3">
                                        <Music className="mt-0.5 h-4 w-4 text-muted-foreground shrink-0" />
                                        <div>
                                            <p className="text-xs text-muted-foreground">Music Style</p>
                                            <p className="text-sm">{strategy.editing_guidance.background_music_style}</p>
                                        </div>
                                    </div>
                                    <div className="flex items-start gap-3">
                                        <Palette className="mt-0.5 h-4 w-4 text-muted-foreground shrink-0" />
                                        <div>
                                            <p className="text-xs text-muted-foreground">Color Grading</p>
                                            <p className="text-sm">{strategy.editing_guidance.color_grading_tips}</p>
                                        </div>
                                    </div>
                                    <div className="flex items-start gap-3">
                                        <Zap className="mt-0.5 h-4 w-4 text-muted-foreground shrink-0" />
                                        <div>
                                            <p className="text-xs text-muted-foreground">Pacing</p>
                                            <p className="text-sm">{strategy.editing_guidance.pacing_notes}</p>
                                        </div>
                                    </div>
                                </div>
                                {strategy.editing_guidance.text_overlays.length > 0 && (
                                    <div>
                                        <p className="text-xs text-muted-foreground mb-2">Text Overlays</p>
                                        <div className="flex flex-wrap gap-1.5">
                                            {strategy.editing_guidance.text_overlays.map((t, i) => (
                                                <Badge key={i} variant="outline" className="text-xs">{t}</Badge>
                                            ))}
                                        </div>
                                    </div>
                                )}
                                {strategy.editing_guidance.sound_effects.length > 0 && (
                                    <div>
                                        <p className="text-xs text-muted-foreground mb-2">Sound Effects</p>
                                        <div className="flex flex-wrap gap-1.5">
                                            {strategy.editing_guidance.sound_effects.map((s, i) => (
                                                <Badge key={i} variant="outline" className="text-xs">{s}</Badge>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </CardContent>
                        )}
                    </Card>

                    {/* AI Refinements */}
                    {strategy.ai_refinements && Object.keys(strategy.ai_refinements).length > 0 && (
                        <Card>
                            <CardHeader
                                className="cursor-pointer"
                                onClick={() => toggleSection('ai')}
                            >
                                <div className="flex items-center justify-between">
                                    <CardTitle className="text-lg flex items-center gap-2">
                                        AI Refinements
                                        <Badge variant="secondary" className="text-[10px]">Gemini</Badge>
                                    </CardTitle>
                                    {expandedSections.has('ai') ? (
                                        <ChevronUp className="h-5 w-5 text-muted-foreground" />
                                    ) : (
                                        <ChevronDown className="h-5 w-5 text-muted-foreground" />
                                    )}
                                </div>
                            </CardHeader>
                            {expandedSections.has('ai') && (
                                <CardContent className="space-y-3">
                                    {typeof strategy.ai_refinements.pacing_analysis === 'string' ? (
                                        <div>
                                            <p className="text-xs font-medium text-muted-foreground mb-1">Pacing Analysis</p>
                                            <p className="text-sm">{strategy.ai_refinements.pacing_analysis}</p>
                                        </div>
                                    ) : null}
                                    {Array.isArray(strategy.ai_refinements.audience_retention_tips) ? (
                                        <div>
                                            <p className="text-xs font-medium text-muted-foreground mb-1">Audience Retention Tips</p>
                                            <ul className="list-disc list-inside space-y-1 text-sm text-muted-foreground">
                                                {(strategy.ai_refinements.audience_retention_tips as string[]).map((tip: string, i: number) => (
                                                    <li key={i}>{String(tip)}</li>
                                                ))}
                                            </ul>
                                        </div>
                                    ) : null}
                                    {Array.isArray(strategy.ai_refinements.monetization_angles) ? (
                                        <div>
                                            <p className="text-xs font-medium text-muted-foreground mb-1">Monetization Angles</p>
                                            <ul className="list-disc list-inside space-y-1 text-sm text-muted-foreground">
                                                {(strategy.ai_refinements.monetization_angles as string[]).map((angle: string, i: number) => (
                                                    <li key={i}>{String(angle)}</li>
                                                ))}
                                            </ul>
                                        </div>
                                    ) : null}
                                </CardContent>
                            )}
                        </Card>
                    )}
                </>
            )}

            {/* Past compilation strategies */}
            {!strategy && !loading && pastCompilations.data && pastCompilations.data.compilation_strategies.length > 0 && (
                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2 text-base">
                            <History className="h-4 w-4" />
                            Past Compilation Strategies
                        </CardTitle>
                        <CardDescription>
                            {pastCompilations.data.compilation_strategies.length} saved from previous sessions
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-3">
                            {pastCompilations.data.compilation_strategies.map((cs) => (
                                <div
                                    key={cs.id}
                                    className="flex items-center justify-between rounded-lg border p-3 transition-colors hover:bg-muted/50 cursor-pointer"
                                    onClick={() => {
                                        setNiche(cs.niche);
                                        if (cs.strategy) {
                                            setStrategy(cs.strategy as unknown as CompilationStrategy);
                                        }
                                    }}
                                >
                                    <div>
                                        <p className="text-sm font-medium">{cs.niche}</p>
                                        <p className="text-xs text-muted-foreground">
                                            Score: {formatScore(cs.compilation_score)} &middot;
                                            {cs.total_source_videos} sources
                                            {cs.created_at && (
                                                <span className="ml-1">
                                                    &middot; {new Date(cs.created_at).toLocaleDateString()}
                                                </span>
                                            )}
                                        </p>
                                    </div>
                                    <Badge variant={cs.compilation_score >= 70 ? 'success' : cs.compilation_score >= 50 ? 'warning' : 'secondary'}>
                                        {formatScore(cs.compilation_score)}
                                    </Badge>
                                </div>
                            ))}
                        </div>
                    </CardContent>
                </Card>
            )}
        </div>
    );
}
