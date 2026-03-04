'use client';

import dynamic from 'next/dynamic';
import { useAppStore } from '@/store/app-store';
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

const ThumbnailDonut = dynamic(
    () => import('@/components/charts/thumbnail-donut').then((m) => ({ default: m.ThumbnailDonut })),
    { ssr: false, loading: () => <div className="h-[250px] animate-pulse rounded-lg bg-muted" /> }
);

import { EmptyState } from '@/components/ui/spinner';
import { Image, Palette, Type, Contrast, Smile, Eye } from 'lucide-react';
import { formatScore } from '@/lib/utils';

export default function ThumbnailsPage() {
    const analysisData = useAppStore((s) => s.analysisData);

    if (!analysisData || Object.keys(analysisData.thumbnail_patterns).length === 0) {
        return (
            <div className="space-y-6">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Thumbnail Insights</h1>
                    <p className="text-muted-foreground">Visual analysis of top-performing thumbnails.</p>
                </div>
                <EmptyState
                    icon={Image}
                    title="No thumbnail data"
                    description="Run a niche analysis to generate thumbnail insights."
                />
            </div>
        );
    }

    const patterns = Object.entries(analysisData.thumbnail_patterns);

    // Aggregate stats for insight cards
    const allPatterns = patterns.map(([, p]) => p);
    const avgFaceFreq =
        allPatterns.length > 0
            ? allPatterns.reduce((s, p) => s + (p.face_frequency || 0), 0) / allPatterns.length
            : 0;
    const avgTextUsage =
        allPatterns.length > 0
            ? allPatterns.reduce((s, p) => s + (p.text_usage || 0), 0) / allPatterns.length
            : 0;
    const avgContrast =
        allPatterns.length > 0
            ? allPatterns.reduce((s, p) => s + (p.avg_contrast || 0), 0) / allPatterns.length
            : 0;

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-3xl font-bold tracking-tight">Thumbnail Insights</h1>
                <p className="text-muted-foreground">
                    Visual patterns from {allPatterns.reduce((s, p) => s + (p.total_analyzed || 0), 0)}{' '}
                    thumbnails across {patterns.length} niches.
                </p>
            </div>

            {/* Aggregate stat cards */}
            <div className="grid gap-4 sm:grid-cols-3">
                <Card>
                    <CardContent className="pt-6">
                        <div className="flex items-center gap-3">
                            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                                <Smile className="h-5 w-5 text-primary" />
                            </div>
                            <div>
                                <p className="text-sm text-muted-foreground">Face Frequency</p>
                                <p className="text-2xl font-bold">{(avgFaceFreq * 100).toFixed(0)}%</p>
                            </div>
                        </div>
                    </CardContent>
                </Card>
                <Card>
                    <CardContent className="pt-6">
                        <div className="flex items-center gap-3">
                            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                                <Type className="h-5 w-5 text-primary" />
                            </div>
                            <div>
                                <p className="text-sm text-muted-foreground">Text Usage</p>
                                <p className="text-2xl font-bold">{(avgTextUsage * 100).toFixed(0)}%</p>
                            </div>
                        </div>
                    </CardContent>
                </Card>
                <Card>
                    <CardContent className="pt-6">
                        <div className="flex items-center gap-3">
                            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                                <Contrast className="h-5 w-5 text-primary" />
                            </div>
                            <div>
                                <p className="text-sm text-muted-foreground">Avg Contrast</p>
                                <p className="text-2xl font-bold">{avgContrast.toFixed(1)}</p>
                            </div>
                        </div>
                    </CardContent>
                </Card>
            </div>

            {/* Insight banner */}
            <Card className="border-primary/30 bg-primary/5">
                <CardContent className="py-4">
                    <div className="flex items-start gap-3">
                        <Eye className="mt-0.5 h-5 w-5 text-primary shrink-0" />
                        <div>
                            <p className="text-sm font-medium">Key Insight</p>
                            <p className="text-sm text-muted-foreground">
                                High performing thumbnails frequently use{' '}
                                {avgContrast > 50 ? 'high contrast colors' : 'moderate contrast'} and{' '}
                                {avgTextUsage > 0.5 ? 'prominent text overlays' : 'minimal text'}.{' '}
                                {avgFaceFreq > 0.5
                                    ? 'Face-forward thumbnails dominate across niches.'
                                    : 'Non-face thumbnails perform well in these niches.'}
                            </p>
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* Per-niche breakdown */}
            {patterns.map(([nicheName, pattern]) => {
                const colorData = (pattern.dominant_colors || []).map((c) => ({
                    name: c.color || c.hex,
                    value: Math.round((c.frequency || 0) * 100),
                }));

                const styleData = (pattern.style_groups || []).map((sg) => ({
                    name: sg.style_label,
                    value: sg.count,
                }));

                return (
                    <Card key={nicheName}>
                        <CardHeader>
                            <div className="flex items-center justify-between">
                                <div>
                                    <CardTitle className="text-lg">{nicheName}</CardTitle>
                                    <CardDescription>
                                        {pattern.total_analyzed} thumbnails analyzed
                                    </CardDescription>
                                </div>
                                <div className="flex gap-2">
                                    <Badge variant="outline">
                                        <Smile className="mr-1 h-3 w-3" />
                                        Face: {((pattern.face_frequency || 0) * 100).toFixed(0)}%
                                    </Badge>
                                    <Badge variant="outline">
                                        <Type className="mr-1 h-3 w-3" />
                                        Text: {((pattern.text_usage || 0) * 100).toFixed(0)}%
                                    </Badge>
                                </div>
                            </div>
                        </CardHeader>
                        <CardContent>
                            <div className="grid gap-6 lg:grid-cols-2">
                                {colorData.length > 0 && (
                                    <ThumbnailDonut title="Dominant Colors" data={colorData} />
                                )}
                                {styleData.length > 0 && (
                                    <ThumbnailDonut title="Style Groups" data={styleData} />
                                )}
                            </div>

                            {/* Style group details */}
                            {pattern.style_groups && pattern.style_groups.length > 0 && (
                                <div className="mt-4 space-y-2">
                                    <p className="text-sm font-medium">Style Breakdown</p>
                                    <div className="grid gap-2 sm:grid-cols-2">
                                        {pattern.style_groups.map((sg, i) => (
                                            <div key={i} className="flex items-center justify-between rounded-lg border p-3">
                                                <div>
                                                    <p className="text-sm font-medium">{sg.style_label}</p>
                                                    <p className="text-xs text-muted-foreground">
                                                        {sg.characteristics?.slice(0, 3).join(', ')}
                                                    </p>
                                                </div>
                                                <div className="text-right">
                                                    <p className="text-sm font-medium">{sg.count} videos</p>
                                                    <p className="text-xs text-muted-foreground">
                                                        avg {(sg.avg_views / 1000).toFixed(0)}K views
                                                    </p>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </CardContent>
                    </Card>
                );
            })}
        </div>
    );
}
