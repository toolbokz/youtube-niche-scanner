'use client';

import React, { useMemo, useState } from 'react';
import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useEditorStore } from '@/store/editor-store';
import type { EditorClip } from '@/types';
import {
    Plus,
    Search,
    Film,
    Clock,
    Zap,
    Filter,
    SortAsc,
} from 'lucide-react';

// ═══════════════════════════════════════════════════════════════════════════════
//  Helpers
// ═══════════════════════════════════════════════════════════════════════════════

function formatTime(seconds: number): string {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s.toString().padStart(2, '0')}`;
}

const ENERGY_COLORS: Record<string, string> = {
    climax: 'text-red-400',
    high: 'text-orange-400',
    medium: 'text-blue-400',
    low: 'text-emerald-400',
};

// ═══════════════════════════════════════════════════════════════════════════════
//  Clip Card
// ═══════════════════════════════════════════════════════════════════════════════

function ClipCard({
    clip,
    isOnTimeline,
    onAddToTimeline,
}: {
    clip: EditorClip;
    isOnTimeline: boolean;
    onAddToTimeline: () => void;
}) {
    return (
        <div
            className={cn(
                'flex items-center gap-2 px-3 py-2 rounded-md border transition-colors',
                'hover:bg-accent/50',
                isOnTimeline
                    ? 'border-primary/30 bg-primary/5 opacity-60'
                    : 'border-border bg-card',
            )}
        >
            {/* Icon */}
            <div className="flex-shrink-0 w-8 h-8 rounded bg-muted flex items-center justify-center">
                <Film className="w-4 h-4 text-muted-foreground" />
            </div>

            {/* Info */}
            <div className="flex-1 min-w-0">
                <p className="text-xs font-medium truncate">
                    {clip.label || clip.segment_type || clip.clip_id.slice(0, 12)}
                </p>
                <div className="flex items-center gap-2 mt-0.5">
                    <span className="flex items-center gap-0.5 text-[10px] text-muted-foreground">
                        <Clock className="w-2.5 h-2.5" />
                        {formatTime(clip.duration_seconds)}
                    </span>
                    <span className={cn('flex items-center gap-0.5 text-[10px]', ENERGY_COLORS[clip.energy_level])}>
                        <Zap className="w-2.5 h-2.5" />
                        {clip.energy_level}
                    </span>
                    {clip.segment_type && (
                        <Badge variant="outline" className="text-[9px] h-3.5 px-1">
                            {clip.segment_type}
                        </Badge>
                    )}
                </div>
            </div>

            {/* Add button */}
            <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7 flex-shrink-0"
                onClick={onAddToTimeline}
                disabled={isOnTimeline}
                title={isOnTimeline ? 'Already on timeline' : 'Add to timeline'}
            >
                <Plus className={cn('w-3.5 h-3.5', isOnTimeline && 'opacity-30')} />
            </Button>
        </div>
    );
}

// ═══════════════════════════════════════════════════════════════════════════════
//  Clip Library Panel
// ═══════════════════════════════════════════════════════════════════════════════

type SortMode = 'position' | 'duration' | 'energy';

export function ClipLibraryPanel() {
    const clipLibrary = useEditorStore((s) => s.clipLibrary);
    const timelineClips = useEditorStore((s) => s.clips);
    const addClip = useEditorStore((s) => s.addClip);

    const [search, setSearch] = useState('');
    const [energyFilter, setEnergyFilter] = useState<string>('');
    const [sortMode, setSortMode] = useState<SortMode>('position');

    const timelineClipIds = useMemo(
        () => new Set(timelineClips.map((c) => c.clip_id)),
        [timelineClips],
    );

    const filteredClips = useMemo(() => {
        let result = [...clipLibrary];

        // Search
        if (search) {
            const q = search.toLowerCase();
            result = result.filter(
                (c) =>
                    c.clip_id.toLowerCase().includes(q) ||
                    c.source_video_id.toLowerCase().includes(q) ||
                    c.segment_type.toLowerCase().includes(q) ||
                    (c.label || '').toLowerCase().includes(q),
            );
        }

        // Energy filter
        if (energyFilter) {
            result = result.filter((c) => c.energy_level === energyFilter);
        }

        // Sort
        if (sortMode === 'duration') {
            result.sort((a, b) => b.duration_seconds - a.duration_seconds);
        } else if (sortMode === 'energy') {
            const order: Record<string, number> = { climax: 0, high: 1, medium: 2, low: 3 };
            result.sort((a, b) => (order[a.energy_level] ?? 9) - (order[b.energy_level] ?? 9));
        }
        // default: position

        return result;
    }, [clipLibrary, search, energyFilter, sortMode]);

    const energyLevels = useMemo(() => {
        const set = new Set(clipLibrary.map((c) => c.energy_level));
        return Array.from(set).sort();
    }, [clipLibrary]);

    const handleAdd = (clip: EditorClip) => {
        addClip({
            ...clip,
            position: timelineClips.length,
            trim_start: null,
            trim_end: null,
        });
    };

    return (
        <div className="flex flex-col h-full">
            {/* Header */}
            <div className="flex items-center gap-2 px-3 py-2 border-b">
                <Film className="w-4 h-4 text-muted-foreground" />
                <span className="text-sm font-medium">Clip Library</span>
                <Badge variant="outline" className="text-[10px] h-5 ml-auto">
                    {clipLibrary.length}
                </Badge>
            </div>

            {/* Filters */}
            <div className="px-3 py-2 space-y-2 border-b">
                <div className="relative">
                    <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
                    <Input
                        placeholder="Search clips..."
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        className="h-7 text-xs pl-7"
                    />
                </div>

                <div className="flex items-center gap-1.5 flex-wrap">
                    <Button
                        variant={energyFilter === '' ? 'secondary' : 'ghost'}
                        size="sm"
                        className="h-6 text-[10px] px-2"
                        onClick={() => setEnergyFilter('')}
                    >
                        All
                    </Button>
                    {energyLevels.map((level) => (
                        <Button
                            key={level}
                            variant={energyFilter === level ? 'secondary' : 'ghost'}
                            size="sm"
                            className="h-6 text-[10px] px-2"
                            onClick={() => setEnergyFilter(level === energyFilter ? '' : level)}
                        >
                            {level}
                        </Button>
                    ))}

                    <div className="flex-1" />

                    <Button
                        variant="ghost"
                        size="icon"
                        className="h-6 w-6"
                        onClick={() =>
                            setSortMode((s) =>
                                s === 'position' ? 'duration' : s === 'duration' ? 'energy' : 'position',
                            )
                        }
                        title={`Sort: ${sortMode}`}
                    >
                        <SortAsc className="w-3 h-3" />
                    </Button>
                </div>
            </div>

            {/* Clip list */}
            <div className="flex-1 overflow-y-auto px-2 py-2 space-y-1">
                {filteredClips.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-8 text-muted-foreground">
                        <Film className="w-8 h-8 opacity-30 mb-2" />
                        <p className="text-sm">No clips found</p>
                    </div>
                ) : (
                    filteredClips.map((clip) => (
                        <ClipCard
                            key={clip.clip_id}
                            clip={clip}
                            isOnTimeline={timelineClipIds.has(clip.clip_id)}
                            onAddToTimeline={() => handleAdd(clip)}
                        />
                    ))
                )}
            </div>
        </div>
    );
}
