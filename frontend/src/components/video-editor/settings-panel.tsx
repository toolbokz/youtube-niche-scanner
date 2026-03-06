'use client';

import React from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { useEditorStore } from '@/store/editor-store';
import {
    Monitor,
    Smartphone,
    Clock,
    Gauge,
    Volume2,
    Settings,
} from 'lucide-react';

// ═══════════════════════════════════════════════════════════════════════════════
//  Settings Panel – video-level controls
// ═══════════════════════════════════════════════════════════════════════════════

export function SettingsPanel() {
    const orientation = useEditorStore((s) => s.orientation);
    const setOrientation = useEditorStore((s) => s.setOrientation);
    const resolution = useEditorStore((s) => s.resolution);
    const setResolution = useEditorStore((s) => s.setResolution);
    const targetDuration = useEditorStore((s) => s.targetDuration);
    const setTargetDuration = useEditorStore((s) => s.setTargetDuration);
    const maxSceneDuration = useEditorStore((s) => s.maxSceneDuration);
    const setMaxSceneDuration = useEditorStore((s) => s.setMaxSceneDuration);
    const backgroundAudio = useEditorStore((s) => s.backgroundAudio);
    const setBackgroundAudio = useEditorStore((s) => s.setBackgroundAudio);
    const totalDuration = useEditorStore((s) => s.totalDuration);

    const currentTotal = totalDuration();
    const durationMinutes = Math.round(targetDuration / 60);

    return (
        <div className="flex flex-col gap-4 p-3">
            {/* Header */}
            <div className="flex items-center gap-2">
                <Settings className="w-4 h-4 text-muted-foreground" />
                <span className="text-sm font-medium">Video Settings</span>
            </div>

            {/* Duration summary */}
            <div className="rounded-md border p-2 bg-muted/30 space-y-1">
                <div className="flex items-center justify-between">
                    <span className="text-[11px] text-muted-foreground">Timeline duration</span>
                    <Badge variant="outline" className="text-[10px] h-4">
                        {Math.floor(currentTotal / 60)}m {Math.floor(currentTotal % 60)}s
                    </Badge>
                </div>
                <div className="flex items-center justify-between">
                    <span className="text-[11px] text-muted-foreground">Target duration</span>
                    <Badge variant="outline" className="text-[10px] h-4">
                        {durationMinutes}m
                    </Badge>
                </div>
                {currentTotal > targetDuration && (
                    <p className="text-[10px] text-amber-500">
                        Timeline exceeds target by {Math.round(currentTotal - targetDuration)}s — lowest-energy clips may be trimmed during render.
                    </p>
                )}
            </div>

            {/* Orientation */}
            <div>
                <label className="text-[11px] font-medium text-muted-foreground flex items-center gap-1 mb-1">
                    <Monitor className="w-3 h-3" />
                    Orientation
                </label>
                <div className="flex gap-1">
                    <Button
                        variant={orientation === 'horizontal' ? 'secondary' : 'outline'}
                        size="sm"
                        className="h-7 text-xs flex-1"
                        onClick={() => setOrientation('horizontal')}
                    >
                        <Monitor className="w-3 h-3 mr-1" />
                        Landscape
                    </Button>
                    <Button
                        variant={orientation === 'vertical' ? 'secondary' : 'outline'}
                        size="sm"
                        className="h-7 text-xs flex-1"
                        onClick={() => setOrientation('vertical')}
                    >
                        <Smartphone className="w-3 h-3 mr-1" />
                        Portrait
                    </Button>
                </div>
            </div>

            {/* Resolution */}
            <div>
                <label className="text-[11px] font-medium text-muted-foreground mb-1">Resolution</label>
                <div className="flex gap-1 flex-wrap mt-1">
                    {(['720p', '1080p', '1440p', '4k'] as const).map((r) => (
                        <Button
                            key={r}
                            variant={resolution === r ? 'secondary' : 'outline'}
                            size="sm"
                            className="h-7 text-xs px-3"
                            onClick={() => setResolution(r)}
                        >
                            {r}
                        </Button>
                    ))}
                </div>
            </div>

            {/* Target duration */}
            <div>
                <label className="text-[11px] font-medium text-muted-foreground flex items-center gap-1 mb-1">
                    <Clock className="w-3 h-3" />
                    Target Duration (minutes)
                </label>
                <div className="flex gap-1 flex-wrap">
                    {[3, 5, 8, 10, 15].map((m) => (
                        <Button
                            key={m}
                            variant={durationMinutes === m ? 'secondary' : 'outline'}
                            size="sm"
                            className="h-7 text-xs px-3"
                            onClick={() => setTargetDuration(m * 60)}
                        >
                            {m}m
                        </Button>
                    ))}
                </div>
            </div>

            {/* Max scene duration */}
            <div>
                <label className="text-[11px] font-medium text-muted-foreground flex items-center gap-1">
                    <Gauge className="w-3 h-3" />
                    Max Scene Duration (sec)
                </label>
                <div className="flex items-center gap-2 mt-1">
                    <Input
                        type="number"
                        min={5}
                        max={120}
                        step={5}
                        value={maxSceneDuration ?? ''}
                        placeholder="No limit"
                        onChange={(e) => {
                            const v = e.target.value ? parseFloat(e.target.value) : null;
                            setMaxSceneDuration(v);
                        }}
                        className="h-7 text-xs flex-1"
                    />
                    {maxSceneDuration !== null && (
                        <Button
                            variant="ghost"
                            size="sm"
                            className="h-7 text-xs"
                            onClick={() => setMaxSceneDuration(null)}
                        >
                            Clear
                        </Button>
                    )}
                </div>
                <p className="text-[10px] text-muted-foreground mt-0.5">
                    Clips exceeding this will be auto-trimmed during rendering.
                </p>
            </div>

            {/* Background Audio */}
            <div>
                <label className="text-[11px] font-medium text-muted-foreground flex items-center gap-1 mb-1">
                    <Volume2 className="w-3 h-3" />
                    Background Audio
                </label>
                <div className="flex gap-1 flex-wrap">
                    {(['none', 'ambient', 'energetic'] as const).map((a) => (
                        <Button
                            key={a}
                            variant={backgroundAudio === a ? 'secondary' : 'outline'}
                            size="sm"
                            className="h-7 text-xs px-3 capitalize"
                            onClick={() => setBackgroundAudio(a)}
                        >
                            {a}
                        </Button>
                    ))}
                </div>
            </div>
        </div>
    );
}
