import { create } from 'zustand';
import type { AnalyzeResponse, NicheScore } from '@/types';

interface AppState {
    // Analysis data
    analysisData: AnalyzeResponse | null;
    setAnalysisData: (data: AnalyzeResponse) => void;
    clearAnalysisData: () => void;

    // Selected niche for detail view
    selectedNiche: NicheScore | null;
    setSelectedNiche: (niche: NicheScore | null) => void;

    // Sidebar state
    sidebarOpen: boolean;
    toggleSidebar: () => void;

    // Theme
    theme: 'light' | 'dark';
    setTheme: (theme: 'light' | 'dark') => void;
    toggleTheme: () => void;
}

export const useAppStore = create<AppState>((set) => ({
    analysisData: null,
    setAnalysisData: (data) => set({ analysisData: data }),
    clearAnalysisData: () => set({ analysisData: null }),

    selectedNiche: null,
    setSelectedNiche: (niche) => set({ selectedNiche: niche }),

    sidebarOpen: true,
    toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),

    theme:
        typeof window !== 'undefined'
            ? (localStorage.getItem('theme') as 'light' | 'dark') || 'dark'
            : 'dark',
    setTheme: (theme) => {
        if (typeof window !== 'undefined') localStorage.setItem('theme', theme);
        set({ theme });
    },
    toggleTheme: () =>
        set((s) => {
            const next = s.theme === 'dark' ? 'light' : 'dark';
            if (typeof window !== 'undefined') localStorage.setItem('theme', next);
            return { theme: next };
        }),
}));
