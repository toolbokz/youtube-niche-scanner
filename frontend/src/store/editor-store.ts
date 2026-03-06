import { create } from 'zustand';
import type {
    EditorClip,
    EditorTransition,
    EditorMarker,
    EditorTextOverlay,
    EditorTimeline,
} from '@/types';

// ═══════════════════════════════════════════════════════════════════════════════
//  Editor View Modes
// ═══════════════════════════════════════════════════════════════════════════════

export type EditorPanel = 'timeline' | 'clips' | 'settings' | 'text';
export type EditorViewMode = 'editor' | 'review';

// ═══════════════════════════════════════════════════════════════════════════════
//  Store Interface
// ═══════════════════════════════════════════════════════════════════════════════

interface EditorState {
    // ── Source job ─────────────────────────────────────────────────────
    jobId: string | null;
    niche: string;
    setJob: (jobId: string, niche: string) => void;
    clearJob: () => void;

    // ── Timeline clips ────────────────────────────────────────────────
    clips: EditorClip[];
    setClips: (clips: EditorClip[]) => void;
    addClip: (clip: EditorClip) => void;
    removeClip: (clipId: string) => void;
    updateClip: (clipId: string, updates: Partial<EditorClip>) => void;
    reorderClips: (fromIndex: number, toIndex: number) => void;
    trimClip: (clipId: string, trimStart: number | null, trimEnd: number | null) => void;

    // ── Transitions ───────────────────────────────────────────────────
    transitions: EditorTransition[];
    setTransitions: (t: EditorTransition[]) => void;
    setTransitionAt: (afterIndex: number, type: EditorTransition['type'], duration?: number) => void;

    // ── Markers ───────────────────────────────────────────────────────
    markers: EditorMarker[];
    setMarkers: (m: EditorMarker[]) => void;
    addMarker: (m: EditorMarker) => void;
    removeMarker: (id: string) => void;

    // ── Text Overlays ─────────────────────────────────────────────────
    textOverlays: EditorTextOverlay[];
    setTextOverlays: (o: EditorTextOverlay[]) => void;
    addTextOverlay: (o: EditorTextOverlay) => void;
    updateTextOverlay: (id: string, updates: Partial<EditorTextOverlay>) => void;
    removeTextOverlay: (id: string) => void;

    // ── Video Settings ────────────────────────────────────────────────
    orientation: 'horizontal' | 'vertical';
    setOrientation: (o: 'horizontal' | 'vertical') => void;
    resolution: '720p' | '1080p' | '1440p' | '4k';
    setResolution: (r: '720p' | '1080p' | '1440p' | '4k') => void;
    targetDuration: number;
    setTargetDuration: (d: number) => void;
    maxSceneDuration: number | null;
    setMaxSceneDuration: (d: number | null) => void;
    backgroundAudio: 'none' | 'ambient' | 'energetic';
    setBackgroundAudio: (a: 'none' | 'ambient' | 'energetic') => void;

    // ── Playback / Selection ──────────────────────────────────────────
    selectedClipId: string | null;
    setSelectedClipId: (id: string | null) => void;
    playheadPosition: number;
    setPlayheadPosition: (p: number) => void;
    isPlaying: boolean;
    setIsPlaying: (p: boolean) => void;
    zoom: number; // 1 = 1x, 2 = 2x, 0.5 = zoom out
    setZoom: (z: number) => void;

    // ── Active panel ──────────────────────────────────────────────────
    activePanel: EditorPanel;
    setActivePanel: (p: EditorPanel) => void;
    viewMode: EditorViewMode;
    setViewMode: (m: EditorViewMode) => void;

    // ── Render state ──────────────────────────────────────────────────
    currentRenderId: string | null;
    setCurrentRenderId: (id: string | null) => void;
    lastRenderUrl: string | null;
    setLastRenderUrl: (url: string | null) => void;

    // ── Clip library (available but not on timeline) ──────────────────
    clipLibrary: EditorClip[];
    setClipLibrary: (clips: EditorClip[]) => void;

    // ── Dirty flag ────────────────────────────────────────────────────
    isDirty: boolean;
    markDirty: () => void;
    markClean: () => void;

    // ── Computed helpers ──────────────────────────────────────────────
    totalDuration: () => number;
    getTimeline: () => EditorTimeline;

    // ── Bulk load from saved timeline ─────────────────────────────────
    loadTimeline: (t: EditorTimeline) => void;
    resetEditor: () => void;
}

// ═══════════════════════════════════════════════════════════════════════════════
//  Helpers
// ═══════════════════════════════════════════════════════════════════════════════

function effectiveDuration(clip: EditorClip): number {
    const start = clip.trim_start ?? clip.start_seconds;
    const end = clip.trim_end ?? clip.end_seconds;
    return Math.max(0, end - start);
}

function reindex(clips: EditorClip[]): EditorClip[] {
    return clips.map((c, i) => ({ ...c, position: i }));
}

// ═══════════════════════════════════════════════════════════════════════════════
//  Store
// ═══════════════════════════════════════════════════════════════════════════════

export const useEditorStore = create<EditorState>((set, get) => ({
    // Source job
    jobId: null,
    niche: '',
    setJob: (jobId, niche) => set({ jobId, niche }),
    clearJob: () => set({ jobId: null, niche: '' }),

    // Timeline clips
    clips: [],
    setClips: (clips) => set({ clips: reindex(clips), isDirty: true }),
    addClip: (clip) =>
        set((s) => ({
            clips: reindex([...s.clips, clip]),
            isDirty: true,
        })),
    removeClip: (clipId) =>
        set((s) => ({
            clips: reindex(s.clips.filter((c) => c.clip_id !== clipId)),
            isDirty: true,
        })),
    updateClip: (clipId, updates) =>
        set((s) => ({
            clips: s.clips.map((c) => (c.clip_id === clipId ? { ...c, ...updates } : c)),
            isDirty: true,
        })),
    reorderClips: (fromIndex, toIndex) =>
        set((s) => {
            const arr = [...s.clips];
            const [moved] = arr.splice(fromIndex, 1);
            arr.splice(toIndex, 0, moved);
            return { clips: reindex(arr), isDirty: true };
        }),
    trimClip: (clipId, trimStart, trimEnd) =>
        set((s) => ({
            clips: s.clips.map((c) =>
                c.clip_id === clipId ? { ...c, trim_start: trimStart, trim_end: trimEnd } : c,
            ),
            isDirty: true,
        })),

    // Transitions
    transitions: [],
    setTransitions: (t) => set({ transitions: t, isDirty: true }),
    setTransitionAt: (afterIndex, type, duration = 0.5) =>
        set((s) => {
            const existing = s.transitions.filter((t) => t.after_clip_index !== afterIndex);
            return {
                transitions: [...existing, { type, duration_seconds: duration, after_clip_index: afterIndex }],
                isDirty: true,
            };
        }),

    // Markers
    markers: [],
    setMarkers: (m) => set({ markers: m, isDirty: true }),
    addMarker: (m) => set((s) => ({ markers: [...s.markers, m], isDirty: true })),
    removeMarker: (id) => set((s) => ({ markers: s.markers.filter((m) => m.id !== id), isDirty: true })),

    // Text Overlays
    textOverlays: [],
    setTextOverlays: (o) => set({ textOverlays: o, isDirty: true }),
    addTextOverlay: (o) => set((s) => ({ textOverlays: [...s.textOverlays, o], isDirty: true })),
    updateTextOverlay: (id, updates) =>
        set((s) => ({
            textOverlays: s.textOverlays.map((o) => (o.id === id ? { ...o, ...updates } : o)),
            isDirty: true,
        })),
    removeTextOverlay: (id) =>
        set((s) => ({
            textOverlays: s.textOverlays.filter((o) => o.id !== id),
            isDirty: true,
        })),

    // Video Settings
    orientation: 'horizontal',
    setOrientation: (o) => set({ orientation: o, isDirty: true }),
    resolution: '1080p',
    setResolution: (r) => set({ resolution: r, isDirty: true }),
    targetDuration: 480,
    setTargetDuration: (d) => set({ targetDuration: d, isDirty: true }),
    maxSceneDuration: null,
    setMaxSceneDuration: (d) => set({ maxSceneDuration: d, isDirty: true }),
    backgroundAudio: 'none',
    setBackgroundAudio: (a) => set({ backgroundAudio: a, isDirty: true }),

    // Playback
    selectedClipId: null,
    setSelectedClipId: (id) => set({ selectedClipId: id }),
    playheadPosition: 0,
    setPlayheadPosition: (p) => set({ playheadPosition: p }),
    isPlaying: false,
    setIsPlaying: (p) => set({ isPlaying: p }),
    zoom: 1,
    setZoom: (z) => set({ zoom: Math.max(0.25, Math.min(4, z)) }),

    // Active panel
    activePanel: 'timeline',
    setActivePanel: (p) => set({ activePanel: p }),
    viewMode: 'editor',
    setViewMode: (m) => set({ viewMode: m }),

    // Render
    currentRenderId: null,
    setCurrentRenderId: (id) => set({ currentRenderId: id }),
    lastRenderUrl: null,
    setLastRenderUrl: (url) => set({ lastRenderUrl: url }),

    // Clip library
    clipLibrary: [],
    setClipLibrary: (clips) => set({ clipLibrary: clips }),

    // Dirty
    isDirty: false,
    markDirty: () => set({ isDirty: true }),
    markClean: () => set({ isDirty: false }),

    // Computed
    totalDuration: () => get().clips.reduce((sum, c) => sum + effectiveDuration(c), 0),

    getTimeline: () => ({
        clips: get().clips,
        transitions: get().transitions,
        markers: get().markers,
        text_overlays: get().textOverlays,
        orientation: get().orientation,
        resolution: get().resolution,
        target_duration_seconds: get().targetDuration,
        max_scene_duration: get().maxSceneDuration,
        background_audio: get().backgroundAudio,
    }),

    // Bulk load
    loadTimeline: (t) =>
        set({
            clips: reindex(t.clips),
            transitions: t.transitions,
            markers: t.markers,
            textOverlays: t.text_overlays,
            orientation: t.orientation,
            resolution: t.resolution,
            targetDuration: t.target_duration_seconds,
            maxSceneDuration: t.max_scene_duration,
            backgroundAudio: t.background_audio,
            isDirty: false,
        }),

    resetEditor: () =>
        set({
            jobId: null,
            niche: '',
            clips: [],
            transitions: [],
            markers: [],
            textOverlays: [],
            orientation: 'horizontal',
            resolution: '1080p',
            targetDuration: 480,
            maxSceneDuration: null,
            backgroundAudio: 'none',
            selectedClipId: null,
            playheadPosition: 0,
            isPlaying: false,
            zoom: 1,
            activePanel: 'timeline',
            viewMode: 'editor',
            currentRenderId: null,
            lastRenderUrl: null,
            clipLibrary: [],
            isDirty: false,
        }),
}));
