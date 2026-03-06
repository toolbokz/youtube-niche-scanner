'use client';

import React, { useCallback, useEffect, useRef, useState } from 'react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useEditorStore } from '@/store/editor-store';
import {
    Play,
    Pause,
    SkipBack,
    SkipForward,
    Volume2,
    VolumeX,
    Maximize2,
    RotateCcw,
} from 'lucide-react';

// ═══════════════════════════════════════════════════════════════════════════════
//  Format helpers
// ═══════════════════════════════════════════════════════════════════════════════

function formatTime(seconds: number): string {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s.toString().padStart(2, '0')}`;
}

// ═══════════════════════════════════════════════════════════════════════════════
//  Preview Player
// ═══════════════════════════════════════════════════════════════════════════════

interface PreviewPlayerProps {
    streamUrl?: string | null;
    className?: string;
}

export function PreviewPlayer({ streamUrl, className }: PreviewPlayerProps) {
    const videoRef = useRef<HTMLVideoElement>(null);
    const [isPlaying, setIsPlaying] = useState(false);
    const [currentTime, setCurrentTime] = useState(0);
    const [duration, setDuration] = useState(0);
    const [muted, setMuted] = useState(false);
    const [seeking, setSeeking] = useState(false);

    const playheadPosition = useEditorStore((s) => s.playheadPosition);
    const setPlayheadPosition = useEditorStore((s) => s.setPlayheadPosition);
    const orientation = useEditorStore((s) => s.orientation);

    const togglePlay = useCallback(() => {
        const v = videoRef.current;
        if (!v) return;
        if (v.paused) {
            v.play();
            setIsPlaying(true);
        } else {
            v.pause();
            setIsPlaying(false);
        }
    }, []);

    const handleTimeUpdate = useCallback(() => {
        const v = videoRef.current;
        if (!v || seeking) return;
        setCurrentTime(v.currentTime);
        setPlayheadPosition(v.currentTime);
    }, [seeking, setPlayheadPosition]);

    const handleLoadedMetadata = useCallback(() => {
        const v = videoRef.current;
        if (v) setDuration(v.duration);
    }, []);

    const handleSeek = useCallback(
        (e: React.ChangeEvent<HTMLInputElement>) => {
            const time = parseFloat(e.target.value);
            setCurrentTime(time);
            if (videoRef.current) {
                videoRef.current.currentTime = time;
            }
            setPlayheadPosition(time);
        },
        [setPlayheadPosition],
    );

    const skipBack = useCallback(() => {
        if (videoRef.current) {
            videoRef.current.currentTime = Math.max(0, videoRef.current.currentTime - 5);
        }
    }, []);

    const skipForward = useCallback(() => {
        if (videoRef.current) {
            videoRef.current.currentTime = Math.min(
                duration,
                videoRef.current.currentTime + 5,
            );
        }
    }, [duration]);

    const toggleMute = useCallback(() => {
        if (videoRef.current) {
            videoRef.current.muted = !videoRef.current.muted;
            setMuted(videoRef.current.muted);
        }
    }, []);

    const toggleFullscreen = useCallback(() => {
        videoRef.current?.requestFullscreen?.();
    }, []);

    const restart = useCallback(() => {
        if (videoRef.current) {
            videoRef.current.currentTime = 0;
            setCurrentTime(0);
            setPlayheadPosition(0);
        }
    }, [setPlayheadPosition]);

    // Aspect ratio container
    const aspectClass = orientation === 'vertical' ? 'aspect-[9/16]' : 'aspect-video';

    return (
        <div className={cn('flex flex-col rounded-lg border bg-card overflow-hidden', className)}>
            {/* Video container */}
            <div className={cn('relative bg-black flex items-center justify-center', aspectClass)}>
                {streamUrl ? (
                    <video
                        ref={videoRef}
                        src={streamUrl}
                        className="w-full h-full object-contain"
                        onTimeUpdate={handleTimeUpdate}
                        onLoadedMetadata={handleLoadedMetadata}
                        onEnded={() => setIsPlaying(false)}
                        playsInline
                    />
                ) : (
                    <div className="flex flex-col items-center gap-2 text-muted-foreground">
                        <Play className="w-10 h-10 opacity-30" />
                        <p className="text-sm">No preview available</p>
                        <p className="text-xs opacity-60">Render a preview to see it here</p>
                    </div>
                )}
            </div>

            {/* Controls bar */}
            <div className="flex items-center gap-2 px-3 py-2 border-t bg-muted/30">
                <Button variant="ghost" size="icon" className="h-7 w-7" onClick={restart}>
                    <RotateCcw className="w-3.5 h-3.5" />
                </Button>
                <Button variant="ghost" size="icon" className="h-7 w-7" onClick={skipBack}>
                    <SkipBack className="w-3.5 h-3.5" />
                </Button>
                <Button variant="ghost" size="icon" className="h-8 w-8" onClick={togglePlay}>
                    {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                </Button>
                <Button variant="ghost" size="icon" className="h-7 w-7" onClick={skipForward}>
                    <SkipForward className="w-3.5 h-3.5" />
                </Button>

                {/* Scrub bar */}
                <input
                    type="range"
                    min={0}
                    max={duration || 100}
                    step={0.1}
                    value={currentTime}
                    onChange={handleSeek}
                    onMouseDown={() => setSeeking(true)}
                    onMouseUp={() => setSeeking(false)}
                    className="flex-1 h-1 accent-primary cursor-pointer"
                />

                <span className="text-[10px] text-muted-foreground tabular-nums w-20 text-center">
                    {formatTime(currentTime)} / {formatTime(duration)}
                </span>

                <Button variant="ghost" size="icon" className="h-7 w-7" onClick={toggleMute}>
                    {muted ? <VolumeX className="w-3.5 h-3.5" /> : <Volume2 className="w-3.5 h-3.5" />}
                </Button>
                <Button variant="ghost" size="icon" className="h-7 w-7" onClick={toggleFullscreen}>
                    <Maximize2 className="w-3.5 h-3.5" />
                </Button>
            </div>
        </div>
    );
}
