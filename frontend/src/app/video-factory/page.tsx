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
    Clock,
    CheckCircle2,
    XCircle,
    Loader2,
    RefreshCw,
    Film,
    Scissors,
    Shield,
    Tag,
    Settings,
    Monitor,
    Smartphone,
    Zap,
    AlertTriangle,
    ChevronDown,
    ChevronUp,
} from 'lucide-react';
import {
    startVideoFactory,
    getVideoFactoryStatus,
    getVideoFactoryJobs,
    cancelVideoFactoryJob,
    getVideoFactoryDownloadUrl,
} from '@/services/api';
import type { VideoFactoryJobStatus, VideoFactoryJobSummary, VideoFactoryClip } from '@/types';

// ── Stage display names ───────────────────────────────────────────────────────

const STAGE_LABELS: Record<string, string> = {
    queued: 'Queued',
    fetching_strategy: 'Analyzing Niche',
    downloading_videos: 'Downloading Videos',
    extracting_segments: 'Extracting Clips',
    validating_clips: 'Validating Clips',
    copyright_check: 'Copyright Check',
    building_timeline: 'Building Timeline',
    assembling_video: 'Assembling Video',
    generating_thumbnail: 'Creating Thumbnail',
    generating_metadata: 'Generating Metadata',
    cleaning_temp: 'Cleanup',
    completed: 'Completed',
    failed: 'Failed',
};

const STAGE_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
    fetching_strategy: Zap,
    downloading_videos: Download,
    extracting_segments: Scissors,
    validating_clips: CheckCircle2,
    copyright_check: Shield,
    building_timeline: Film,
    assembling_video: FileVideo,
    generating_thumbnail: Image,
    generating_metadata: Tag,
    cleaning_temp: RefreshCw,
};

function statusColor(status: string) {
    switch (status) {
        case 'completed': return 'bg-green-500/20 text-green-400 border-green-500/30';
        case 'failed': return 'bg-red-500/20 text-red-400 border-red-500/30';
        case 'queued': return 'bg-gray-500/20 text-gray-400 border-gray-500/30';
        default: return 'bg-blue-500/20 text-blue-400 border-blue-500/30';
    }
}

function energyBadge(level: string) {
    switch (level) {
        case 'climax': return 'bg-red-500/20 text-red-400 border-red-500/30';
        case 'high': return 'bg-orange-500/20 text-orange-400 border-orange-500/30';
        case 'medium': return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30';
        case 'low': return 'bg-blue-500/20 text-blue-400 border-blue-500/30';
        default: return 'bg-gray-500/20 text-gray-400 border-gray-500/30';
    }
}

function formatDuration(seconds: number) {
    const m = Math.floor(seconds / 60);
    const s = Math.round(seconds % 60);
    return `${m}:${s.toString().padStart(2, '0')}`;
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

    // Video settings
    const [targetDuration, setTargetDuration] = useState(8);
    const [orientation, setOrientation] = useState<'landscape' | 'portrait'>('landscape');
    const [transitionStyle, setTransitionStyle] = useState<'crossfade' | 'cut' | 'fade'>('crossfade');
    const [showSettings, setShowSettings] = useState(false);

    // ── Load existing jobs on mount ──────────────────────────────────

    const loadJobs = useCallback(async () => {
        try {
            const result = await getVideoFactoryJobs();
            setJobs(result.jobs);
        } catch { /* ignore */ }
    }, []);

    useEffect(() => { loadJobs(); }, [loadJobs]);

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
        poll();
        pollRef.current = setInterval(poll, 2000);
        return () => { if (pollRef.current) clearInterval(pollRef.current); };
    }, [activeJobId, loadJobs]);

    // ── Start job ────────────────────────────────────────────────────

    const handleStart = async () => {
        if (!niche.trim()) return;
        setIsStarting(true);
        setError(null);
        setActiveJob(null);

        try {
            const result = await startVideoFactory({
                niche: niche.trim(),
                target_duration_minutes: targetDuration,
                orientation,
                transition_style: transitionStyle,
            });
            setActiveJobId(result.job_id);
        } catch (err: any) {
            setError(err.message || 'Failed to start compilation pipeline');
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

    const handleViewJob = (jobId: string) => { setActiveJobId(jobId); };

    // ── Render ───────────────────────────────────────────────────────

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-2xl font-bold tracking-tight">Compilation Video Factory</h1>
                <p className="text-muted-foreground">
                    Produce real compilation videos from YouTube source clips — no slides, no filler.
                </p>
            </div>

            {/* Start card with settings */}
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <Factory className="h-5 w-5" /> New Compilation Video
                    </CardTitle>
                    <CardDescription>
                        Enter a niche to discover source videos, extract the best clips,
                        and assemble a compilation video ready for YouTube.
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                    <div className="flex gap-3">
                        <Input
                            placeholder="Enter niche (e.g. funny cats, tech fails, cooking hacks)"
                            value={niche}
                            onChange={e => setNiche(e.target.value)}
                            onKeyDown={e => e.key === 'Enter' && handleStart()}
                            className="flex-1"
                            disabled={isStarting}
                        />
                        <Button onClick={handleStart} disabled={isStarting || !niche.trim()}>
                            {isStarting ? (
                                <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Starting...</>
                            ) : (
                                <><Play className="mr-2 h-4 w-4" /> Make Video</>
                            )}
                        </Button>
                    </div>

                    {/* Settings toggle */}
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setShowSettings(!showSettings)}
                        className="text-muted-foreground"
                    >
                        <Settings className="mr-1 h-4 w-4" />
                        Video Settings
                        {showSettings ? <ChevronUp className="ml-1 h-3 w-3" /> : <ChevronDown className="ml-1 h-3 w-3" />}
                    </Button>

                    {showSettings && (
                        <div className="grid gap-4 sm:grid-cols-3 rounded-lg border p-4">
                            {/* Duration */}
                            <div className="space-y-2">
                                <label className="text-sm font-medium">Target Duration</label>
                                <div className="flex gap-2">
                                    {[3, 5, 8, 10, 15].map(d => (
                                        <Button
                                            key={d}
                                            variant={targetDuration === d ? 'default' : 'outline'}
                                            size="sm"
                                            onClick={() => setTargetDuration(d)}
                                        >
                                            {d}m
                                        </Button>
                                    ))}
                                </div>
                            </div>

                            {/* Orientation */}
                            <div className="space-y-2">
                                <label className="text-sm font-medium">Orientation</label>
                                <div className="flex gap-2">
                                    <Button
                                        variant={orientation === 'landscape' ? 'default' : 'outline'}
                                        size="sm"
                                        onClick={() => setOrientation('landscape')}
                                    >
                                        <Monitor className="mr-1 h-4 w-4" /> 16:9
                                    </Button>
                                    <Button
                                        variant={orientation === 'portrait' ? 'default' : 'outline'}
                                        size="sm"
                                        onClick={() => setOrientation('portrait')}
                                    >
                                        <Smartphone className="mr-1 h-4 w-4" /> 9:16
                                    </Button>
                                </div>
                            </div>

                            {/* Transition */}
                            <div className="space-y-2">
                                <label className="text-sm font-medium">Transitions</label>
                                <div className="flex gap-2">
                                    {(['crossfade', 'cut', 'fade'] as const).map(t => (
                                        <Button
                                            key={t}
                                            variant={transitionStyle === t ? 'default' : 'outline'}
                                            size="sm"
                                            onClick={() => setTransitionStyle(t)}
                                        >
                                            {t.charAt(0).toUpperCase() + t.slice(1)}
                                        </Button>
                                    ))}
                                </div>
                            </div>
                        </div>
                    )}

                    {error && <p className="text-sm text-red-400">{error}</p>}
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
                                {activeJob.niche}
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

                        {/* Stage pipeline */}
                        <div className="flex flex-wrap gap-2">
                            {activeJob.stages_completed.map(stage => {
                                const Icon = STAGE_ICONS[stage];
                                return (
                                    <Badge key={stage} variant="outline" className="bg-green-500/10 text-green-400 border-green-500/30">
                                        {Icon ? <Icon className="mr-1 h-3 w-3" /> : <CheckCircle2 className="mr-1 h-3 w-3" />}
                                        {STAGE_LABELS[stage] || stage}
                                    </Badge>
                                );
                            })}
                        </div>

                        {/* Error */}
                        {activeJob.error && (
                            <div className="rounded-lg bg-red-500/10 border border-red-500/30 p-3">
                                <p className="text-sm text-red-400">{activeJob.error}</p>
                            </div>
                        )}

                        {/* Strategy summary */}
                        {activeJob.strategy && (
                            <div className="rounded-lg bg-muted/50 p-4 space-y-2">
                                <h4 className="text-sm font-semibold flex items-center gap-2">
                                    <Zap className="h-4 w-4 text-yellow-400" /> Compilation Strategy
                                </h4>
                                <p className="text-lg font-bold">{activeJob.strategy.title}</p>
                                <p className="text-sm text-muted-foreground line-clamp-2">
                                    {activeJob.strategy.description}
                                </p>
                                <div className="flex gap-4 text-xs text-muted-foreground">
                                    <span>{activeJob.strategy.source_videos_found} source videos</span>
                                    <span>{activeJob.strategy.segments_recommended} clips</span>
                                    <span>Score: {activeJob.strategy.compilation_score.toFixed(1)}</span>
                                </div>
                            </div>
                        )}

                        {/* Copyright report */}
                        {activeJob.copyright_report && (
                            <div className={`rounded-lg p-4 space-y-2 ${activeJob.copyright_report.is_safe
                                    ? 'bg-green-500/10 border border-green-500/30'
                                    : 'bg-yellow-500/10 border border-yellow-500/30'
                                }`}>
                                <h4 className="text-sm font-semibold flex items-center gap-2">
                                    <Shield className={`h-4 w-4 ${activeJob.copyright_report.is_safe ? 'text-green-400' : 'text-yellow-400'}`} />
                                    Copyright Safety: {activeJob.copyright_report.is_safe ? 'Safe' : 'Warnings'}
                                </h4>
                                <div className="text-xs text-muted-foreground">
                                    {activeJob.copyright_report.unique_sources} unique sources
                                </div>
                                {activeJob.copyright_report.issues.length > 0 && (
                                    <div className="space-y-1 mt-2">
                                        {activeJob.copyright_report.issues.slice(0, 3).map((issue, i) => (
                                            <div key={i} className="flex items-start gap-2 text-xs">
                                                <AlertTriangle className={`h-3 w-3 mt-0.5 shrink-0 ${issue.severity === 'error' ? 'text-red-400' : 'text-yellow-400'
                                                    }`} />
                                                <span>{issue.message}</span>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        )}

                        {/* Clips preview */}
                        {activeJob.clips && activeJob.clips.length > 0 && (
                            <div className="rounded-lg bg-muted/50 p-4 space-y-3">
                                <h4 className="text-sm font-semibold flex items-center gap-2">
                                    <Scissors className="h-4 w-4" />
                                    Extracted Clips ({activeJob.clips.filter(c => c.is_valid).length} valid / {activeJob.clips.length} total)
                                </h4>
                                <div className="space-y-1 max-h-60 overflow-y-auto">
                                    {activeJob.clips.map(clip => (
                                        <div
                                            key={clip.clip_id}
                                            className={`flex items-center justify-between rounded px-3 py-2 text-sm ${clip.is_valid ? 'bg-card' : 'bg-red-500/5 opacity-60'
                                                }`}
                                        >
                                            <div className="flex items-center gap-3">
                                                <span className="text-xs text-muted-foreground w-6">
                                                    #{clip.position + 1}
                                                </span>
                                                <Badge variant="outline" className="text-xs">
                                                    {clip.segment_type.replace(/_/g, ' ')}
                                                </Badge>
                                                <Badge className={`text-xs ${energyBadge(clip.energy_level)}`}>
                                                    {clip.energy_level}
                                                </Badge>
                                            </div>
                                            <div className="flex items-center gap-3">
                                                <span className="text-xs text-muted-foreground">
                                                    {formatDuration(clip.duration_seconds)}
                                                </span>
                                                <span className="text-xs text-muted-foreground truncate max-w-[120px]">
                                                    {clip.source_video_id}
                                                </span>
                                                {clip.is_valid ? (
                                                    <CheckCircle2 className="h-3 w-3 text-green-400" />
                                                ) : (
                                                    <XCircle className="h-3 w-3 text-red-400" />
                                                )}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* Timeline info */}
                        {activeJob.timeline_info && (
                            <div className="rounded-lg bg-muted/50 p-4 space-y-1">
                                <h4 className="text-sm font-semibold flex items-center gap-2">
                                    <Film className="h-4 w-4" /> Timeline
                                </h4>
                                <div className="flex gap-4 text-sm text-muted-foreground">
                                    <span>{activeJob.timeline_info.entries} clips</span>
                                    <span>{formatDuration(activeJob.timeline_info.total_duration)} total</span>
                                    <span>Target: {formatDuration(activeJob.timeline_info.target_duration)}</span>
                                </div>
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
                                <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                                    {[
                                        { file: 'video' as const, icon: FileVideo, label: 'Video', ext: 'MP4', color: 'text-blue-400' },
                                        { file: 'thumbnail' as const, icon: Image, label: 'Thumbnail', ext: 'PNG', color: 'text-green-400' },
                                        { file: 'metadata' as const, icon: Tag, label: 'Metadata', ext: 'JSON', color: 'text-purple-400' },
                                    ].map(({ file, icon: Icon, label, ext, color }) => (
                                        <a
                                            key={file}
                                            href={getVideoFactoryDownloadUrl(activeJob.job_id, file)}
                                            className="flex items-center gap-2 rounded-lg border bg-card p-3 text-sm font-medium transition-colors hover:bg-accent"
                                            download
                                        >
                                            <Icon className={`h-5 w-5 ${color}`} />
                                            <div>
                                                <div>{label}</div>
                                                <div className="text-xs text-muted-foreground">{ext}</div>
                                            </div>
                                        </a>
                                    ))}
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
                                <Clock className="h-5 w-5" /> Recent Jobs
                            </CardTitle>
                            <Button variant="outline" size="sm" onClick={loadJobs}>
                                <RefreshCw className="mr-1 h-3 w-3" /> Refresh
                            </Button>
                        </div>
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-2">
                            {jobs.map(job => (
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
                                        <Badge className={statusColor(job.status)}>{job.status}</Badge>
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

            {!activeJob && jobs.length === 0 && (
                <EmptyState
                    icon={Factory}
                    title="No compilation videos yet"
                    description="Enter a niche above and click 'Make Video' to produce a real compilation video from YouTube source clips."
                />
            )}
        </div>
    );
}
