'use client';

import { useState, useEffect, useCallback, useRef, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
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
    Trash2,
    GripVertical,
    Eye,
    Mic,
    Subtitles,
    Music,
    Wand2,
    RotateCcw,
} from 'lucide-react';
import {
    startVideoFactory,
    getVideoFactoryStatus,
    getVideoFactoryJobs,
    cancelVideoFactoryJob,
    getVideoFactoryDownloadUrl,
    getVideoFactoryStreamUrl,
    deleteVideoFactoryJob,
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

const ALL_STAGES = [
    'fetching_strategy',
    'downloading_videos',
    'extracting_segments',
    'validating_clips',
    'copyright_check',
    'building_timeline',
    'assembling_video',
    'generating_thumbnail',
    'generating_metadata',
    'cleaning_temp',
];

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

// ── View modes ────────────────────────────────────────────────────────────────

type ViewMode = 'create' | 'progress' | 'preview';

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function VideoFactoryPage() {
    return (
        <Suspense fallback={
            <div className="space-y-6">
                <div>
                    <h1 className="text-2xl font-bold tracking-tight">Compilation Video Factory</h1>
                    <p className="text-muted-foreground">Loading...</p>
                </div>
            </div>
        }>
            <VideoFactoryContent />
        </Suspense>
    );
}

function VideoFactoryContent() {
    const searchParams = useSearchParams();

    const [niche, setNiche] = useState('');
    const [isStarting, setIsStarting] = useState(false);
    const [activeJobId, setActiveJobId] = useState<string | null>(null);
    const [activeJob, setActiveJob] = useState<VideoFactoryJobStatus | null>(null);
    const [jobs, setJobs] = useState<VideoFactoryJobSummary[]>([]);
    const [error, setError] = useState<string | null>(null);
    const [viewMode, setViewMode] = useState<ViewMode>('create');
    const [isDeleting, setIsDeleting] = useState(false);
    const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

    // Video settings
    const [targetDuration, setTargetDuration] = useState(8);
    const [orientation, setOrientation] = useState<'landscape' | 'portrait'>('landscape');
    const [transitionStyle, setTransitionStyle] = useState<'crossfade' | 'cut' | 'fade'>('crossfade');
    const [showSettings, setShowSettings] = useState(false);
    const [enableVoiceover, setEnableVoiceover] = useState(false);
    const [enableSubtitles, setEnableSubtitles] = useState(false);
    const [enableThumbnail, setEnableThumbnail] = useState(true);
    const [enableBgMusic, setEnableBgMusic] = useState(false);
    const [enableTransitions, setEnableTransitions] = useState(true);

    // Clip editor state
    const [removedClips, setRemovedClips] = useState<Set<string>>(new Set());

    // ── Read niche from URL query (CI → VF flow) ─────────────────────

    useEffect(() => {
        const nicheParam = searchParams.get('niche');
        if (nicheParam) {
            setNiche(nicheParam);
            setShowSettings(true);
        }
    }, [searchParams]);

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
                if (status.status === 'completed') {
                    if (pollRef.current) clearInterval(pollRef.current);
                    setViewMode('preview');
                    loadJobs();
                } else if (status.status === 'failed') {
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
        setRemovedClips(new Set());

        try {
            const result = await startVideoFactory({
                niche: niche.trim(),
                target_duration_minutes: targetDuration,
                orientation,
                transition_style: transitionStyle,
                enable_voiceover: enableVoiceover,
                enable_subtitles: enableSubtitles,
                enable_thumbnail: enableThumbnail,
                enable_background_music: enableBgMusic,
                enable_transitions: enableTransitions,
            });
            setActiveJobId(result.job_id);
            setViewMode('progress');
        } catch (err: unknown) {
            const message = err instanceof Error ? err.message : 'Failed to start compilation pipeline';
            setError(message);
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

    const handleDelete = async () => {
        if (!activeJobId) return;
        setIsDeleting(true);
        try {
            await deleteVideoFactoryJob(activeJobId);
            setActiveJob(null);
            setActiveJobId(null);
            setViewMode('create');
            loadJobs();
        } catch (err: unknown) {
            const message = err instanceof Error ? err.message : 'Failed to delete job';
            setError(message);
        } finally {
            setIsDeleting(false);
        }
    };

    const handleRebuild = () => {
        if (activeJob) {
            setNiche(activeJob.niche);
        }
        setActiveJob(null);
        setActiveJobId(null);
        setViewMode('create');
        setShowSettings(true);
        setRemovedClips(new Set());
    };

    const handleViewJob = (jobId: string) => {
        setActiveJobId(jobId);
        setRemovedClips(new Set());
    };

    // ── Clip editor actions ──────────────────────────────────────────

    const toggleClipRemoved = (clipId: string) => {
        setRemovedClips(prev => {
            const next = new Set(prev);
            if (next.has(clipId)) next.delete(clipId);
            else next.add(clipId);
            return next;
        });
    };

    const getVisibleClips = (): VideoFactoryClip[] => {
        if (!activeJob?.clips) return [];
        return activeJob.clips.filter(c => !removedClips.has(c.clip_id));
    };

    // ── Render ───────────────────────────────────────────────────────

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-2xl font-bold tracking-tight">Compilation Video Factory</h1>
                <p className="text-muted-foreground">
                    Produce real compilation videos from YouTube source clips — no slides, no filler.
                </p>
            </div>

            {/* ═══ CREATE VIEW ═══ */}
            {viewMode === 'create' && (
                <>
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
                                <div className="rounded-lg border p-4 space-y-5">
                                    {/* Row 1: Duration, Orientation, Transitions */}
                                    <div className="grid gap-4 sm:grid-cols-3">
                                        {/* Duration */}
                                        <div className="space-y-2">
                                            <label className="text-sm font-medium flex items-center gap-1.5">
                                                <Clock className="h-3.5 w-3.5 text-muted-foreground" /> Target Duration
                                            </label>
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
                                            <label className="text-sm font-medium flex items-center gap-1.5">
                                                <Monitor className="h-3.5 w-3.5 text-muted-foreground" /> Orientation
                                            </label>
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

                                        {/* Transition style */}
                                        <div className="space-y-2">
                                            <label className="text-sm font-medium flex items-center gap-1.5">
                                                <Wand2 className="h-3.5 w-3.5 text-muted-foreground" /> Transition Style
                                            </label>
                                            <div className="flex gap-2">
                                                {(['crossfade', 'cut', 'fade'] as const).map(t => (
                                                    <Button
                                                        key={t}
                                                        variant={transitionStyle === t ? 'default' : 'outline'}
                                                        size="sm"
                                                        onClick={() => setTransitionStyle(t)}
                                                        disabled={!enableTransitions}
                                                    >
                                                        {t.charAt(0).toUpperCase() + t.slice(1)}
                                                    </Button>
                                                ))}
                                            </div>
                                        </div>
                                    </div>

                                    {/* Row 2: Toggle switches */}
                                    <div className="border-t pt-4">
                                        <label className="text-sm font-medium mb-3 block">Production Options</label>
                                        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
                                            <ToggleOption
                                                icon={<Scissors className="h-4 w-4" />}
                                                label="Transitions"
                                                enabled={enableTransitions}
                                                onToggle={() => setEnableTransitions(!enableTransitions)}
                                            />
                                            <ToggleOption
                                                icon={<Mic className="h-4 w-4" />}
                                                label="Voiceover"
                                                enabled={enableVoiceover}
                                                onToggle={() => setEnableVoiceover(!enableVoiceover)}
                                            />
                                            <ToggleOption
                                                icon={<Subtitles className="h-4 w-4" />}
                                                label="Subtitles"
                                                enabled={enableSubtitles}
                                                onToggle={() => setEnableSubtitles(!enableSubtitles)}
                                            />
                                            <ToggleOption
                                                icon={<Image className="h-4 w-4" />}
                                                label="Thumbnail"
                                                enabled={enableThumbnail}
                                                onToggle={() => setEnableThumbnail(!enableThumbnail)}
                                            />
                                            <ToggleOption
                                                icon={<Music className="h-4 w-4" />}
                                                label="Background Music"
                                                enabled={enableBgMusic}
                                                onToggle={() => setEnableBgMusic(!enableBgMusic)}
                                            />
                                        </div>
                                    </div>
                                </div>
                            )}

                            {error && <p className="text-sm text-red-400">{error}</p>}
                        </CardContent>
                    </Card>

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
                                            onClick={() => {
                                                handleViewJob(job.job_id);
                                                setViewMode(job.status === 'completed' ? 'preview' : 'progress');
                                            }}
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

                    {jobs.length === 0 && (
                        <EmptyState
                            icon={Factory}
                            title="No compilation videos yet"
                            description="Enter a niche above and click 'Make Video' to produce a real compilation video from YouTube source clips."
                        />
                    )}
                </>
            )}

            {/* ═══ PROGRESS VIEW ═══ */}
            {viewMode === 'progress' && activeJob && (
                <>
                    {/* Back button */}
                    <Button variant="ghost" size="sm" onClick={() => setViewMode('create')}>
                        ← Back to Create
                    </Button>

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
                                    {activeJob.status === 'completed' && (
                                        <Button size="sm" onClick={() => setViewMode('preview')}>
                                            <Eye className="mr-1 h-4 w-4" /> Preview
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

                            {/* Full pipeline stages */}
                            <div className="grid grid-cols-5 gap-2 sm:grid-cols-10">
                                {ALL_STAGES.map(stage => {
                                    const isComplete = activeJob.stages_completed.includes(stage);
                                    const isCurrent = activeJob.current_stage === stage;
                                    const Icon = STAGE_ICONS[stage] || CheckCircle2;
                                    return (
                                        <div
                                            key={stage}
                                            className={`flex flex-col items-center gap-1 rounded-lg p-2 text-center transition-all ${isComplete
                                                    ? 'bg-green-500/10 text-green-400'
                                                    : isCurrent
                                                        ? 'bg-blue-500/10 text-blue-400 ring-1 ring-blue-500/30'
                                                        : 'bg-muted/30 text-muted-foreground/50'
                                                }`}
                                            title={STAGE_LABELS[stage] || stage}
                                        >
                                            {isCurrent && !isComplete ? (
                                                <Loader2 className="h-4 w-4 animate-spin" />
                                            ) : (
                                                <Icon className="h-4 w-4" />
                                            )}
                                            <span className="text-[9px] leading-tight">
                                                {(STAGE_LABELS[stage] || stage).split(' ').slice(0, 2).join(' ')}
                                            </span>
                                        </div>
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

                            {/* Clip Editor */}
                            {activeJob.clips && activeJob.clips.length > 0 && (
                                <div className="rounded-lg bg-muted/50 p-4 space-y-3">
                                    <div className="flex items-center justify-between">
                                        <h4 className="text-sm font-semibold flex items-center gap-2">
                                            <Scissors className="h-4 w-4" />
                                            Clip Editor ({getVisibleClips().length} / {activeJob.clips.length} clips)
                                        </h4>
                                        {removedClips.size > 0 && (
                                            <Button
                                                variant="ghost"
                                                size="sm"
                                                onClick={() => setRemovedClips(new Set())}
                                                className="text-xs"
                                            >
                                                <RotateCcw className="mr-1 h-3 w-3" /> Reset
                                            </Button>
                                        )}
                                    </div>
                                    <div className="space-y-1 max-h-72 overflow-y-auto">
                                        {activeJob.clips.map(clip => {
                                            const isRemoved = removedClips.has(clip.clip_id);
                                            return (
                                                <div
                                                    key={clip.clip_id}
                                                    className={`flex items-center justify-between rounded px-3 py-2 text-sm transition-all ${isRemoved
                                                            ? 'bg-red-500/5 opacity-40 line-through'
                                                            : clip.is_valid
                                                                ? 'bg-card'
                                                                : 'bg-red-500/5 opacity-60'
                                                        }`}
                                                >
                                                    <div className="flex items-center gap-3">
                                                        <GripVertical className="h-4 w-4 text-muted-foreground/40 cursor-grab" />
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
                                                        <span className="text-xs text-muted-foreground truncate max-w-[100px]">
                                                            {clip.source_video_id}
                                                        </span>
                                                        <Button
                                                            variant="ghost"
                                                            size="sm"
                                                            className="h-6 w-6 p-0"
                                                            onClick={() => toggleClipRemoved(clip.clip_id)}
                                                            title={isRemoved ? 'Restore clip' : 'Remove clip'}
                                                        >
                                                            {isRemoved ? (
                                                                <RotateCcw className="h-3 w-3 text-blue-400" />
                                                            ) : (
                                                                <XCircle className="h-3 w-3 text-red-400" />
                                                            )}
                                                        </Button>
                                                    </div>
                                                </div>
                                            );
                                        })}
                                    </div>
                                    {removedClips.size > 0 && (
                                        <p className="text-xs text-muted-foreground">
                                            {removedClips.size} clip(s) removed. These will be excluded in future rebuilds.
                                        </p>
                                    )}
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

                            {/* Failed job actions */}
                            {activeJob.status === 'failed' && (
                                <div className="flex gap-3">
                                    <Button variant="outline" onClick={handleRebuild}>
                                        <RotateCcw className="mr-2 h-4 w-4" /> Edit & Rebuild
                                    </Button>
                                    <Button variant="destructive" onClick={handleDelete} disabled={isDeleting}>
                                        {isDeleting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Trash2 className="mr-2 h-4 w-4" />}
                                        Delete Job
                                    </Button>
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </>
            )}

            {/* ═══ PREVIEW VIEW ═══ */}
            {viewMode === 'preview' && activeJob && activeJob.status === 'completed' && (
                <>
                    {/* Back button */}
                    <Button variant="ghost" size="sm" onClick={() => setViewMode('create')}>
                        ← Back to Create
                    </Button>

                    {/* Video Player */}
                    <Card className="overflow-hidden">
                        <div className={`relative bg-black ${orientation === 'portrait' ? 'max-w-sm mx-auto' : ''}`}>
                            <video
                                className="w-full"
                                controls
                                autoPlay={false}
                                preload="metadata"
                                src={getVideoFactoryStreamUrl(activeJob.job_id)}
                                poster={
                                    activeJob.output_files?.thumbnail
                                        ? getVideoFactoryDownloadUrl(activeJob.job_id, 'thumbnail')
                                        : undefined
                                }
                            >
                                Your browser does not support the video tag.
                            </video>
                        </div>
                        <CardContent className="pt-4 space-y-4">
                            {/* Title & metadata */}
                            {activeJob.metadata && (
                                <div className="space-y-2">
                                    <h2 className="text-xl font-bold">{activeJob.metadata.title}</h2>
                                    <p className="text-sm text-muted-foreground line-clamp-3">
                                        {activeJob.metadata.description}
                                    </p>
                                    {activeJob.metadata.tags.length > 0 && (
                                        <div className="flex flex-wrap gap-1 mt-1">
                                            {activeJob.metadata.tags.slice(0, 12).map(tag => (
                                                <Badge key={tag} variant="outline" className="text-xs">
                                                    {tag}
                                                </Badge>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            )}

                            {/* Info row */}
                            <div className="flex flex-wrap gap-4 text-sm text-muted-foreground">
                                {activeJob.timeline_info && (
                                    <>
                                        <span className="flex items-center gap-1">
                                            <Film className="h-4 w-4" />
                                            {activeJob.timeline_info.entries} clips
                                        </span>
                                        <span className="flex items-center gap-1">
                                            <Clock className="h-4 w-4" />
                                            {formatDuration(activeJob.timeline_info.total_duration)}
                                        </span>
                                    </>
                                )}
                                {activeJob.copyright_report && (
                                    <span className={`flex items-center gap-1 ${activeJob.copyright_report.is_safe ? 'text-green-400' : 'text-yellow-400'
                                        }`}>
                                        <Shield className="h-4 w-4" />
                                        {activeJob.copyright_report.is_safe ? 'Copyright Safe' : 'Warnings'}
                                    </span>
                                )}
                                {activeJob.settings && (
                                    <span className="flex items-center gap-1">
                                        {activeJob.settings.orientation === 'portrait'
                                            ? <Smartphone className="h-4 w-4" />
                                            : <Monitor className="h-4 w-4" />
                                        }
                                        {activeJob.settings.orientation === 'portrait' ? '9:16' : '16:9'}
                                    </span>
                                )}
                            </div>

                            {/* Action buttons */}
                            <div className="border-t pt-4">
                                <h4 className="text-sm font-semibold mb-3">Actions</h4>
                                <div className="flex flex-wrap gap-3">
                                    {/* Download assets */}
                                    {activeJob.output_files && (
                                        <>
                                            <a
                                                href={getVideoFactoryDownloadUrl(activeJob.job_id, 'video')}
                                                download
                                            >
                                                <Button variant="outline">
                                                    <Download className="mr-2 h-4 w-4" /> Download MP4
                                                </Button>
                                            </a>
                                            <a
                                                href={getVideoFactoryDownloadUrl(activeJob.job_id, 'thumbnail')}
                                                download
                                            >
                                                <Button variant="outline">
                                                    <Image className="mr-2 h-4 w-4" /> Thumbnail
                                                </Button>
                                            </a>
                                            <a
                                                href={getVideoFactoryDownloadUrl(activeJob.job_id, 'metadata')}
                                                download
                                            >
                                                <Button variant="outline">
                                                    <Tag className="mr-2 h-4 w-4" /> Metadata
                                                </Button>
                                            </a>
                                        </>
                                    )}

                                    {/* Edit & Rebuild */}
                                    <Button variant="secondary" onClick={handleRebuild}>
                                        <RotateCcw className="mr-2 h-4 w-4" /> Edit & Rebuild
                                    </Button>

                                    {/* Open in Editor */}
                                    <Button
                                        variant="outline"
                                        onClick={() => window.location.href = `/video-editor?job=${activeJob.job_id}`}
                                    >
                                        <Scissors className="mr-2 h-4 w-4" /> Open in Editor
                                    </Button>

                                    {/* Delete */}
                                    <Button variant="destructive" onClick={handleDelete} disabled={isDeleting}>
                                        {isDeleting ? (
                                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                        ) : (
                                            <Trash2 className="mr-2 h-4 w-4" />
                                        )}
                                        Delete
                                    </Button>
                                </div>
                            </div>
                        </CardContent>
                    </Card>

                    {/* Strategy summary below player */}
                    {activeJob.strategy && (
                        <Card>
                            <CardHeader>
                                <CardTitle className="text-sm flex items-center gap-2">
                                    <Zap className="h-4 w-4 text-yellow-400" /> Compilation Strategy
                                </CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className="flex gap-6 text-sm text-muted-foreground">
                                    <span>{activeJob.strategy.source_videos_found} source videos</span>
                                    <span>{activeJob.strategy.segments_recommended} clips extracted</span>
                                    <span>Score: {activeJob.strategy.compilation_score.toFixed(1)}</span>
                                </div>
                            </CardContent>
                        </Card>
                    )}

                    {/* Clips used */}
                    {activeJob.clips && activeJob.clips.length > 0 && (
                        <Card>
                            <CardHeader>
                                <CardTitle className="text-sm flex items-center gap-2">
                                    <Scissors className="h-4 w-4" />
                                    Clips Used ({activeJob.clips.filter(c => c.is_valid).length})
                                </CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className="space-y-1 max-h-48 overflow-y-auto">
                                    {activeJob.clips.filter(c => c.is_valid).map(clip => (
                                        <div
                                            key={clip.clip_id}
                                            className="flex items-center justify-between rounded px-3 py-2 text-sm bg-card"
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
                                            <span className="text-xs text-muted-foreground">
                                                {formatDuration(clip.duration_seconds)}
                                            </span>
                                        </div>
                                    ))}
                                </div>
                            </CardContent>
                        </Card>
                    )}
                </>
            )}

            {/* Error display (global) */}
            {error && viewMode !== 'create' && (
                <div className="rounded-lg bg-red-500/10 border border-red-500/30 p-3">
                    <p className="text-sm text-red-400">{error}</p>
                </div>
            )}
        </div>
    );
}

// ── Toggle Option Component ───────────────────────────────────────────────────

function ToggleOption({
    icon,
    label,
    enabled,
    onToggle,
}: {
    icon: React.ReactNode;
    label: string;
    enabled: boolean;
    onToggle: () => void;
}) {
    return (
        <button
            type="button"
            onClick={onToggle}
            className={`flex items-center gap-2 rounded-lg border p-3 text-sm font-medium transition-all cursor-pointer ${enabled
                    ? 'border-primary bg-primary/10 text-primary'
                    : 'border-border bg-card text-muted-foreground hover:bg-accent'
                }`}
        >
            {icon}
            <span>{label}</span>
            <div className={`ml-auto h-4 w-7 rounded-full transition-colors ${enabled ? 'bg-primary' : 'bg-muted'}`}>
                <div className={`h-3 w-3 mt-0.5 rounded-full bg-white transition-transform ${enabled ? 'translate-x-3.5' : 'translate-x-0.5'}`} />
            </div>
        </button>
    );
}
