'use client';

import dynamic from 'next/dynamic';
import { useParams } from 'next/navigation';
import { useAppStore } from '@/store/app-store';
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';

const NicheRadar = dynamic(
    () => import('@/components/charts/niche-radar').then((m) => ({ default: m.NicheRadar })),
    { ssr: false, loading: () => <div className="h-[300px] animate-pulse rounded-lg bg-muted" /> }
);
const VelocityChart = dynamic(
    () => import('@/components/charts/velocity-chart').then((m) => ({ default: m.VelocityChart })),
    { ssr: false, loading: () => <div className="h-[200px] animate-pulse rounded-lg bg-muted" /> }
);

import { EmptyState } from '@/components/ui/spinner';
import { ArrowLeft, Users, Eye, Calendar, Zap, TrendingUp } from 'lucide-react';
import Link from 'next/link';
import { formatScore, formatNumber } from '@/lib/utils';

export default function NicheDetailPage() {
    const params = useParams();
    const nicheId = decodeURIComponent(params.id as string);
    const analysisData = useAppStore((s) => s.analysisData);

    if (!analysisData) {
        return (
            <EmptyState
                icon={TrendingUp}
                title="No analysis data"
                description="Run an analysis first to view niche details."
            >
                <Link href="/discover">
                    <Button className="mt-4">Go to Discovery</Button>
                </Link>
            </EmptyState>
        );
    }

    const niche = analysisData.top_niches.find(
        (n) => n.niche.toLowerCase() === nicheId.toLowerCase()
    );

    if (!niche) {
        return (
            <EmptyState
                icon={TrendingUp}
                title="Niche not found"
                description={`No data found for "${nicheId}".`}
            >
                <Link href="/discover">
                    <Button className="mt-4">Back to Discovery</Button>
                </Link>
            </EmptyState>
        );
    }

    const viralOpps = analysisData.viral_opportunities[niche.niche] || [];
    const velocity = analysisData.topic_velocities[niche.niche];
    const channelConcept = analysisData.channel_concepts.find(
        (c) => c.niche.toLowerCase() === niche.niche.toLowerCase()
    );

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center gap-4">
                <Link href="/discover">
                    <Button variant="ghost" size="icon">
                        <ArrowLeft className="h-4 w-4" />
                    </Button>
                </Link>
                <div>
                    <div className="flex items-center gap-3">
                        <h1 className="text-3xl font-bold tracking-tight">{niche.niche}</h1>
                        <Badge variant="success" className="text-lg px-3 py-1">
                            {formatScore(niche.overall_score)}
                        </Badge>
                    </div>
                    <p className="text-muted-foreground">
                        Rank #{niche.rank} · {niche.keywords?.length || 0} keywords tracked
                    </p>
                </div>
            </div>

            {/* Score cards */}
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                {[
                    { label: 'Demand', value: niche.demand_score },
                    { label: 'Competition', value: niche.competition_score },
                    { label: 'Trend Momentum', value: niche.trend_momentum },
                    { label: 'Virality', value: niche.virality_score },
                    { label: 'CTR Potential', value: niche.ctr_potential },
                    { label: 'Faceless Viability', value: niche.faceless_viability },
                    { label: 'Viral Opportunity', value: niche.viral_opportunity_score },
                    { label: 'Topic Velocity', value: niche.topic_velocity_score },
                ].map((item) => (
                    <Card key={item.label}>
                        <CardContent className="pt-6">
                            <p className="text-sm text-muted-foreground">{item.label}</p>
                            <p className="text-2xl font-bold">{formatScore(item.value || 0)}</p>
                            <div className="mt-1 h-1.5 w-full rounded-full bg-muted">
                                <div
                                    className="h-full rounded-full bg-primary transition-all"
                                    style={{ width: `${Math.min(item.value || 0, 100)}%` }}
                                />
                            </div>
                        </CardContent>
                    </Card>
                ))}
            </div>

            {/* Radar + Velocity charts */}
            <div className="grid gap-6 lg:grid-cols-2">
                <NicheRadar niche={niche} />
                {velocity && <VelocityChart data={velocity} title="Topic Velocity" />}
            </div>

            {/* Channel concept */}
            {channelConcept && (
                <Card>
                    <CardHeader>
                        <CardTitle className="text-base">Channel Concept</CardTitle>
                        <CardDescription>{channelConcept.positioning}</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <div className="grid gap-4 sm:grid-cols-3">
                            <div>
                                <p className="text-sm text-muted-foreground">Target Audience</p>
                                <p className="text-sm font-medium">
                                    {channelConcept.audience?.age_range || 'General'}
                                    {channelConcept.audience?.interests?.length
                                        ? ` · ${channelConcept.audience.interests.slice(0, 2).join(', ')}`
                                        : ''}
                                </p>
                            </div>
                            <div>
                                <p className="text-sm text-muted-foreground">Posting Cadence</p>
                                <p className="text-sm font-medium">{channelConcept.posting_cadence}</p>
                            </div>
                            <div>
                                <p className="text-sm text-muted-foreground">Estimated RPM</p>
                                <p className="text-sm font-medium">${channelConcept.estimated_rpm?.toFixed(2)}</p>
                            </div>
                        </div>
                    </CardContent>
                </Card>
            )}

            {/* Viral opportunities table */}
            {viralOpps.length > 0 && (
                <Card>
                    <CardHeader>
                        <CardTitle className="text-base">Viral Opportunities</CardTitle>
                        <CardDescription>
                            Small channels with breakout videos — {viralOpps.length} detected
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="p-0">
                        <div className="overflow-x-auto">
                            <table className="w-full text-sm">
                                <thead>
                                    <tr className="border-b bg-muted/50">
                                        <th className="px-4 py-3 text-left font-medium">Channel</th>
                                        <th className="px-4 py-3 text-left font-medium">
                                            <Users className="inline mr-1 h-3 w-3" />
                                            Subscribers
                                        </th>
                                        <th className="px-4 py-3 text-left font-medium">Video Title</th>
                                        <th className="px-4 py-3 text-left font-medium">
                                            <Eye className="inline mr-1 h-3 w-3" />
                                            Views
                                        </th>
                                        <th className="px-4 py-3 text-left font-medium">
                                            <Calendar className="inline mr-1 h-3 w-3" />
                                            Age (days)
                                        </th>
                                        <th className="px-4 py-3 text-left font-medium">
                                            <Zap className="inline mr-1 h-3 w-3" />
                                            Score
                                        </th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {viralOpps
                                        .sort((a, b) => b.opportunity_score - a.opportunity_score)
                                        .map((opp, i) => (
                                            <tr key={i} className="border-b transition-colors hover:bg-muted/50">
                                                <td className="px-4 py-3 font-medium">{opp.channel_name}</td>
                                                <td className="px-4 py-3">{formatNumber(opp.channel_subscribers)}</td>
                                                <td className="max-w-xs truncate px-4 py-3">{opp.video_title}</td>
                                                <td className="px-4 py-3">{formatNumber(opp.video_views)}</td>
                                                <td className="px-4 py-3 text-muted-foreground">
                                                    {opp.video_age_days != null ? `${opp.video_age_days}d ago` : '—'}
                                                </td>
                                                <td className="px-4 py-3">
                                                    <Badge variant="success">{opp.opportunity_score?.toFixed(0)}</Badge>
                                                </td>
                                            </tr>
                                        ))}
                                </tbody>
                            </table>
                        </div>
                    </CardContent>
                </Card>
            )}

            {/* Keywords */}
            <Card>
                <CardHeader>
                    <CardTitle className="text-base">Keywords</CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="flex flex-wrap gap-2">
                        {(niche.keywords || []).map((kw) => (
                            <Badge key={kw} variant="outline">
                                {kw}
                            </Badge>
                        ))}
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
