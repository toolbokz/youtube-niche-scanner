'use client';

import React, { useCallback, useMemo, useRef } from 'react';
import {
    DndContext,
    closestCenter,
    KeyboardSensor,
    PointerSensor,
    useSensor,
    useSensors,
    type DragEndEvent,
} from '@dnd-kit/core';
import {
    SortableContext,
    sortableKeyboardCoordinates,
    horizontalListSortingStrategy,
    useSortable,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { useEditorStore } from '@/store/editor-store';
import type { EditorClip, EditorTransition } from '@/types';
import {
    GripVertical,
    Scissors,
    X,
    ChevronLeft,
    ChevronRight,
    ZoomIn,
    ZoomOut,
    Flag,
    Plus,
} from 'lucide-react';

// ═══════════════════════════════════════════════════════════════════════════════
//  Helper: format seconds → mm:ss
// ═══════════════════════════════════════════════════════════════════════════════

function formatTime(seconds: number): string {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s.toString().padStart(2, '0')}`;
}

function effectiveDuration(clip: EditorClip): number {
    const start = clip.trim_start ?? clip.start_seconds;
    const end = clip.trim_end ?? clip.end_seconds;
    return Math.max(0, end - start);
}

// ═══════════════════════════════════════════════════════════════════════════════
//  Energy Level Colors
// ═══════════════════════════════════════════════════════════════════════════════

const ENERGY_COLORS: Record<string, string> = {
    climax: 'bg-red-500/30 border-red-500/50',
    high: 'bg-orange-500/30 border-orange-500/50',
    medium: 'bg-blue-500/30 border-blue-500/50',
    low: 'bg-emerald-500/30 border-emerald-500/50',
};

const ENERGY_BADGE: Record<string, 'default' | 'destructive' | 'secondary' | 'outline' | 'success' | 'warning'> = {
    climax: 'destructive',
    high: 'warning',
    medium: 'default',
    low: 'success',
};

const TRANSITION_LABELS: Record<string, string> = {
    cut: '⬛ Cut',
    fade: '🔲 Fade',
    crossdissolve: '🔀 Dissolve',
    zoom: '🔍 Zoom',
};

// ═══════════════════════════════════════════════════════════════════════════════
//  Sortable Clip Block
// ═══════════════════════════════════════════════════════════════════════════════

interface SortableClipProps {
    clip: EditorClip;
    pixelsPerSecond: number;
    isSelected: boolean;
    transition?: EditorTransition;
    onSelect: () => void;
    onRemove: () => void;
    onTrim: () => void;
}

function SortableClipBlock({
    clip,
    pixelsPerSecond,
    isSelected,
    transition,
    onSelect,
    onRemove,
    onTrim,
}: SortableClipProps) {
    const {
        attributes,
        listeners,
        setNodeRef,
        transform,
        transition: dndTransition,
        isDragging,
    } = useSortable({ id: clip.clip_id });

    const style = {
        transform: CSS.Transform.toString(transform),
        transition: dndTransition,
    };

    const duration = effectiveDuration(clip);
    const width = Math.max(60, duration * pixelsPerSecond);

    return (
        <div className="flex items-end" style={style} ref={setNodeRef}>
            {/* Transition indicator */}
            {transition && clip.position > 0 && (
                <div className="flex flex-col items-center justify-end px-0.5 -mr-1 z-10">
                    <span className="text-[10px] text-muted-foreground whitespace-nowrap mb-0.5">
                        {TRANSITION_LABELS[transition.type] || transition.type}
                    </span>
                    <div className="w-px h-6 bg-border" />
                </div>
            )}

            {/* Clip block */}
            <div
                className={cn(
                    'relative flex flex-col rounded-md border cursor-pointer transition-all select-none',
                    'hover:ring-2 hover:ring-primary/50',
                    ENERGY_COLORS[clip.energy_level] || ENERGY_COLORS.medium,
                    isSelected && 'ring-2 ring-primary shadow-lg',
                    isDragging && 'opacity-50 z-50',
                )}
                style={{ width, minHeight: 72 }}
                onClick={onSelect}
            >
                {/* Drag handle */}
                <div
                    className="absolute top-0.5 left-0.5 cursor-grab active:cursor-grabbing text-muted-foreground/60 hover:text-foreground"
                    {...attributes}
                    {...listeners}
                >
                    <GripVertical className="w-3.5 h-3.5" />
                </div>

                {/* Remove button */}
                <button
                    className="absolute top-0.5 right-0.5 text-muted-foreground/60 hover:text-destructive"
                    onClick={(e) => {
                        e.stopPropagation();
                        onRemove();
                    }}
                >
                    <X className="w-3.5 h-3.5" />
                </button>

                {/* Content */}
                <div className="flex-1 flex flex-col justify-center px-2 pt-4 pb-1 overflow-hidden">
                    <p className="text-[11px] font-medium truncate leading-tight">
                        {clip.label || clip.segment_type || clip.clip_id.slice(0, 8)}
                    </p>
                    <div className="flex items-center gap-1 mt-0.5">
                        <Badge variant={ENERGY_BADGE[clip.energy_level]} className="text-[9px] px-1 py-0 h-3.5">
                            {clip.energy_level}
                        </Badge>
                        <span className="text-[10px] text-muted-foreground">
                            {formatTime(duration)}
                        </span>
                    </div>
                </div>

                {/* Trim indicators */}
                {(clip.trim_start !== null || clip.trim_end !== null) && (
                    <div className="absolute bottom-0.5 right-1 flex items-center gap-0.5 text-muted-foreground/70">
                        <Scissors className="w-2.5 h-2.5" />
                        <span className="text-[9px]">trimmed</span>
                    </div>
                )}
            </div>
        </div>
    );
}

// ═══════════════════════════════════════════════════════════════════════════════
//  Timeline Ruler
// ═══════════════════════════════════════════════════════════════════════════════

function TimelineRuler({ totalDuration, pixelsPerSecond }: { totalDuration: number; pixelsPerSecond: number }) {
    const ticks: number[] = [];
    const interval = totalDuration > 600 ? 60 : totalDuration > 120 ? 30 : 10;

    for (let t = 0; t <= totalDuration; t += interval) {
        ticks.push(t);
    }

    return (
        <div
            className="relative h-5 border-b border-border/50 flex-shrink-0"
            style={{ width: totalDuration * pixelsPerSecond }}
        >
            {ticks.map((t) => (
                <div
                    key={t}
                    className="absolute top-0 flex flex-col items-center"
                    style={{ left: t * pixelsPerSecond }}
                >
                    <div className="w-px h-2 bg-muted-foreground/40" />
                    <span className="text-[9px] text-muted-foreground/60 mt-0.5">
                        {formatTime(t)}
                    </span>
                </div>
            ))}
        </div>
    );
}

// ═══════════════════════════════════════════════════════════════════════════════
//  Marker Layer
// ═══════════════════════════════════════════════════════════════════════════════

function MarkerLayer({ pixelsPerSecond }: { pixelsPerSecond: number }) {
    const markers = useEditorStore((s) => s.markers);
    const removeMarker = useEditorStore((s) => s.removeMarker);

    if (markers.length === 0) return null;

    return (
        <div className="relative h-4 flex-shrink-0">
            {markers.map((m) => (
                <div
                    key={m.id}
                    className="absolute top-0 -translate-x-1/2 cursor-pointer group"
                    style={{ left: m.timestamp * pixelsPerSecond }}
                    title={m.label}
                >
                    <Flag
                        className="w-3 h-3"
                        style={{ color: m.color }}
                        onClick={() => removeMarker(m.id)}
                    />
                </div>
            ))}
        </div>
    );
}

// ═══════════════════════════════════════════════════════════════════════════════
//  Playhead
// ═══════════════════════════════════════════════════════════════════════════════

function Playhead({ pixelsPerSecond }: { pixelsPerSecond: number }) {
    const playheadPosition = useEditorStore((s) => s.playheadPosition);

    return (
        <div
            className="absolute top-0 bottom-0 w-0.5 bg-red-500 z-30 pointer-events-none"
            style={{ left: playheadPosition * pixelsPerSecond }}
        >
            <div className="w-3 h-3 bg-red-500 rounded-full -translate-x-[5px] -translate-y-1" />
        </div>
    );
}

// ═══════════════════════════════════════════════════════════════════════════════
//  Main Timeline Editor
// ═══════════════════════════════════════════════════════════════════════════════

export function TimelineEditor() {
    const clips = useEditorStore((s) => s.clips);
    const transitions = useEditorStore((s) => s.transitions);
    const selectedClipId = useEditorStore((s) => s.selectedClipId);
    const zoom = useEditorStore((s) => s.zoom);
    const setSelectedClipId = useEditorStore((s) => s.setSelectedClipId);
    const removeClip = useEditorStore((s) => s.removeClip);
    const reorderClips = useEditorStore((s) => s.reorderClips);
    const setZoom = useEditorStore((s) => s.setZoom);
    const setPlayheadPosition = useEditorStore((s) => s.setPlayheadPosition);
    const addMarker = useEditorStore((s) => s.addMarker);
    const playheadPosition = useEditorStore((s) => s.playheadPosition);

    const scrollRef = useRef<HTMLDivElement>(null);

    const sensors = useSensors(
        useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
        useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
    );

    // 20px per second at zoom 1
    const pixelsPerSecond = 20 * zoom;

    const totalDuration = useMemo(
        () => clips.reduce((sum, c) => sum + effectiveDuration(c), 0),
        [clips],
    );

    const transitionMap = useMemo(() => {
        const map: Record<number, EditorTransition> = {};
        transitions.forEach((t) => {
            map[t.after_clip_index] = t;
        });
        return map;
    }, [transitions]);

    const handleDragEnd = useCallback(
        (event: DragEndEvent) => {
            const { active, over } = event;
            if (!over || active.id === over.id) return;

            const fromIndex = clips.findIndex((c) => c.clip_id === active.id);
            const toIndex = clips.findIndex((c) => c.clip_id === over.id);
            if (fromIndex >= 0 && toIndex >= 0) {
                reorderClips(fromIndex, toIndex);
            }
        },
        [clips, reorderClips],
    );

    const handleTimelineClick = useCallback(
        (e: React.MouseEvent<HTMLDivElement>) => {
            if (!scrollRef.current) return;
            const rect = scrollRef.current.getBoundingClientRect();
            const scrollLeft = scrollRef.current.scrollLeft;
            const x = e.clientX - rect.left + scrollLeft;
            const time = Math.max(0, x / pixelsPerSecond);
            setPlayheadPosition(Math.min(time, totalDuration));
        },
        [pixelsPerSecond, totalDuration, setPlayheadPosition],
    );

    const handleAddMarker = useCallback(() => {
        addMarker({
            id: `m-${Date.now()}`,
            timestamp: playheadPosition,
            label: `Marker at ${formatTime(playheadPosition)}`,
            marker_type: 'note',
            color: '#3b82f6',
        });
    }, [playheadPosition, addMarker]);

    return (
        <div className="flex flex-col rounded-lg border bg-card overflow-hidden">
            {/* Toolbar */}
            <div className="flex items-center gap-2 px-3 py-2 border-b bg-muted/30">
                <span className="text-xs font-medium text-muted-foreground mr-2">Timeline</span>

                <Badge variant="outline" className="text-[10px] h-5">
                    {clips.length} clips
                </Badge>
                <Badge variant="outline" className="text-[10px] h-5">
                    {formatTime(totalDuration)}
                </Badge>

                <div className="flex-1" />

                <Button variant="ghost" size="icon" className="h-7 w-7" onClick={handleAddMarker} title="Add marker at playhead">
                    <Flag className="w-3.5 h-3.5" />
                </Button>

                <div className="flex items-center gap-1 border-l pl-2 ml-1">
                    <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7"
                        onClick={() => setZoom(zoom - 0.25)}
                        disabled={zoom <= 0.25}
                    >
                        <ZoomOut className="w-3.5 h-3.5" />
                    </Button>
                    <span className="text-[10px] text-muted-foreground w-8 text-center">
                        {Math.round(zoom * 100)}%
                    </span>
                    <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7"
                        onClick={() => setZoom(zoom + 0.25)}
                        disabled={zoom >= 4}
                    >
                        <ZoomIn className="w-3.5 h-3.5" />
                    </Button>
                </div>
            </div>

            {/* Scrollable area */}
            <div
                ref={scrollRef}
                className="relative overflow-x-auto overflow-y-hidden"
                style={{ minHeight: 120 }}
                onClick={handleTimelineClick}
            >
                <div
                    className="relative"
                    style={{ width: Math.max(totalDuration * pixelsPerSecond + 100, 600), minHeight: 120 }}
                >
                    <TimelineRuler totalDuration={totalDuration} pixelsPerSecond={pixelsPerSecond} />
                    <MarkerLayer pixelsPerSecond={pixelsPerSecond} />
                    <Playhead pixelsPerSecond={pixelsPerSecond} />

                    {/* Clip track */}
                    <div className="flex items-end gap-0 px-2 py-2" onClick={(e) => e.stopPropagation()}>
                        <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
                            <SortableContext items={clips.map((c) => c.clip_id)} strategy={horizontalListSortingStrategy}>
                                {clips.map((clip, i) => (
                                    <SortableClipBlock
                                        key={clip.clip_id}
                                        clip={clip}
                                        pixelsPerSecond={pixelsPerSecond}
                                        isSelected={selectedClipId === clip.clip_id}
                                        transition={transitionMap[i - 1]}
                                        onSelect={() => setSelectedClipId(clip.clip_id)}
                                        onRemove={() => removeClip(clip.clip_id)}
                                        onTrim={() => setSelectedClipId(clip.clip_id)}
                                    />
                                ))}
                            </SortableContext>
                        </DndContext>

                        {clips.length === 0 && (
                            <div className="flex items-center justify-center w-full h-16 text-sm text-muted-foreground">
                                Drag clips from the library to build your timeline
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
