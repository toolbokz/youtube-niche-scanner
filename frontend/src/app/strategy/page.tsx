'use client';

import { useState } from 'react';
import { useAppStore } from '@/store/app-store';
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { EmptyState } from '@/components/ui/spinner';
import {
    Video,
    ChevronDown,
    ChevronUp,
    Target,
    Clock,
    DollarSign,
    Users,
    Lightbulb,
    FileText,
    Palette,
} from 'lucide-react';
import { formatScore } from '@/lib/utils';

export default function StrategyPage() {
    const analysisData = useAppStore((s) => s.analysisData);
    const [expandedCards, setExpandedCards] = useState<Set<string>>(new Set());

    if (!analysisData) {
        return (
            <div className="space-y-6">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Video Strategy</h1>
                    <p className="text-muted-foreground">AI-powered video strategies for your niches.</p>
                </div>
                <EmptyState
                    icon={Video}
                    title="No strategy data"
                    description="Run a niche analysis to generate video strategies."
                />
            </div>
        );
    }

    const { channel_concepts, video_blueprints } = analysisData;

    const toggleExpand = (id: string) => {
        const next = new Set(expandedCards);
        if (next.has(id)) next.delete(id);
        else next.add(id);
        setExpandedCards(next);
    };

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-3xl font-bold tracking-tight">Video Strategy</h1>
                <p className="text-muted-foreground">
                    Channel concepts and video blueprints for {channel_concepts.length} niches.
                </p>
            </div>

            {/* Channel Concepts */}
            {channel_concepts.map((concept) => (
                <Card key={concept.niche}>
                    <CardHeader>
                        <div className="flex items-center justify-between">
                            <div>
                                <CardTitle className="text-lg">{concept.niche}</CardTitle>
                                <CardDescription>{concept.positioning}</CardDescription>
                            </div>
                            <Badge variant="outline" className="text-base">
                                ${concept.estimated_rpm?.toFixed(2)} RPM
                            </Badge>
                        </div>
                    </CardHeader>
                    <CardContent className="space-y-6">
                        {/* Concept details */}
                        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                            <div className="flex items-start gap-3">
                                <Users className="mt-0.5 h-4 w-4 text-muted-foreground shrink-0" />
                                <div>
                                    <p className="text-xs text-muted-foreground">Target Audience</p>
                                    <p className="text-sm font-medium">{concept.target_audience}</p>
                                </div>
                            </div>
                            <div className="flex items-start gap-3">
                                <Clock className="mt-0.5 h-4 w-4 text-muted-foreground shrink-0" />
                                <div>
                                    <p className="text-xs text-muted-foreground">Posting Cadence</p>
                                    <p className="text-sm font-medium">{concept.posting_cadence}</p>
                                </div>
                            </div>
                            <div className="flex items-start gap-3">
                                <DollarSign className="mt-0.5 h-4 w-4 text-muted-foreground shrink-0" />
                                <div>
                                    <p className="text-xs text-muted-foreground">Estimated RPM</p>
                                    <p className="text-sm font-medium">${concept.estimated_rpm?.toFixed(2)}</p>
                                </div>
                            </div>
                            <div className="flex items-start gap-3">
                                <Target className="mt-0.5 h-4 w-4 text-muted-foreground shrink-0" />
                                <div>
                                    <p className="text-xs text-muted-foreground">Time to Monetization</p>
                                    <p className="text-sm font-medium">{concept.time_to_monetization_months} months</p>
                                </div>
                            </div>
                        </div>

                        {/* Audience persona */}
                        {concept.audience_persona && (
                            <div className="rounded-lg border p-4">
                                <p className="text-sm font-medium mb-2">Audience Persona</p>
                                <div className="grid gap-2 sm:grid-cols-2 text-sm">
                                    <div>
                                        <span className="text-muted-foreground">Age Range: </span>
                                        {concept.audience_persona.age_range}
                                    </div>
                                    <div>
                                        <span className="text-muted-foreground">Platforms: </span>
                                        {concept.audience_persona.platforms?.join(', ')}
                                    </div>
                                    <div>
                                        <span className="text-muted-foreground">Interests: </span>
                                        {concept.audience_persona.interests?.join(', ')}
                                    </div>
                                    <div>
                                        <span className="text-muted-foreground">Pain Points: </span>
                                        {concept.audience_persona.pain_points?.join(', ')}
                                    </div>
                                </div>
                            </div>
                        )}

                        {/* Video ideas */}
                        {video_blueprints[concept.niche] && (
                            <div>
                                <p className="text-sm font-medium mb-3">
                                    Video Ideas ({video_blueprints[concept.niche].length})
                                </p>
                                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                                    {video_blueprints[concept.niche].map((bp, j) => {
                                        const cardId = `${concept.niche}-${j}`;
                                        const isExpanded = expandedCards.has(cardId);

                                        return (
                                            <div
                                                key={j}
                                                className="rounded-lg border p-4 transition-colors hover:bg-muted/50"
                                            >
                                                <div className="flex items-start justify-between gap-2">
                                                    <div className="min-w-0 flex-1">
                                                        <p className="text-sm font-medium leading-tight">{bp.title}</p>
                                                        <p className="mt-1 text-xs text-muted-foreground">{bp.topic}</p>
                                                    </div>
                                                    {bp.ctr_score > 0 && (
                                                        <Badge variant="success" className="shrink-0">
                                                            CTR {formatScore(bp.ctr_score)}
                                                        </Badge>
                                                    )}
                                                </div>

                                                {/* Thumbnail concept */}
                                                {bp.thumbnail_concept && (
                                                    <div className="mt-2 flex items-center gap-2 text-xs text-muted-foreground">
                                                        <Palette className="h-3 w-3" />
                                                        <span>
                                                            {bp.thumbnail_concept.style} · {bp.thumbnail_concept.emotion}
                                                        </span>
                                                    </div>
                                                )}

                                                {/* Expand/collapse */}
                                                <Button
                                                    variant="ghost"
                                                    size="sm"
                                                    className="mt-2 w-full"
                                                    onClick={() => toggleExpand(cardId)}
                                                >
                                                    {isExpanded ? (
                                                        <>
                                                            <ChevronUp className="mr-1 h-3 w-3" /> Less
                                                        </>
                                                    ) : (
                                                        <>
                                                            <ChevronDown className="mr-1 h-3 w-3" /> Details
                                                        </>
                                                    )}
                                                </Button>

                                                {/* Expanded details */}
                                                {isExpanded && (
                                                    <div className="mt-3 space-y-3 border-t pt-3 text-xs">
                                                        {bp.script_structure && (
                                                            <div>
                                                                <p className="font-medium flex items-center gap-1">
                                                                    <FileText className="h-3 w-3" /> Script Structure
                                                                </p>
                                                                <p className="mt-1 text-muted-foreground">
                                                                    Hook: {bp.script_structure.hook}
                                                                </p>
                                                                <p className="text-muted-foreground">
                                                                    Sections: {bp.script_structure.sections?.join(' → ')}
                                                                </p>
                                                            </div>
                                                        )}

                                                        {bp.production_plan && (
                                                            <div>
                                                                <p className="font-medium flex items-center gap-1">
                                                                    <Video className="h-3 w-3" /> Production Plan
                                                                </p>
                                                                <p className="text-muted-foreground">
                                                                    Format: {bp.production_plan.format} ·{' '}
                                                                    {bp.production_plan.estimated_duration_minutes} min ·{' '}
                                                                    {bp.production_plan.editing_complexity} editing
                                                                </p>
                                                            </div>
                                                        )}

                                                        {bp.seo_description && (
                                                            <div>
                                                                <p className="font-medium flex items-center gap-1">
                                                                    <Lightbulb className="h-3 w-3" /> SEO Description
                                                                </p>
                                                                <p className="text-muted-foreground line-clamp-3">
                                                                    {bp.seo_description}
                                                                </p>
                                                            </div>
                                                        )}

                                                        {bp.monetization_strategy && (
                                                            <div>
                                                                <p className="font-medium flex items-center gap-1">
                                                                    <DollarSign className="h-3 w-3" /> Monetization
                                                                </p>
                                                                <p className="text-muted-foreground">
                                                                    Primary: {bp.monetization_strategy.primary_revenue} · RPM: $
                                                                    {bp.monetization_strategy.estimated_rpm?.toFixed(2)}
                                                                </p>
                                                            </div>
                                                        )}

                                                        {bp.target_keywords && bp.target_keywords.length > 0 && (
                                                            <div className="flex flex-wrap gap-1">
                                                                {bp.target_keywords.map((kw) => (
                                                                    <Badge key={kw} variant="outline" className="text-[10px]">
                                                                        {kw}
                                                                    </Badge>
                                                                ))}
                                                            </div>
                                                        )}
                                                    </div>
                                                )}
                                            </div>
                                        );
                                    })}
                                </div>
                            </div>
                        )}
                    </CardContent>
                </Card>
            ))}

            {channel_concepts.length === 0 && (
                <EmptyState
                    icon={Video}
                    title="No channel concepts"
                    description="Channel concepts are generated as part of the analysis pipeline."
                />
            )}
        </div>
    );
}
