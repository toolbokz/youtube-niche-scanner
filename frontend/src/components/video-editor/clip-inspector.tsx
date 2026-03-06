'use client';

import React from 'react';
import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useEditorStore } from '@/store/editor-store';
import type { EditorClip } from '@/types';
import {
    Scissors,
    X,
    ChevronUp,
    ChevronDown,
    Clock,
    Zap,
    Film,
    RotateCcw,
} from 'lucide-react';

function formatTime(seconds: number): string {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s.toString().padStart(2, '0')}`;
}

// ═══════════════════════════════════════════════════════════════════════════════
//  Clip Inspector – shows when a clip is selected on the timeline
// ═══════════════════════════════════════════════════════════════════════════════

export function ClipInspector() {
    const clips = useEditorStore((s) => s.clips);
    const selectedClipId = useEditorStore((s) => s.selectedClipId);
    const setSelectedClipId = useEditorStore((s) => s.setSelectedClipId);
    const updateClip = useEditorStore((s) => s.updateClip);
    const trimClip = useEditorStore((s) => s.trimClip);
    const removeClip = useEditorStore((s) => s.removeClip);
    const reorderClips = useEditorStore((s) => s.reorderClips);
    const transitions = useEditorStore((s) => s.transitions);
    const setTransitionAt = useEditorStore((s) => s.setTransitionAt);

    const clip = clips.find((c) => c.clip_id === selectedClipId);

    if (!clip) {
        return (
            <div className="flex flex-col items-center justify-center h-full text-muted-foreground p-4">
                <Scissors className="w-8 h-8 opacity-30 mb-2" />
                <p className="text-sm">Select a clip on the timeline</p>
                <p className="text-xs opacity-60">to edit its properties</p>
            </div>
        );
    }

    const effectiveStart = clip.trim_start ?? clip.start_seconds;
    const effectiveEnd = clip.trim_end ?? clip.end_seconds;
    const effectiveDuration = Math.max(0, effectiveEnd - effectiveStart);
    const clipIndex = clips.findIndex((c) => c.clip_id === clip.clip_id);
    const currentTransition = transitions.find((t) => t.after_clip_index === clipIndex - 1);

    return (
        <div className="flex flex-col gap-3 p-3">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <Film className="w-4 h-4 text-muted-foreground" />
                    <span className="text-sm font-medium">Clip Properties</span>
                </div>
                <Button variant="ghost" size="icon" className="h-6 w-6" onClick={() => setSelectedClipId(null)}>
                    <X className="w-3.5 h-3.5" />
                </Button>
            </div>

            {/* Clip info */}
            <div className="rounded-md border p-2 space-y-1.5 bg-muted/30">
                <p className="text-xs font-medium truncate">
                    {clip.label || clip.segment_type || clip.clip_id.slice(0, 16)}
                </p>
                <div className="flex items-center gap-2 flex-wrap">
                    <Badge variant="outline" className="text-[10px] h-4 px-1">
                        {clip.segment_type || 'unknown'}
                    </Badge>
                    <Badge variant="outline" className="text-[10px] h-4 px-1">
                        <Zap className="w-2 h-2 mr-0.5" />
                        {clip.energy_level}
                    </Badge>
                    <span className="text-[10px] text-muted-foreground">
                        <Clock className="w-2 h-2 inline mr-0.5" />
                        {formatTime(effectiveDuration)}
                    </span>
                </div>
                <p className="text-[10px] text-muted-foreground truncate">
                    Source: {clip.source_video_id}
                </p>
            </div>

            {/* Label */}
            <div>
                <label className="text-[11px] font-medium text-muted-foreground">Label</label>
                <Input
                    value={clip.label || ''}
                    onChange={(e) => updateClip(clip.clip_id, { label: e.target.value })}
                    className="h-7 text-xs mt-0.5"
                    placeholder="Clip label..."
                />
            </div>

            {/* Trim controls */}
            <div>
                <label className="text-[11px] font-medium text-muted-foreground flex items-center gap-1">
                    <Scissors className="w-3 h-3" />
                    Trim
                </label>
                <div className="grid grid-cols-2 gap-2 mt-1">
                    <div>
                        <span className="text-[10px] text-muted-foreground">Start (s)</span>
                        <Input
                            type="number"
                            min={clip.start_seconds}
                            max={effectiveEnd}
                            step={0.1}
                            value={effectiveStart}
                            onChange={(e) =>
                                trimClip(clip.clip_id, parseFloat(e.target.value) || clip.start_seconds, clip.trim_end)
                            }
                            className="h-7 text-xs mt-0.5"
                        />
                    </div>
                    <div>
                        <span className="text-[10px] text-muted-foreground">End (s)</span>
                        <Input
                            type="number"
                            min={effectiveStart}
                            max={clip.end_seconds}
                            step={0.1}
                            value={effectiveEnd}
                            onChange={(e) =>
                                trimClip(clip.clip_id, clip.trim_start, parseFloat(e.target.value) || clip.end_seconds)
                            }
                            className="h-7 text-xs mt-0.5"
                        />
                    </div>
                </div>
                {(clip.trim_start !== null || clip.trim_end !== null) && (
                    <Button
                        variant="ghost"
                        size="sm"
                        className="h-6 text-[10px] mt-1 w-full"
                        onClick={() => trimClip(clip.clip_id, null, null)}
                    >
                        <RotateCcw className="w-2.5 h-2.5 mr-1" />
                        Reset trim
                    </Button>
                )}
            </div>

            {/* Transition before this clip */}
            {clipIndex > 0 && (
                <div>
                    <label className="text-[11px] font-medium text-muted-foreground">Transition In</label>
                    <div className="flex gap-1 mt-1 flex-wrap">
                        {(['cut', 'fade', 'crossdissolve', 'zoom'] as const).map((t) => (
                            <Button
                                key={t}
                                variant={currentTransition?.type === t ? 'secondary' : 'outline'}
                                size="sm"
                                className="h-6 text-[10px] px-2"
                                onClick={() => setTransitionAt(clipIndex - 1, t)}
                            >
                                {t}
                            </Button>
                        ))}
                    </div>
                </div>
            )}

            {/* Reorder */}
            <div className="flex items-center gap-1">
                <Button
                    variant="outline"
                    size="sm"
                    className="h-7 text-xs flex-1"
                    onClick={() => {
                        if (clipIndex > 0) reorderClips(clipIndex, clipIndex - 1);
                    }}
                    disabled={clipIndex <= 0}
                >
                    <ChevronUp className="w-3 h-3 mr-1" />
                    Move Left
                </Button>
                <Button
                    variant="outline"
                    size="sm"
                    className="h-7 text-xs flex-1"
                    onClick={() => {
                        if (clipIndex < clips.length - 1) reorderClips(clipIndex, clipIndex + 1);
                    }}
                    disabled={clipIndex >= clips.length - 1}
                >
                    Move Right
                    <ChevronDown className="w-3 h-3 ml-1" />
                </Button>
            </div>

            {/* Remove */}
            <Button
                variant="destructive"
                size="sm"
                className="h-7 text-xs w-full"
                onClick={() => {
                    removeClip(clip.clip_id);
                    setSelectedClipId(null);
                }}
            >
                <X className="w-3 h-3 mr-1" />
                Remove from Timeline
            </Button>
        </div>
    );
}
