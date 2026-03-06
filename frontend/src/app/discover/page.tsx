'use client';

import { useState } from 'react';
import dynamic from 'next/dynamic';
import { useAppStore } from '@/store/app-store';
import { useAnalyze, useDiscover, usePersistedNiches, useDiscoveries } from '@/hooks/use-api';
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Spinner, EmptyState } from '@/components/ui/spinner';

const ScoreDistributionChart = dynamic(
    () => import('@/components/charts/score-chart').then((m) => ({ default: m.ScoreDistributionChart })),
    { ssr: false, loading: () => <div className="h-[300px] animate-pulse rounded-lg bg-muted" /> }
);
import {
    Compass,
    Search,
    Rocket,
    Zap,
    X,
    ArrowUpDown,
    ArrowUp,
    ArrowDown,
    ChevronRight,
} from 'lucide-react';
import Link from 'next/link';
import { formatScore } from '@/lib/utils';
import type { NicheScore } from '@/types';

type SortKey = keyof Pick<
    NicheScore,
    | 'overall_score'
    | 'demand_score'
    | 'competition_score'
    | 'trend_momentum'
    | 'virality_score'
    | 'ctr_potential'
    | 'faceless_viability'
>;

const COLUMNS: { key: SortKey; label: string }[] = [
    { key: 'overall_score', label: 'Score' },
    { key: 'demand_score', label: 'Demand' },
    { key: 'competition_score', label: 'Competition' },
    { key: 'trend_momentum', label: 'Trend' },
    { key: 'virality_score', label: 'Virality' },
    { key: 'ctr_potential', label: 'CTR' },
    { key: 'faceless_viability', label: 'Faceless' },
];

export default function DiscoverPage() {
    const analysisData = useAppStore((s) => s.analysisData);
    const analyze = useAnalyze();
    const discover = useDiscover();

    const [seedInput, setSeedInput] = useState('');
    const [seeds, setSeeds] = useState<string[]>([]);
    const [topN, setTopN] = useState(20);
    const [videosPerNiche, setVideosPerNiche] = useState(10);
    const [searchFilter, setSearchFilter] = useState('');
    const [sortKey, setSortKey] = useState<SortKey>('overall_score');
    const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');

    const isLoading = analyze.isPending || discover.isPending;

    // Load persisted niches when no active analysis
    const persistedNichesQuery = usePersistedNiches(100, 0);
    const discoveriesQuery = useDiscoveries(10);

    const addSeed = () => {
        const trimmed = seedInput.trim();
        if (trimmed && !seeds.includes(trimmed)) {
            setSeeds([...seeds, trimmed]);
            setSeedInput('');
        }
    };

    const removeSeed = (s: string) => setSeeds(seeds.filter((x) => x !== s));

    const handleAnalyze = () => {
        if (seeds.length === 0) return;
        analyze.mutate({ seed_keywords: seeds, top_n: topN, videos_per_niche: videosPerNiche });
    };

    const handleDiscover = (deep = false) => {
        discover.mutate({ deep, top_n: topN, videos_per_niche: videosPerNiche });
    };

    const toggleSort = (key: SortKey) => {
        if (sortKey === key) {
            setSortDir(sortDir === 'desc' ? 'asc' : 'desc');
        } else {
            setSortKey(key);
            setSortDir('desc');
        }
    };

    // Filter + sort niches
    const niches = (analysisData?.top_niches || [])
        .filter((n) => n.niche.toLowerCase().includes(searchFilter.toLowerCase()))
        .sort((a, b) => {
            const va = Number(a[sortKey]) || 0;
            const vb = Number(b[sortKey]) || 0;
            return sortDir === 'desc' ? vb - va : va - vb;
        });

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-3xl font-bold tracking-tight">Discover Niches</h1>
                <p className="text-muted-foreground">
                    Find profitable YouTube niches with data-driven analysis.
                </p>
            </div>

            {/* Discovery Controls */}
            <Card>
                <CardHeader className="pb-3">
                    <CardTitle className="text-base">Discovery Controls</CardTitle>
                    <CardDescription>Enter seed keywords or run automatic discovery.</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                    {/* Seed keywords input */}
                    <div className="flex gap-2">
                        <Input
                            placeholder="Enter a seed keyword (e.g. ai tools, passive income)..."
                            value={seedInput}
                            onChange={(e) => setSeedInput(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && addSeed()}
                            disabled={isLoading}
                        />
                        <Button variant="outline" onClick={addSeed} disabled={isLoading || !seedInput.trim()}>
                            Add
                        </Button>
                    </div>

                    {/* Seed tags */}
                    {seeds.length > 0 && (
                        <div className="flex flex-wrap gap-2">
                            {seeds.map((s) => (
                                <Badge key={s} variant="secondary" className="gap-1 pr-1">
                                    {s}
                                    <button onClick={() => removeSeed(s)} className="ml-1 rounded-full hover:bg-accent">
                                        <X className="h-3 w-3" />
                                    </button>
                                </Badge>
                            ))}
                        </div>
                    )}

                    {/* Controls row */}
                    <div className="flex flex-wrap items-center gap-4">
                        <div className="flex items-center gap-2">
                            <label className="text-sm text-muted-foreground">Top niches:</label>
                            <Input
                                type="number"
                                min={1}
                                max={50}
                                value={topN}
                                onChange={(e) => setTopN(Number(e.target.value))}
                                className="w-20"
                                disabled={isLoading}
                            />
                        </div>
                        <div className="flex items-center gap-2">
                            <label className="text-sm text-muted-foreground">Videos/niche:</label>
                            <Input
                                type="number"
                                min={1}
                                max={30}
                                value={videosPerNiche}
                                onChange={(e) => setVideosPerNiche(Number(e.target.value))}
                                className="w-20"
                                disabled={isLoading}
                            />
                        </div>
                    </div>

                    {/* Action buttons */}
                    <div className="flex flex-wrap gap-3">
                        <Button onClick={handleAnalyze} disabled={isLoading || seeds.length === 0}>
                            {isLoading && analyze.isPending ? (
                                <Spinner className="mr-2 h-4 w-4" />
                            ) : (
                                <Search className="mr-2 h-4 w-4" />
                            )}
                            Run Analysis
                        </Button>
                        <Button variant="secondary" onClick={() => handleDiscover(false)} disabled={isLoading}>
                            {isLoading && discover.isPending ? (
                                <Spinner className="mr-2 h-4 w-4" />
                            ) : (
                                <Rocket className="mr-2 h-4 w-4" />
                            )}
                            Auto Discovery
                        </Button>
                        <Button variant="outline" onClick={() => handleDiscover(true)} disabled={isLoading}>
                            <Zap className="mr-2 h-4 w-4" />
                            Deep Discovery
                        </Button>
                    </div>

                    {/* Error */}
                    {(analyze.isError || discover.isError) && (
                        <p className="text-sm text-destructive">
                            {(analyze.error || discover.error)?.message || 'An error occurred'}
                        </p>
                    )}
                </CardContent>
            </Card>

            {/* Loading state */}
            {isLoading && (
                <Card>
                    <CardContent className="flex items-center justify-center py-16">
                        <div className="flex flex-col items-center gap-3">
                            <Spinner size={32} />
                            <p className="text-sm text-muted-foreground">
                                Running pipeline... This may take a few minutes.
                            </p>
                        </div>
                    </CardContent>
                </Card>
            )}

            {/* Results */}
            {!isLoading && niches.length > 0 && (
                <>
                    {/* Search filter */}
                    <div className="flex items-center gap-4">
                        <div className="relative flex-1 max-w-sm">
                            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                            <Input
                                placeholder="Filter niches..."
                                value={searchFilter}
                                onChange={(e) => setSearchFilter(e.target.value)}
                                className="pl-9"
                            />
                        </div>
                        <span className="text-sm text-muted-foreground">{niches.length} niches</span>
                    </div>

                    {/* Niche table */}
                    <Card>
                        <CardContent className="p-0">
                            <div className="overflow-x-auto">
                                <table className="w-full text-sm">
                                    <thead>
                                        <tr className="border-b bg-muted/50">
                                            <th className="px-4 py-3 text-left font-medium">#</th>
                                            <th className="px-4 py-3 text-left font-medium">Niche</th>
                                            {COLUMNS.map((col) => (
                                                <th key={col.key} className="px-4 py-3 text-left font-medium">
                                                    <button
                                                        onClick={() => toggleSort(col.key)}
                                                        className="flex items-center gap-1 hover:text-foreground"
                                                    >
                                                        {col.label}
                                                        {sortKey === col.key ? (
                                                            sortDir === 'desc' ? (
                                                                <ArrowDown className="h-3 w-3" />
                                                            ) : (
                                                                <ArrowUp className="h-3 w-3" />
                                                            )
                                                        ) : (
                                                            <ArrowUpDown className="h-3 w-3 opacity-30" />
                                                        )}
                                                    </button>
                                                </th>
                                            ))}
                                            <th className="px-4 py-3" />
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {niches.map((niche, i) => (
                                            <tr
                                                key={niche.niche}
                                                className="border-b transition-colors hover:bg-muted/50"
                                            >
                                                <td className="px-4 py-3 text-muted-foreground">{niche.rank || i + 1}</td>
                                                <td className="px-4 py-3 font-medium">{niche.niche}</td>
                                                {COLUMNS.map((col) => (
                                                    <td key={col.key} className="px-4 py-3">
                                                        <Badge
                                                            variant={
                                                                Number(niche[col.key]) >= 70
                                                                    ? 'success'
                                                                    : Number(niche[col.key]) >= 50
                                                                        ? 'warning'
                                                                        : 'secondary'
                                                            }
                                                        >
                                                            {formatScore(Number(niche[col.key]) || 0)}
                                                        </Badge>
                                                    </td>
                                                ))}
                                                <td className="px-4 py-3">
                                                    <Link href={`/niches/${encodeURIComponent(niche.niche)}`}>
                                                        <Button variant="ghost" size="icon">
                                                            <ChevronRight className="h-4 w-4" />
                                                        </Button>
                                                    </Link>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </CardContent>
                    </Card>

                    {/* Score distribution chart */}
                    <ScoreDistributionChart niches={niches} />
                </>
            )}

            {!isLoading && !analysisData && (
                <>
                    {/* Show persisted niches from past analysis runs */}
                    {persistedNichesQuery.data && persistedNichesQuery.data.niches.length > 0 ? (
                        <>
                            {/* Past discoveries info */}
                            {discoveriesQuery.data && discoveriesQuery.data.discoveries.length > 0 && (
                                <Card>
                                    <CardHeader className="pb-3">
                                        <CardTitle className="text-base">Past Discoveries</CardTitle>
                                        <CardDescription>
                                            {discoveriesQuery.data.discoveries.length} previous analysis run{discoveriesQuery.data.discoveries.length > 1 ? 's' : ''} found
                                        </CardDescription>
                                    </CardHeader>
                                    <CardContent>
                                        <div className="flex flex-wrap gap-2">
                                            {discoveriesQuery.data.discoveries.slice(0, 5).map((run) => (
                                                <Badge key={run.id} variant="outline" className="text-xs">
                                                    {run.seed_keywords.slice(0, 3).join(', ')}
                                                    {' · '}
                                                    {run.total_niches} niches
                                                    {run.completed_at && (
                                                        <span className="ml-1 text-muted-foreground">
                                                            {new Date(run.completed_at).toLocaleDateString()}
                                                        </span>
                                                    )}
                                                </Badge>
                                            ))}
                                        </div>
                                    </CardContent>
                                </Card>
                            )}

                            {/* Persisted niches table */}
                            <div className="flex items-center gap-4">
                                <div className="relative flex-1 max-w-sm">
                                    <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                                    <Input
                                        placeholder="Filter saved niches..."
                                        value={searchFilter}
                                        onChange={(e) => setSearchFilter(e.target.value)}
                                        className="pl-9"
                                    />
                                </div>
                                <span className="text-sm text-muted-foreground">
                                    {persistedNichesQuery.data.niches.length} saved niches
                                </span>
                            </div>

                            <Card>
                                <CardContent className="p-0">
                                    <div className="overflow-x-auto">
                                        <table className="w-full text-sm">
                                            <thead>
                                                <tr className="border-b bg-muted/50">
                                                    <th className="px-4 py-3 text-left font-medium">#</th>
                                                    <th className="px-4 py-3 text-left font-medium">Niche</th>
                                                    {COLUMNS.map((col) => (
                                                        <th key={col.key} className="px-4 py-3 text-left font-medium">
                                                            {col.label}
                                                        </th>
                                                    ))}
                                                    <th className="px-4 py-3" />
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {persistedNichesQuery.data.niches
                                                    .filter((n) => n.niche.toLowerCase().includes(searchFilter.toLowerCase()))
                                                    .map((niche, i) => (
                                                        <tr key={niche.id} className="border-b transition-colors hover:bg-muted/50">
                                                            <td className="px-4 py-3 text-muted-foreground">{niche.rank || i + 1}</td>
                                                            <td className="px-4 py-3 font-medium">{niche.niche}</td>
                                                            {COLUMNS.map((col) => (
                                                                <td key={col.key} className="px-4 py-3">
                                                                    <Badge
                                                                        variant={
                                                                            Number(niche[col.key]) >= 70
                                                                                ? 'success'
                                                                                : Number(niche[col.key]) >= 50
                                                                                    ? 'warning'
                                                                                    : 'secondary'
                                                                        }
                                                                    >
                                                                        {formatScore(Number(niche[col.key]) || 0)}
                                                                    </Badge>
                                                                </td>
                                                            ))}
                                                            <td className="px-4 py-3">
                                                                <Link href={`/niches/${encodeURIComponent(niche.niche)}`}>
                                                                    <Button variant="ghost" size="icon">
                                                                        <ChevronRight className="h-4 w-4" />
                                                                    </Button>
                                                                </Link>
                                                            </td>
                                                        </tr>
                                                    ))}
                                            </tbody>
                                        </table>
                                    </div>
                                </CardContent>
                            </Card>
                        </>
                    ) : (
                        <EmptyState
                            icon={Compass}
                            title="No results yet"
                            description="Enter seed keywords and run an analysis, or use automatic discovery to find trending niches."
                        />
                    )}
                </>
            )}
        </div>
    );
}
