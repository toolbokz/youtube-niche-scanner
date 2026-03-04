'use client';

import { useState } from 'react';
import { useReports, useReport } from '@/hooks/use-api';
import { getReportDownloadUrl } from '@/services/api';
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { LoadingScreen, EmptyState } from '@/components/ui/spinner';
import {
    FileText,
    Search,
    Download,
    FileJson,
    FileType,
    Calendar,
    ChevronRight,
    ArrowLeft,
    Hash,
} from 'lucide-react';
import { formatTimestamp } from '@/lib/utils';
import { useAppStore } from '@/store/app-store';

export default function ReportsPage() {
    const [search, setSearch] = useState('');
    const [selectedFilename, setSelectedFilename] = useState<string | null>(null);
    const { data: reportsData, isLoading: loadingList } = useReports(search);
    const { data: reportDetail, isLoading: loadingDetail } = useReport(selectedFilename || '');
    const setAnalysisData = useAppStore((s) => s.setAnalysisData);

    if (selectedFilename && reportDetail) {
        const report = reportDetail.report;
        return (
            <div className="space-y-6">
                <div className="flex items-center gap-4">
                    <Button variant="ghost" size="icon" onClick={() => setSelectedFilename(null)}>
                        <ArrowLeft className="h-4 w-4" />
                    </Button>
                    <div>
                        <h1 className="text-3xl font-bold tracking-tight">Report Detail</h1>
                        <p className="text-muted-foreground">{selectedFilename}</p>
                    </div>
                </div>

                {/* Actions */}
                <div className="flex gap-3">
                    <a href={getReportDownloadUrl(selectedFilename, 'json')} target="_blank" rel="noopener">
                        <Button variant="outline" size="sm">
                            <FileJson className="mr-2 h-4 w-4" />
                            Download JSON
                        </Button>
                    </a>
                    <a href={getReportDownloadUrl(selectedFilename, 'markdown')} target="_blank" rel="noopener">
                        <Button variant="outline" size="sm">
                            <FileType className="mr-2 h-4 w-4" />
                            Download Markdown
                        </Button>
                    </a>
                    <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => {
                            if (report) setAnalysisData(report as any);
                        }}
                    >
                        Load into Dashboard
                    </Button>
                </div>

                {/* Report summary */}
                <div className="grid gap-4 sm:grid-cols-3">
                    <Card>
                        <CardContent className="pt-6">
                            <p className="text-sm text-muted-foreground">Seed Keywords</p>
                            <div className="mt-1 flex flex-wrap gap-1">
                                {(report.seed_keywords || []).map((kw: string) => (
                                    <Badge key={kw} variant="outline">{kw}</Badge>
                                ))}
                            </div>
                        </CardContent>
                    </Card>
                    <Card>
                        <CardContent className="pt-6">
                            <p className="text-sm text-muted-foreground">Niches Found</p>
                            <p className="text-2xl font-bold">{(report.top_niches || []).length}</p>
                        </CardContent>
                    </Card>
                    <Card>
                        <CardContent className="pt-6">
                            <p className="text-sm text-muted-foreground">Video Blueprints</p>
                            <p className="text-2xl font-bold">
                                {Object.values(report.video_blueprints || {}).reduce(
                                    (s: number, v: any) => s + (Array.isArray(v) ? v.length : 0),
                                    0
                                )}
                            </p>
                        </CardContent>
                    </Card>
                </div>

                {/* Top niches from report */}
                <Card>
                    <CardHeader>
                        <CardTitle className="text-base">Top Niches in Report</CardTitle>
                    </CardHeader>
                    <CardContent className="p-0">
                        <div className="overflow-x-auto">
                            <table className="w-full text-sm">
                                <thead>
                                    <tr className="border-b bg-muted/50">
                                        <th className="px-4 py-3 text-left font-medium">#</th>
                                        <th className="px-4 py-3 text-left font-medium">Niche</th>
                                        <th className="px-4 py-3 text-left font-medium">Score</th>
                                        <th className="px-4 py-3 text-left font-medium">Demand</th>
                                        <th className="px-4 py-3 text-left font-medium">Virality</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {(report.top_niches || []).map((n: any, i: number) => (
                                        <tr key={i} className="border-b hover:bg-muted/50">
                                            <td className="px-4 py-3 text-muted-foreground">{n.rank || i + 1}</td>
                                            <td className="px-4 py-3 font-medium">{n.niche}</td>
                                            <td className="px-4 py-3">
                                                <Badge variant="success">{n.overall_score?.toFixed(1)}</Badge>
                                            </td>
                                            <td className="px-4 py-3">{n.demand_score?.toFixed(1)}</td>
                                            <td className="px-4 py-3">{n.virality_score?.toFixed(1)}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </CardContent>
                </Card>

                {/* Raw metadata */}
                {report.metadata && (
                    <Card>
                        <CardHeader>
                            <CardTitle className="text-base">Metadata</CardTitle>
                        </CardHeader>
                        <CardContent>
                            <pre className="overflow-x-auto rounded-lg bg-muted p-4 text-xs">
                                {JSON.stringify(report.metadata, null, 2)}
                            </pre>
                        </CardContent>
                    </Card>
                )}
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-3xl font-bold tracking-tight">Reports</h1>
                <p className="text-muted-foreground">Browse and download saved analysis reports.</p>
            </div>

            {/* Search */}
            <div className="relative max-w-md">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                    placeholder="Search reports..."
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    className="pl-9"
                />
            </div>

            {loadingList && <LoadingScreen message="Loading reports..." />}

            {!loadingList && (!reportsData?.reports || reportsData.reports.length === 0) && (
                <EmptyState
                    icon={FileText}
                    title="No reports found"
                    description="Reports are generated when you run analysis. Run a discovery to create your first report."
                />
            )}

            {!loadingList && reportsData?.reports && reportsData.reports.length > 0 && (
                <div className="grid gap-3">
                    {reportsData.reports.map((report) => (
                        <Card
                            key={report.filename}
                            className="cursor-pointer transition-colors hover:bg-muted/50"
                            onClick={() => setSelectedFilename(report.filename)}
                        >
                            <CardContent className="flex items-center justify-between p-4">
                                <div className="flex items-center gap-4">
                                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                                        <FileText className="h-5 w-5 text-primary" />
                                    </div>
                                    <div>
                                        <p className="text-sm font-medium">{report.filename}</p>
                                        <div className="flex items-center gap-3 text-xs text-muted-foreground">
                                            <span className="flex items-center gap-1">
                                                <Calendar className="h-3 w-3" />
                                                {formatTimestamp(report.created)}
                                            </span>
                                            <span className="flex items-center gap-1">
                                                <Hash className="h-3 w-3" />
                                                {report.niche_count} niches
                                            </span>
                                        </div>
                                        <div className="mt-1 flex flex-wrap gap-1">
                                            {report.seed_keywords.slice(0, 5).map((kw) => (
                                                <Badge key={kw} variant="outline" className="text-[10px]">
                                                    {kw}
                                                </Badge>
                                            ))}
                                        </div>
                                    </div>
                                </div>
                                <ChevronRight className="h-4 w-4 text-muted-foreground" />
                            </CardContent>
                        </Card>
                    ))}
                </div>
            )}
        </div>
    );
}
