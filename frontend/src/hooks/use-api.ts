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
