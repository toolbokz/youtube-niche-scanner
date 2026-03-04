'use client';

import dynamic from 'next/dynamic';
import { useAppStore } from '@/store/app-store';
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { EmptyState } from '@/components/ui/spinner';
import {
    TrendingUp,
    Zap,
    Eye,
    Target,
    Flame,
    BarChart3,
    Compass,
} from 'lucide-react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { formatScore } from '@/lib/utils';

// Lazy-load Recharts bundles — they're ~200KB and only needed after data loads
const ScoreDistributionChart = dynamic(
    () => import('@/components/charts/score-chart').then((m) => ({ default: m.ScoreDistributionChart })),
    { ssr: false, loading: () => <div className="h-[300px] animate-pulse rounded-lg bg-muted" /> }
);

function StatCard({
    title,
    value,
    description,
    icon: Icon,
    trend,
}: {
    title: string;
    value: string;
    description: string;
    icon: React.ComponentType<{ className?: string }>;
    trend?: string;
}) {
    return (
        <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">{title}</CardTitle>
                <Icon className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
                <div className="text-2xl font-bold">{value}</div>
                <p className="text-xs text-muted-foreground">
                    {description}
                    {trend && <span className="ml-1 text-emerald-500">{trend}</span>}
                </p>
            </CardContent>
        </Card>
    );
}

export default function DashboardPage() {
    const analysisData = useAppStore((s) => s.analysisData);

    if (!analysisData) {
        return (
            <div className="space-y-6">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
                    <p className="text-muted-foreground">
                        Your YouTube growth intelligence command center.
                    </p>
                </div>

                <EmptyState
                    icon={Compass}
                    title="No analysis data yet"
                    description="Run a niche discovery or analysis to populate the dashboard with insights."
                >
                    <Link href="/discover">
                        <Button className="mt-4">
                            <Compass className="mr-2 h-4 w-4" />
                            Start Discovery
                        </Button>
                    </Link>
                </EmptyState>
            </div>
        );
    }

    const { top_niches, channel_concepts, viral_opportunities, topic_velocities, metadata } =
        analysisData;

    const topNiche = top_niches[0];
    const totalViralOpps = Object.values(viral_opportunities).reduce(
        (sum, arr) => sum + arr.length,
        0
    );
    const avgScore =
        top_niches.length > 0
            ? top_niches.reduce((s, n) => s + n.overall_score, 0) / top_niches.length
            : 0;

    // Find highest velocity niche
    const velocityEntries = Object.entries(topic_velocities);
    const highestVelocity = velocityEntries.length > 0
        ? velocityEntries.reduce((best, [key, val]) =>
            (val.velocity_score || 0) > (best[1].velocity_score || 0) ? [key, val] : best
        )
        : null;

    return (
        <div className="space-y-6">
            {/* Header */}
            <div>
                <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
                <p className="text-muted-foreground">
                    Analysis complete — {top_niches.length} niches discovered from{' '}
                    {analysisData.seed_keywords.length} seed keywords.
                </p>
            </div>

            {/* Stat cards */}
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                <StatCard
                    title="Top Niches"
                    value={String(top_niches.length)}
                    description="Niches analyzed & ranked"
                    icon={Target}
                />
                <StatCard
                    title="Best Opportunity"
                    value={topNiche ? formatScore(topNiche.overall_score) : '—'}
                    description={topNiche?.niche || 'N/A'}
                    icon={TrendingUp}
                    trend={topNiche ? `#1 ranked` : undefined}
                />
                <StatCard
                    title="Viral Opportunities"
                    value={String(totalViralOpps)}
                    description="Small channels with breakout videos"
                    icon={Flame}
                />
                <StatCard
                    title="Avg Opportunity Score"
                    value={formatScore(avgScore)}
                    description="Across all niches"
                    icon={BarChart3}
                />
            </div>

            {/* Charts row */}
            <div className="grid gap-6 lg:grid-cols-2">
                <ScoreDistributionChart niches={top_niches} />

                {/* Top niches quick list */}
                <Card>
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium">Top Niches Ranked</CardTitle>
                        <CardDescription>Sorted by overall opportunity score</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-3">
                            {top_niches.slice(0, 8).map((niche, i) => (
                                <Link
                                    key={niche.niche}
                                    href={`/niches/${encodeURIComponent(niche.niche)}`}
                                    className="flex items-center justify-between rounded-lg border p-3 transition-colors hover:bg-accent"
                                >
                                    <div className="flex items-center gap-3">
                                        <span className="flex h-7 w-7 items-center justify-center rounded-full bg-primary/10 text-xs font-bold text-primary">
                                            {i + 1}
                                        </span>
                                        <div>
                                            <p className="text-sm font-medium">{niche.niche}</p>
                                            <p className="text-xs text-muted-foreground">
                                                {niche.keywords?.slice(0, 3).join(', ')}
                                            </p>
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <Badge variant={niche.overall_score >= 70 ? 'success' : niche.overall_score >= 50 ? 'warning' : 'secondary'}>
                                            {formatScore(niche.overall_score)}
                                        </Badge>
                                    </div>
                                </Link>
                            ))}
                        </div>
                    </CardContent>
                </Card>
            </div>

            {/* Trending & viral opps row */}
            <div className="grid gap-6 lg:grid-cols-2">
                {/* Highest velocity */}
                <Card>
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium">Trending Topics</CardTitle>
                        <CardDescription>Fastest growing niches by upload velocity</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-3">
                            {velocityEntries.slice(0, 6).map(([name, vel]) => (
                                <div key={name} className="flex items-center justify-between">
                                    <div className="flex items-center gap-2">
                                        {vel.acceleration > 0.2 ? (
                                            <TrendingUp className="h-4 w-4 text-emerald-500" />
                                        ) : (
                                            <BarChart3 className="h-4 w-4 text-muted-foreground" />
                                        )}
                                        <span className="text-sm">{name}</span>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <span className="text-xs text-muted-foreground">
                                            {vel.growth_rate?.toFixed(2)}x growth
                                        </span>
                                        <Badge variant="outline">{vel.velocity_score?.toFixed(0)}</Badge>
                                    </div>
                                </div>
                            ))}
                            {velocityEntries.length === 0 && (
                                <p className="text-sm text-muted-foreground">No velocity data available.</p>
                            )}
                        </div>
                    </CardContent>
                </Card>

                {/* Top viral opportunities */}
                <Card>
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium">Top Viral Opportunities</CardTitle>
                        <CardDescription>Small channels with breakout performance</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-3">
                            {Object.entries(viral_opportunities)
                                .flatMap(([niche, opps]) => opps.map((o) => ({ ...o, niche_name: niche })))
                                .sort((a, b) => b.opportunity_score - a.opportunity_score)
                                .slice(0, 6)
                                .map((opp, i) => (
                                    <div key={i} className="flex items-center justify-between">
                                        <div className="min-w-0 flex-1">
                                            <p className="truncate text-sm font-medium">{opp.channel_name}</p>
                                            <p className="truncate text-xs text-muted-foreground">
                                                {opp.video_title}
                                            </p>
                                        </div>
                                        <div className="ml-3 flex items-center gap-2">
                                            <span className="text-xs text-muted-foreground">
                                                {(opp.video_views / 1000).toFixed(0)}K views
                                            </span>
                                            <Badge variant="success">
                                                <Zap className="mr-1 h-3 w-3" />
                                                {opp.opportunity_score?.toFixed(0)}
                                            </Badge>
                                        </div>
                                    </div>
                                ))}
                            {totalViralOpps === 0 && (
                                <p className="text-sm text-muted-foreground">No viral opportunities detected.</p>
                            )}
                        </div>
                    </CardContent>
                </Card>
            </div>

            {/* Faceless viability leaders */}
            {top_niches.some((n) => n.faceless_viability > 0) && (
                <Card>
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium">Faceless Viability Leaders</CardTitle>
                        <CardDescription>Best niches for faceless content creation</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                            {top_niches
                                .filter((n) => n.faceless_viability > 50)
                                .sort((a, b) => b.faceless_viability - a.faceless_viability)
                                .slice(0, 8)
                                .map((niche) => (
                                    <div
                                        key={niche.niche}
                                        className="flex items-center justify-between rounded-lg border p-3"
                                    >
                                        <span className="text-sm font-medium">{niche.niche}</span>
                                        <Badge variant="success">{formatScore(niche.faceless_viability)}</Badge>
                                    </div>
                                ))}
                        </div>
                    </CardContent>
                </Card>
            )}
        </div>
    );
}
