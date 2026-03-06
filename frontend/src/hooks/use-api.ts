'use client';

import { useQuery, useMutation } from '@tanstack/react-query';
import {
    getHealth,
    runAnalysis,
    runDiscover,
    getReports,
    getReport,
    getCacheStats,
    getAINicheInsights,
    getAIVideoStrategy,
    getAITrendForecast,
    getDashboardData,
    getDiscoveries,
    getPersistedNiches,
    getNicheVideoIdeas,
    getVideoStrategies,
    getCompilationStrategies,
} from '@/services/api';
import type { AnalyzeRequest, DiscoverRequest } from '@/types';
import { useAppStore } from '@/store/app-store';

// ── Health ────────────────────────────────────────────────────────────────────

export function useHealth() {
    return useQuery({
        queryKey: ['health'],
        queryFn: getHealth,
        staleTime: 30_000,
        refetchInterval: 30_000,
    });
}

// ── Analysis ──────────────────────────────────────────────────────────────────

export function useAnalyze() {
    const setAnalysisData = useAppStore((s) => s.setAnalysisData);
    return useMutation({
        mutationFn: (params: AnalyzeRequest) => runAnalysis(params),
        onSuccess: (data) => setAnalysisData(data),
    });
}

export function useDiscover() {
    const setAnalysisData = useAppStore((s) => s.setAnalysisData);
    return useMutation({
        mutationFn: (params?: DiscoverRequest) => runDiscover(params),
        onSuccess: (data) => setAnalysisData(data),
    });
}

// ── Reports ───────────────────────────────────────────────────────────────────

export function useReports(search = '') {
    return useQuery({
        queryKey: ['reports', search],
        queryFn: () => getReports(search),
        staleTime: 10 * 60 * 1000, // 10 min — reports don't change often
    });
}

export function useReport(filename: string) {
    return useQuery({
        queryKey: ['report', filename],
        queryFn: () => getReport(filename),
        enabled: !!filename,
        staleTime: 30 * 60 * 1000, // 30 min — individual reports are immutable
    });
}

// ── Cache ─────────────────────────────────────────────────────────────────────

export function useCacheStats() {
    return useQuery({
        queryKey: ['cache-stats'],
        queryFn: getCacheStats,
        staleTime: 60_000, // 1 min
    });
}

// ── AI ────────────────────────────────────────────────────────────────────────

export function useAINicheInsights(topN = 5) {
    return useQuery({
        queryKey: ['ai-niche-insights', topN],
        queryFn: () => getAINicheInsights(topN),
        enabled: false, // manual trigger
        staleTime: 15 * 60 * 1000, // 15 min — AI results are expensive
        gcTime: 60 * 60 * 1000,     // 1 hour
    });
}

export function useAIVideoStrategy(niche: string) {
    return useQuery({
        queryKey: ['ai-video-strategy', niche],
        queryFn: () => getAIVideoStrategy(niche),
        enabled: false,
        staleTime: 15 * 60 * 1000,
        gcTime: 60 * 60 * 1000,
    });
}

export function useAITrendForecast() {
    return useQuery({
        queryKey: ['ai-trend-forecast'],
        queryFn: getAITrendForecast,
        enabled: false,
        staleTime: 15 * 60 * 1000,
        gcTime: 60 * 60 * 1000,
    });
}

// ── Dashboard batch ───────────────────────────────────────────────────────────

export function useDashboardData() {
    return useQuery({
        queryKey: ['dashboard-data'],
        queryFn: getDashboardData,
        staleTime: 2 * 60 * 1000, // 2 min
    });
}

// ── Persistence / History ─────────────────────────────────────────────────────

export function useDiscoveries(limit = 50) {
    return useQuery({
        queryKey: ['discoveries', limit],
        queryFn: () => getDiscoveries(limit),
        staleTime: 30_000,
    });
}

export function usePersistedNiches(limit = 100, minScore = 0) {
    return useQuery({
        queryKey: ['persisted-niches', limit, minScore],
        queryFn: () => getPersistedNiches(limit, minScore),
        staleTime: 30_000,
    });
}

export function useNicheVideoIdeas(nicheName: string) {
    return useQuery({
        queryKey: ['niche-video-ideas', nicheName],
        queryFn: () => getNicheVideoIdeas(nicheName),
        enabled: !!nicheName,
        staleTime: 60_000,
    });
}

export function useVideoStrategies(niche = '', limit = 50) {
    return useQuery({
        queryKey: ['video-strategies', niche, limit],
        queryFn: () => getVideoStrategies(niche, limit),
        staleTime: 30_000,
    });
}

export function useCompilationStrategies(niche = '', limit = 50) {
    return useQuery({
        queryKey: ['compilation-strategies', niche, limit],
        queryFn: () => getCompilationStrategies(niche, limit),
        staleTime: 30_000,
    });
}
