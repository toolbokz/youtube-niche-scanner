'use client';

import React, { useState } from 'react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { useEditorStore } from '@/store/editor-store';
import type { EditorTextOverlay } from '@/types';
import {
    Type,
    Plus,
    X,
    AlignCenter,
    AlignLeft,
    AlignRight,
    ChevronsUp,
    ChevronsDown,
} from 'lucide-react';

function formatTime(seconds: number): string {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s.toString().padStart(2, '0')}`;
}

const POSITION_OPTIONS: Array<{ value: EditorTextOverlay['position']; label: string }> = [
    { value: 'top', label: 'Top' },
    { value: 'center', label: 'Center' },
    { value: 'bottom', label: 'Bottom' },
    { value: 'top-left', label: 'Top-L' },
    { value: 'top-right', label: 'Top-R' },
    { value: 'bottom-left', label: 'Bot-L' },
    { value: 'bottom-right', label: 'Bot-R' },
];

// ═══════════════════════════════════════════════════════════════════════════════
//  Text Overlay Panel
// ═══════════════════════════════════════════════════════════════════════════════

export function TextOverlayPanel() {
    const overlays = useEditorStore((s) => s.textOverlays);
    const addTextOverlay = useEditorStore((s) => s.addTextOverlay);
    const updateTextOverlay = useEditorStore((s) => s.updateTextOverlay);
    const removeTextOverlay = useEditorStore((s) => s.removeTextOverlay);
    const playheadPosition = useEditorStore((s) => s.playheadPosition);
    const totalDuration = useEditorStore((s) => s.totalDuration);

    const [editingId, setEditingId] = useState<string | null>(null);

    const handleAdd = () => {
        const id = `txt-${Date.now()}`;
        const startAt = playheadPosition;
        const endAt = Math.min(startAt + 5, totalDuration());

        addTextOverlay({
            id,
            text: 'New Text',
            start_seconds: startAt,
            end_seconds: endAt,
            font_size: 48,
            color: '#ffffff',
            position: 'bottom',
            background_opacity: 0.5,
        });

        setEditingId(id);
    };

    return (
        <div className="flex flex-col gap-3 p-3">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <Type className="w-4 h-4 text-muted-foreground" />
                    <span className="text-sm font-medium">Text Overlays</span>
                    <Badge variant="outline" className="text-[10px] h-5">{overlays.length}</Badge>
                </div>
                <Button variant="outline" size="sm" className="h-7 text-xs" onClick={handleAdd}>
                    <Plus className="w-3 h-3 mr-1" />
                    Add
                </Button>
            </div>

            {/* Overlay list */}
            {overlays.length === 0 ? (
                <div className="flex flex-col items-center py-6 text-muted-foreground">
                    <Type className="w-8 h-8 opacity-30 mb-2" />
                    <p className="text-xs">No text overlays</p>
                    <p className="text-[10px] opacity-60">Click Add to create one</p>
                </div>
            ) : (
                <div className="space-y-2">
                    {overlays.map((overlay) => (
                        <OverlayEditor
                            key={overlay.id}
                            overlay={overlay}
                            isExpanded={editingId === overlay.id}
                            onToggle={() => setEditingId(editingId === overlay.id ? null : overlay.id)}
                            onUpdate={(updates) => updateTextOverlay(overlay.id, updates)}
                            onRemove={() => {
                                removeTextOverlay(overlay.id);
                                if (editingId === overlay.id) setEditingId(null);
                            }}
                        />
                    ))}
                </div>
            )}
        </div>
    );
}

// ═══════════════════════════════════════════════════════════════════════════════
//  Single overlay editor
// ═══════════════════════════════════════════════════════════════════════════════

function OverlayEditor({
    overlay,
    isExpanded,
    onToggle,
    onUpdate,
    onRemove,
}: {
    overlay: EditorTextOverlay;
    isExpanded: boolean;
    onToggle: () => void;
    onUpdate: (updates: Partial<EditorTextOverlay>) => void;
    onRemove: () => void;
}) {
    return (
        <div className="rounded-md border p-2 space-y-2 bg-muted/20">
            {/* Summary row */}
            <div className="flex items-center gap-2 cursor-pointer" onClick={onToggle}>
                <Type className="w-3.5 h-3.5 text-muted-foreground flex-shrink-0" />
                <span className="text-xs font-medium truncate flex-1">{overlay.text || 'Empty'}</span>
                <span className="text-[10px] text-muted-foreground">
                    {formatTime(overlay.start_seconds)}–{formatTime(overlay.end_seconds)}
                </span>
                <Button variant="ghost" size="icon" className="h-5 w-5 flex-shrink-0" onClick={(e) => { e.stopPropagation(); onRemove(); }}>
                    <X className="w-3 h-3" />
                </Button>
            </div>

            {/* Expanded editor */}
            {isExpanded && (
                <div className="space-y-2 pt-1 border-t">
                    {/* Text */}
                    <div>
                        <label className="text-[10px] text-muted-foreground">Text</label>
                        <Input
                            value={overlay.text}
                            onChange={(e) => onUpdate({ text: e.target.value })}
                            className="h-7 text-xs mt-0.5"
                        />
                    </div>

                    {/* Time range */}
                    <div className="grid grid-cols-2 gap-2">
                        <div>
                            <label className="text-[10px] text-muted-foreground">Start (s)</label>
                            <Input
                                type="number"
                                min={0}
                                step={0.5}
                                value={overlay.start_seconds}
                                onChange={(e) => onUpdate({ start_seconds: parseFloat(e.target.value) || 0 })}
                                className="h-7 text-xs mt-0.5"
                            />
                        </div>
                        <div>
                            <label className="text-[10px] text-muted-foreground">End (s)</label>
                            <Input
                                type="number"
                                min={0}
                                step={0.5}
                                value={overlay.end_seconds}
                                onChange={(e) => onUpdate({ end_seconds: parseFloat(e.target.value) || 0 })}
                                className="h-7 text-xs mt-0.5"
                            />
                        </div>
                    </div>

                    {/* Font size + color */}
                    <div className="grid grid-cols-2 gap-2">
                        <div>
                            <label className="text-[10px] text-muted-foreground">Font Size</label>
                            <Input
                                type="number"
                                min={12}
                                max={120}
                                value={overlay.font_size}
                                onChange={(e) => onUpdate({ font_size: parseInt(e.target.value) || 48 })}
                                className="h-7 text-xs mt-0.5"
                            />
                        </div>
                        <div>
                            <label className="text-[10px] text-muted-foreground">Color</label>
                            <div className="flex items-center gap-1 mt-0.5">
                                <input
                                    type="color"
                                    value={overlay.color}
                                    onChange={(e) => onUpdate({ color: e.target.value })}
                                    className="w-7 h-7 rounded border cursor-pointer"
                                />
                                <Input
                                    value={overlay.color}
                                    onChange={(e) => onUpdate({ color: e.target.value })}
                                    className="h-7 text-xs flex-1"
                                />
                            </div>
                        </div>
                    </div>

                    {/* Position */}
                    <div>
                        <label className="text-[10px] text-muted-foreground">Position</label>
                        <div className="flex gap-1 flex-wrap mt-1">
                            {POSITION_OPTIONS.map((opt) => (
                                <Button
                                    key={opt.value}
                                    variant={overlay.position === opt.value ? 'secondary' : 'outline'}
                                    size="sm"
                                    className="h-6 text-[10px] px-2"
                                    onClick={() => onUpdate({ position: opt.value })}
                                >
                                    {opt.label}
                                </Button>
                            ))}
                        </div>
                    </div>

                    {/* BG opacity */}
                    <div>
                        <label className="text-[10px] text-muted-foreground">
                            Background Opacity: {Math.round(overlay.background_opacity * 100)}%
                        </label>
                        <input
                            type="range"
                            min={0}
                            max={1}
                            step={0.05}
                            value={overlay.background_opacity}
                            onChange={(e) => onUpdate({ background_opacity: parseFloat(e.target.value) })}
                            className="w-full h-1 accent-primary mt-1"
                        />
                    </div>
                </div>
            )}
        </div>
    );
}
