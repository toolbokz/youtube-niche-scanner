'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Progress } from '@/components/ui/progress';
import { EmptyState, Spinner } from '@/components/ui/spinner';
import {
    Factory,
    Play,
    Download,
    FileVideo,
    Image,
    FileText,
    Subtitles,
    Clock,
    CheckCircle2,
    XCircle,
    Loader2,
    Trash2,
    RefreshCw,
    Sparkles,
    Film,
    Mic,
    Palette,
    Tag,
} from 'lucide-react';
import {
    startVideoFactory,
    getVideoFactoryStatus,
    getVideoFactoryJobs,
    cancelVideoFactoryJob,
    getVideoFactoryDownloadUrl,
} from '@/services/api';
import type { VideoFactoryJobStatus, VideoFactoryJobSummary } from '@/types';

// ── Stage display names ───────────────────────────────────────────────────────

const STAGE_LABELS: Record<string, string> = {
    queued: 'Queued',
    generating_concept: 'Generating Concept',
    generating_script: 'Writing Script',
    generating_voiceover: 'Creating Voiceover',
    selecting_clips: 'Selecting Clips',
    extracting_clips: 'Extracting Clips',
    assembling_video: 'Assembling Video',
    generating_subtitles: 'Generating Subtitles',
    generating_thumbnail: 'Creating Thumbnail',
    generating_metadata: 'Generating Metadata',
    rendering: 'Final Render',
    completed: 'Completed',
    failed: 'Failed',
};

const STAGE_ICONS: Record<string, React.ComponentType<{ className?: string; size?: number }>> = {
    generating_concept: Sparkles,
    generating_script: FileText,
    generating_voiceover: Mic,
    selecting_clips: Film,
    assembling_video: FileVideo,
    generating_subtitles: Subtitles,
    generating_thumbnail: Image,
    generating_metadata: Tag,
    rendering: Play,
};

function statusColor(status: string) {
    switch (status) {
        case 'completed': return 'bg-green-500/20 text-green-400 border-green-500/30';
        case 'failed': return 'bg-red-500/20 text-red-400 border-red-500/30';
        case 'queued': return 'bg-gray-500/20 text-gray-400 border-gray-500/30';
        default: return 'bg-blue-500/20 text-blue-400 border-blue-500/30';
    }
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function VideoFactoryPage() {
    const [niche, setNiche] = useState('');
    const [isStarting, setIsStarting] = useState(false);
    const [activeJobId, setActiveJobId] = useState<string | null>(null);
    const [activeJob, setActiveJob] = useState<VideoFactoryJobStatus | null>(null);
    const [jobs, setJobs] = useState<VideoFactoryJobSummary[]>([]);
    const [error, setError] = useState<string | null>(null);
    const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

    // ── Load existing jobs on mount ──────────────────────────────────

    const loadJobs = useCallback(async () => {
        try {
            const result = await getVideoFactoryJobs();
            setJobs(result.jobs);
        } catch { /* ignore */ }
    }, []);

    useEffect(() => {
        loadJobs();
    }, [loadJobs]);

    // ── Poll active job ──────────────────────────────────────────────

    useEffect(() => {
        if (!activeJobId) return;

        const poll = async () => {
            try {
                const status = await getVideoFactoryStatus(activeJobId);
                setActiveJob(status);
                if (status.status === 'completed' || status.status === 'failed') {
                    if (pollRef.current) clearInterval(pollRef.current);
                    loadJobs();
                }
            } catch {
                if (pollRef.current) clearInterval(pollRef.current);
            }
        };

        poll(); // immediate first poll
        pollRef.current = setInterval(poll, 2000);
        return () => {
            if (pollRef.current) clearInterval(pollRef.current);
        };
    }, [activeJobId, loadJobs]);

    // ── Start job ────────────────────────────────────────────────────

    const handleStart = async () => {
        if (!niche.trim()) return;
        setIsStarting(true);
        setError(null);
        setActiveJob(null);

        try {
            const result = await startVideoFactory({ niche: niche.trim() });
            setActiveJobId(result.job_id);
        } catch (err: any) {
            setError(err.message || 'Failed to start video factory');
        } finally {
            setIsStarting(false);
        }
    };

    const handleCancel = async () => {
        if (!activeJobId) return;
        try {
            await cancelVideoFactoryJob(activeJobId);
            setActiveJob(prev => prev ? { ...prev, status: 'failed', error: 'Cancelled' } : null);
            if (pollRef.current) clearInterval(pollRef.current);
        } catch { /* ignore */ }
    };

    const handleViewJob = async (jobId: string) => {
        setActiveJobId(jobId);
    };

    // ── Render ───────────────────────────────────────────────────────

    return (
        <div className="space-y-6">
            {/* Header */}
            <div>
                <h1 className="text-2xl font-bold tracking-tight">Video Factory</h1>
                <p className="text-muted-foreground">
                    Automatically produce ready-to-upload YouTube videos from any niche.
                </p>
            </div>

            {/* Start new job */}
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <Factory className="h-5 w-5" />
                        Generate New Video
                    </CardTitle>
                    <CardDescription>
                        Enter a niche and the system will automatically generate a complete YouTube video
                        with voiceover, subtitles, thumbnail, and publishing metadata.
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="flex gap-3">
                        <Input
                            placeholder="Enter niche (e.g. passive income, AI tools, fitness tips)"
                            value={niche}
                            onChange={(e) => setNiche(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && handleStart()}
                            className="flex-1"
                            disabled={isStarting}
                        />
                        <Button onClick={handleStart} disabled={isStarting || !niche.trim()}>
                            {isStarting ? (
                                <>
                                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                    Starting...
                                </>
                            ) : (
                                <>
                                    <Play className="mr-2 h-4 w-4" />
                                    Generate Video
                                </>
                            )}
                        </Button>
                    </div>
                    {error && (
                        <p className="mt-3 text-sm text-red-400">{error}</p>
                    )}
                </CardContent>
            </Card>

            {/* Active job progress */}
            {activeJob && (
                <Card className="border-primary/30">
                    <CardHeader>
                        <div className="flex items-center justify-between">
                            <CardTitle className="flex items-center gap-2">
                                {activeJob.status === 'completed' ? (
                                    <CheckCircle2 className="h-5 w-5 text-green-400" />
                                ) : activeJob.status === 'failed' ? (
                                    <XCircle className="h-5 w-5 text-red-400" />
                                ) : (
                                    <Loader2 className="h-5 w-5 animate-spin text-blue-400" />
                                )}
                                Job: {activeJob.niche}
                            </CardTitle>
                            <div className="flex items-center gap-2">
                                <Badge className={statusColor(activeJob.status)}>
                                    {activeJob.status}
                                </Badge>
                                {activeJob.status !== 'completed' && activeJob.status !== 'failed' && (
                                    <Button variant="outline" size="sm" onClick={handleCancel}>
                                        Cancel
                                    </Button>
                                )}
                            </div>
                        </div>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        {/* Progress bar */}
                        <div className="space-y-2">
                            <div className="flex items-center justify-between text-sm">
                                <span className="text-muted-foreground">
                                    {STAGE_LABELS[activeJob.current_stage] || activeJob.current_stage}
                                </span>
                                <span className="font-medium">{Math.round(activeJob.progress_pct)}%</span>
                            </div>
                            <Progress value={activeJob.progress_pct} />
                        </div>

                        {/* Stage pipeline visualization */}
                        <div className="flex flex-wrap gap-2">
                            {activeJob.stages_completed.map((stage) => (
                                <Badge key={stage} variant="outline" className="bg-green-500/10 text-green-400 border-green-500/30">
                                    <CheckCircle2 className="mr-1 h-3 w-3" />
                                    {STAGE_LABELS[stage] || stage}
                                </Badge>
                            ))}
                        </div>

                        {/* Error */}
                        {activeJob.error && (
                            <div className="rounded-lg bg-red-500/10 border border-red-500/30 p-3">
                                <p className="text-sm text-red-400">{activeJob.error}</p>
                            </div>
                        )}

                        {/* Concept preview */}
                        {activeJob.concept && (
                            <div className="rounded-lg bg-muted/50 p-4 space-y-2">
                                <h4 className="text-sm font-semibold">Video Concept</h4>
                                <p className="text-lg font-bold">{activeJob.concept.title}</p>
                                <p className="text-sm text-muted-foreground">{activeJob.concept.concept}</p>
                                <p className="text-xs text-muted-foreground">
                                    Target: {activeJob.concept.target_audience}
                                </p>
                            </div>
                        )}

                        {/* Metadata preview */}
                        {activeJob.metadata && (
                            <div className="rounded-lg bg-muted/50 p-4 space-y-2">
                                <h4 className="text-sm font-semibold">YouTube Metadata</h4>
                                <p className="font-medium">{activeJob.metadata.title}</p>
                                <p className="text-sm text-muted-foreground line-clamp-3">
                                    {activeJob.metadata.description}
                                </p>
                                <div className="flex flex-wrap gap-1 mt-2">
                                    {activeJob.metadata.tags.slice(0, 10).map(tag => (
                                        <Badge key={tag} variant="outline" className="text-xs">
                                            {tag}
                                        </Badge>
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* Download buttons */}
                        {activeJob.status === 'completed' && activeJob.output_files && (
                            <div className="space-y-3">
                                <h4 className="text-sm font-semibold">Download Assets</h4>
                                <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                                    <a
                                        href={getVideoFactoryDownloadUrl(activeJob.job_id, 'video')}
                                        className="flex items-center gap-2 rounded-lg border bg-card p-3 text-sm font-medium transition-colors hover:bg-accent"
                                        download
                                    >
                                        <FileVideo className="h-5 w-5 text-blue-400" />
                                        <div>
                                            <div>Video</div>
                                            <div className="text-xs text-muted-foreground">MP4</div>
                                        </div>
                                    </a>
                                    <a
                                        href={getVideoFactoryDownloadUrl(activeJob.job_id, 'thumbnail')}
                                        className="flex items-center gap-2 rounded-lg border bg-card p-3 text-sm font-medium transition-colors hover:bg-accent"
                                        download
                                    >
                                        <Image className="h-5 w-5 text-green-400" />
                                        <div>
                                            <div>Thumbnail</div>
                                            <div className="text-xs text-muted-foreground">PNG</div>
                                        </div>
                                    </a>
                                    <a
                                        href={getVideoFactoryDownloadUrl(activeJob.job_id, 'subtitles')}
                                        className="flex items-center gap-2 rounded-lg border bg-card p-3 text-sm font-medium transition-colors hover:bg-accent"
                                        download
                                    >
                                        <Subtitles className="h-5 w-5 text-yellow-400" />
                                        <div>
                                            <div>Subtitles</div>
                                            <div className="text-xs text-muted-foreground">SRT</div>
                                        </div>
                                    </a>
                                    <a
                                        href={getVideoFactoryDownloadUrl(activeJob.job_id, 'metadata')}
                                        className="flex items-center gap-2 rounded-lg border bg-card p-3 text-sm font-medium transition-colors hover:bg-accent"
                                        download
                                    >
                                        <Tag className="h-5 w-5 text-purple-400" />
                                        <div>
                                            <div>Metadata</div>
                                            <div className="text-xs text-muted-foreground">JSON</div>
                                        </div>
                                    </a>
                                </div>
                            </div>
                        )}
                    </CardContent>
                </Card>
            )}

            {/* Job history */}
            {jobs.length > 0 && (
                <Card>
                    <CardHeader>
                        <div className="flex items-center justify-between">
                            <CardTitle className="flex items-center gap-2">
                                <Clock className="h-5 w-5" />
                                Recent Jobs
                            </CardTitle>
                            <Button variant="outline" size="sm" onClick={loadJobs}>
                                <RefreshCw className="mr-1 h-3 w-3" />
                                Refresh
                            </Button>
                        </div>
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-2">
                            {jobs.map((job) => (
                                <div
                                    key={job.job_id}
                                    className="flex items-center justify-between rounded-lg border bg-card p-3 transition-colors hover:bg-accent/50 cursor-pointer"
                                    onClick={() => handleViewJob(job.job_id)}
                                >
                                    <div className="flex items-center gap-3">
                                        {job.status === 'completed' ? (
                                            <CheckCircle2 className="h-4 w-4 text-green-400" />
                                        ) : job.status === 'failed' ? (
                                            <XCircle className="h-4 w-4 text-red-400" />
                                        ) : (
                                            <Loader2 className="h-4 w-4 animate-spin text-blue-400" />
                                        )}
                                        <div>
                                            <p className="text-sm font-medium">{job.niche}</p>
                                            <p className="text-xs text-muted-foreground">
                                                {STAGE_LABELS[job.current_stage] || job.current_stage}
                                                {job.progress_pct > 0 && job.status !== 'completed' && (
                                                    <> — {Math.round(job.progress_pct)}%</>
                                                )}
                                            </p>
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <Badge className={statusColor(job.status)}>
                                            {job.status}
                                        </Badge>
                                        <span className="text-xs text-muted-foreground">
                                            {new Date(job.created_at).toLocaleString()}
                                        </span>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </CardContent>
                </Card>
            )}

            {/* Empty state */}
            {!activeJob && jobs.length === 0 && (
                <EmptyState
                    icon={Factory}
                    title="No videos yet"
                    description="Enter a niche above and click 'Generate Video' to start your first automated video production."
                />
            )}
        </div>
    );
}
