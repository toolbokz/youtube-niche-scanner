'use client';

import { useState, useEffect, useCallback, useRef, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Spinner } from '@/components/ui/spinner';
import {
    TimelineEditor,
    PreviewPlayer,
    ClipLibraryPanel,
    ClipInspector,
    SettingsPanel,
    TextOverlayPanel,
} from '@/components/video-editor';
import { useEditorStore, type EditorPanel } from '@/store/editor-store';
import {
    getEditorClips,
    loadEditorTimeline,
    saveEditorTimeline,
    startEditorRender,
    getEditorRenderStatus,
    getEditorRenderStreamUrl,
    getVideoFactoryStreamUrl,
} from '@/services/api';
import type { EditorClip, EditorRenderStatus } from '@/types';
import {
    Film,
    LayoutGrid,
    Settings,
    Type,
    Save,
    Eye,
    Clapperboard,
    ArrowLeft,
    Loader2,
    CheckCircle2,
    XCircle,
    Download,
    RotateCcw,
    AlertTriangle,
} from 'lucide-react';

// ═══════════════════════════════════════════════════════════════════════════════
//  Inner page content (needs Suspense boundary for useSearchParams)
// ═══════════════════════════════════════════════════════════════════════════════

function VideoEditorContent() {
    const router = useRouter();
    const params = useSearchParams();
    const jobId = params.get('job');

    // ── Store ─────────────────────────────────────────────────────────
    const store = useEditorStore();
    const {
        setJob,
        setClips,
        setClipLibrary,
        loadTimeline,
        getTimeline,
        clips,
        isDirty,
        markClean,
        viewMode,
        setViewMode,
        activePanel,
        setActivePanel,
        resetEditor,
        currentRenderId,
        setCurrentRenderId,
        lastRenderUrl,
        setLastRenderUrl,
    } = store;

    // ── Local state ───────────────────────────────────────────────────
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [saving, setSaving] = useState(false);
    const [renderStatus, setRenderStatus] = useState<EditorRenderStatus | null>(null);
    const renderPollRef = useRef<ReturnType<typeof setInterval> | null>(null);

    // ── Load clips + saved timeline on mount ──────────────────────────
    useEffect(() => {
        if (!jobId) {
            setError('No job ID provided. Navigate from Video Factory.');
            setLoading(false);
            return;
        }

        let cancelled = false;

        async function load() {
            try {
                setLoading(true);
                setError(null);

                // Fetch clips from the completed job
                const data = await getEditorClips(jobId!);
                if (cancelled) return;

                setJob(jobId!, data.niche);

                // Build clip library from all extracted clips
                const libraryClips: EditorClip[] = data.clips.map((c, i) => ({
                    clip_id: c.clip_id,
                    source_video_id: c.source_video_id,
                    source_file_path: c.source_file_path,
                    start_seconds: c.start_seconds,
                    end_seconds: c.end_seconds,
                    duration_seconds: c.duration_seconds,
                    position: i,
                    segment_type: c.segment_type,
                    energy_level: c.energy_level,
                    label: '',
                    trim_start: null,
                    trim_end: null,
                    is_valid: c.is_valid,
                    width: c.width,
                    height: c.height,
                    file_size_mb: c.file_size_mb,
                }));
                setClipLibrary(libraryClips);

                // Try to load a saved timeline
                const saved = await loadEditorTimeline(jobId!);
                if (cancelled) return;

                if (saved.found && saved.timeline) {
                    loadTimeline(saved.timeline);
                } else {
                    // Initialize timeline from the job's compiled order
                    const timelineClips: EditorClip[] = data.timeline.map((t, i) => ({
                        clip_id: t.clip_id,
                        source_video_id: t.source_video_id,
                        source_file_path: t.clip_file_path,
                        start_seconds: t.start_seconds,
                        end_seconds: t.end_seconds,
                        duration_seconds: t.duration_seconds,
                        position: i,
                        segment_type: t.segment_type,
                        energy_level: t.energy_level,
                        label: '',
                        trim_start: null,
                        trim_end: null,
                    }));
                    setClips(timelineClips);
                    markClean(); // Initial load isn't dirty
                }

                // Set the original video as initial preview
                setLastRenderUrl(getVideoFactoryStreamUrl(jobId!));
            } catch (err: any) {
                if (!cancelled) {
                    setError(err.message || 'Failed to load editor data');
                }
            } finally {
                if (!cancelled) setLoading(false);
            }
        }

        load();
        return () => {
            cancelled = true;
        };
    }, [jobId]); // eslint-disable-line react-hooks/exhaustive-deps

    // ── Cleanup render polling on unmount ──────────────────────────────
    useEffect(() => {
        return () => {
            if (renderPollRef.current) clearInterval(renderPollRef.current);
        };
    }, []);

    // ── Save timeline ─────────────────────────────────────────────────
    const handleSave = useCallback(async () => {
        if (!jobId) return;
        try {
            setSaving(true);
            await saveEditorTimeline(jobId, getTimeline());
            markClean();
        } catch (err: any) {
            setError(err.message || 'Save failed');
        } finally {
            setSaving(false);
        }
    }, [jobId, getTimeline, markClean]);

    // ── Render (preview or final) ─────────────────────────────────────
    const handleRender = useCallback(
        async (isPreview: boolean) => {
            if (!jobId) return;

            try {
                const timeline = getTimeline();
                const res = await startEditorRender({
                    job_id: jobId,
                    is_preview: isPreview,
                    clips: timeline.clips,
                    transitions: timeline.transitions,
                    markers: timeline.markers,
                    text_overlays: timeline.text_overlays,
                    orientation: timeline.orientation,
                    resolution: isPreview ? '720p' : timeline.resolution,
                    target_duration_seconds: timeline.target_duration_seconds,
                    max_scene_duration: timeline.max_scene_duration,
                    background_audio: timeline.background_audio,
                });

                setCurrentRenderId(res.render_id);
                setRenderStatus({
                    render_id: res.render_id,
                    job_id: jobId,
                    type: res.type,
                    status: 'queued',
                    progress_pct: 0,
                    output_path: null,
                    error: null,
                });

                // Poll for status
                if (renderPollRef.current) clearInterval(renderPollRef.current);
                renderPollRef.current = setInterval(async () => {
                    try {
                        const status = await getEditorRenderStatus(res.render_id);
                        setRenderStatus(status);

                        if (status.status === 'completed') {
                            clearInterval(renderPollRef.current!);
                            renderPollRef.current = null;
                            setLastRenderUrl(getEditorRenderStreamUrl(res.render_id));
                            if (!isPreview) {
                                setViewMode('review');
                            }
                        } else if (status.status === 'failed') {
                            clearInterval(renderPollRef.current!);
                            renderPollRef.current = null;
                        }
                    } catch {
                        // fetch error — keep polling
                    }
                }, 2000);
            } catch (err: any) {
                setError(err.message || 'Render failed to start');
            }
        },
        [jobId, getTimeline, setCurrentRenderId, setLastRenderUrl, setViewMode],
    );

    // ── Render state helpers ──────────────────────────────────────────
    const isRendering =
        renderStatus?.status === 'queued' || renderStatus?.status === 'rendering';
    const renderComplete = renderStatus?.status === 'completed';
    const renderFailed = renderStatus?.status === 'failed';

    // ── Tab configs ───────────────────────────────────────────────────
    const panels: Array<{ key: EditorPanel; label: string; icon: typeof Film }> = [
        { key: 'timeline', label: 'Timeline', icon: Film },
        { key: 'clips', label: 'Clips', icon: LayoutGrid },
        { key: 'text', label: 'Text', icon: Type },
        { key: 'settings', label: 'Settings', icon: Settings },
    ];

    // ══════════════════════════════════════════════════════════════════
    //  Loading / Error states
    // ══════════════════════════════════════════════════════════════════

    if (loading) {
        return (
            <div className="flex items-center justify-center h-[60vh]">
                <Spinner size={32} />
            </div>
        );
    }

    if (error && !clips.length) {
        return (
            <div className="flex flex-col items-center justify-center h-[60vh] gap-3">
                <AlertTriangle className="w-10 h-10 text-amber-500" />
                <p className="text-sm text-muted-foreground">{error}</p>
                <Button variant="outline" size="sm" onClick={() => router.push('/video-factory')}>
                    <ArrowLeft className="w-3.5 h-3.5 mr-1" />
                    Back to Video Factory
                </Button>
            </div>
        );
    }

    // ══════════════════════════════════════════════════════════════════
    //  Review Mode
    // ══════════════════════════════════════════════════════════════════

    if (viewMode === 'review') {
        return (
            <div className="space-y-4 p-4">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <Button variant="ghost" size="sm" onClick={() => setViewMode('editor')}>
                            <ArrowLeft className="w-3.5 h-3.5 mr-1" />
                            Back to Editor
                        </Button>
                        <h1 className="text-lg font-semibold">Video Review</h1>
                        <Badge variant="success">Final Render</Badge>
                    </div>
                    <div className="flex items-center gap-2">
                        {lastRenderUrl && (
                            <a href={lastRenderUrl} download>
                                <Button variant="outline" size="sm">
                                    <Download className="w-3.5 h-3.5 mr-1" />
                                    Download
                                </Button>
                            </a>
                        )}
                        <Button variant="outline" size="sm" onClick={() => router.push('/video-factory')}>
                            Return to Factory
                        </Button>
                    </div>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                    {/* Video player */}
                    <div className="lg:col-span-2">
                        <PreviewPlayer streamUrl={lastRenderUrl} />
                    </div>

                    {/* Details */}
                    <Card>
                        <CardHeader className="p-4">
                            <CardTitle className="text-sm">Render Details</CardTitle>
                        </CardHeader>
                        <CardContent className="p-4 pt-0 space-y-3">
                            <div className="space-y-2">
                                <DetailRow label="Niche" value={store.niche} />
                                <DetailRow label="Clips" value={String(clips.length)} />
                                <DetailRow
                                    label="Duration"
                                    value={`${Math.floor(store.totalDuration() / 60)}m ${Math.floor(store.totalDuration() % 60)}s`}
                                />
                                <DetailRow label="Resolution" value={store.resolution} />
                                <DetailRow label="Orientation" value={store.orientation} />
                                <DetailRow label="Audio" value={store.backgroundAudio} />
                            </div>

                            {renderStatus && (
                                <div className="pt-2 border-t">
                                    <DetailRow label="Render ID" value={renderStatus.render_id} />
                                    <DetailRow
                                        label="Status"
                                        value={
                                            <Badge
                                                variant={
                                                    renderStatus.status === 'completed'
                                                        ? 'success'
                                                        : renderStatus.status === 'failed'
                                                        ? 'destructive'
                                                        : 'default'
                                                }
                                            >
                                                {renderStatus.status}
                                            </Badge>
                                        }
                                    />
                                </div>
                            )}

                            <div className="pt-2 border-t flex flex-col gap-2">
                                <Button
                                    variant="outline"
                                    size="sm"
                                    className="w-full text-xs"
                                    onClick={() => setViewMode('editor')}
                                >
                                    <RotateCcw className="w-3 h-3 mr-1" />
                                    Return to Editor
                                </Button>
                            </div>
                        </CardContent>
                    </Card>
                </div>
            </div>
        );
    }

    // ══════════════════════════════════════════════════════════════════
    //  Editor Mode
    // ══════════════════════════════════════════════════════════════════

    return (
        <div className="flex flex-col h-[calc(100vh-4rem)] overflow-hidden">
            {/* ── Top bar ──────────────────────────────────────────── */}
            <div className="flex items-center gap-2 px-4 py-2 border-b bg-card/80 backdrop-blur flex-shrink-0">
                <Button variant="ghost" size="sm" onClick={() => router.push('/video-factory')}>
                    <ArrowLeft className="w-3.5 h-3.5 mr-1" />
                    Factory
                </Button>

                <div className="w-px h-5 bg-border" />

                <Clapperboard className="w-4 h-4 text-muted-foreground" />
                <span className="text-sm font-medium">Video Editor</span>
                {store.niche && (
                    <Badge variant="outline" className="text-[10px]">
                        {store.niche}
                    </Badge>
                )}

                {isDirty && (
                    <Badge variant="warning" className="text-[10px]">
                        Unsaved
                    </Badge>
                )}

                <div className="flex-1" />

                {/* Error banner */}
                {error && (
                    <div className="flex items-center gap-1 text-xs text-destructive mr-2">
                        <XCircle className="w-3.5 h-3.5" />
                        {error}
                    </div>
                )}

                {/* Save */}
                <Button
                    variant="outline"
                    size="sm"
                    onClick={handleSave}
                    disabled={saving || !isDirty}
                >
                    {saving ? (
                        <Loader2 className="w-3.5 h-3.5 mr-1 animate-spin" />
                    ) : (
                        <Save className="w-3.5 h-3.5 mr-1" />
                    )}
                    Save
                </Button>

                {/* Preview render */}
                <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleRender(true)}
                    disabled={isRendering || clips.length === 0}
                >
                    {isRendering && renderStatus?.type === 'preview' ? (
                        <Loader2 className="w-3.5 h-3.5 mr-1 animate-spin" />
                    ) : (
                        <Eye className="w-3.5 h-3.5 mr-1" />
                    )}
                    Preview
                </Button>

                {/* Final render */}
                <Button
                    size="sm"
                    onClick={() => handleRender(false)}
                    disabled={isRendering || clips.length === 0}
                >
                    {isRendering && renderStatus?.type === 'final' ? (
                        <Loader2 className="w-3.5 h-3.5 mr-1 animate-spin" />
                    ) : (
                        <Clapperboard className="w-3.5 h-3.5 mr-1" />
                    )}
                    Render
                </Button>
            </div>

            {/* ── Render progress bar ──────────────────────────────── */}
            {isRendering && renderStatus && (
                <div className="px-4 py-1.5 border-b bg-muted/30 flex items-center gap-3 flex-shrink-0">
                    <Loader2 className="w-3.5 h-3.5 animate-spin text-primary" />
                    <span className="text-xs text-muted-foreground">
                        Rendering {renderStatus.type}...
                    </span>
                    <Progress value={renderStatus.progress_pct} className="flex-1 h-1.5" />
                    <span className="text-xs text-muted-foreground tabular-nums">
                        {Math.round(renderStatus.progress_pct)}%
                    </span>
                </div>
            )}

            {renderFailed && renderStatus && (
                <div className="px-4 py-1.5 border-b bg-destructive/10 flex items-center gap-2 flex-shrink-0">
                    <XCircle className="w-3.5 h-3.5 text-destructive" />
                    <span className="text-xs text-destructive">
                        Render failed: {renderStatus.error}
                    </span>
                </div>
            )}

            {/* ── Main layout: sidebar-left | center | sidebar-right ── */}
            <div className="flex flex-1 overflow-hidden">
                {/* Left sidebar: clip library / settings / text */}
                <div className="w-72 border-r bg-card/50 flex flex-col flex-shrink-0 overflow-hidden">
                    {/* Panel tabs */}
                    <div className="flex border-b">
                        {panels.map(({ key, label, icon: Icon }) => (
                            <button
                                key={key}
                                className={`flex-1 flex flex-col items-center gap-0.5 py-2 text-[10px] transition-colors ${
                                    activePanel === key
                                        ? 'text-primary border-b-2 border-primary bg-primary/5'
                                        : 'text-muted-foreground hover:text-foreground'
                                }`}
                                onClick={() => setActivePanel(key)}
                            >
                                <Icon className="w-3.5 h-3.5" />
                                {label}
                            </button>
                        ))}
                    </div>

                    {/* Panel content */}
                    <div className="flex-1 overflow-y-auto">
                        {activePanel === 'timeline' && <ClipInspector />}
                        {activePanel === 'clips' && <ClipLibraryPanel />}
                        {activePanel === 'text' && <TextOverlayPanel />}
                        {activePanel === 'settings' && <SettingsPanel />}
                    </div>
                </div>

                {/* Center: preview + timeline */}
                <div className="flex-1 flex flex-col overflow-hidden">
                    {/* Preview player */}
                    <div className="flex-shrink-0 p-3">
                        <PreviewPlayer
                            streamUrl={lastRenderUrl}
                            className="max-h-[40vh]"
                        />
                    </div>

                    {/* Timeline */}
                    <div className="flex-1 overflow-auto p-3 pt-0">
                        <TimelineEditor />
                    </div>
                </div>
            </div>
        </div>
    );
}

// ═══════════════════════════════════════════════════════════════════════════════
//  Detail row for review screen
// ═══════════════════════════════════════════════════════════════════════════════

function DetailRow({ label, value }: { label: string; value: React.ReactNode }) {
    return (
        <div className="flex items-center justify-between text-xs">
            <span className="text-muted-foreground">{label}</span>
            <span className="font-medium">{value}</span>
        </div>
    );
}

// ═══════════════════════════════════════════════════════════════════════════════
//  Page Export (wrapped in Suspense for useSearchParams)
// ═══════════════════════════════════════════════════════════════════════════════

export default function VideoEditorPage() {
    return (
        <Suspense
            fallback={
                <div className="flex items-center justify-center h-[60vh]">
                    <Spinner size={32} />
                </div>
            }
        >
            <VideoEditorContent />
        </Suspense>
    );
}
