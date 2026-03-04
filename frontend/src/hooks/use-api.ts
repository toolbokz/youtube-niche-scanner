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
} from '@/services/api';
import type { AnalyzeRequest, DiscoverRequest } from '@/types';
import { useAppStore } from '@/store/app-store';

// ── Health ────────────────────────────────────────────────────────────────────

export function useHealth() {
    return useQuery({
        queryKey: ['health'],
        queryFn: getHealth,
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
    });
}

export function useReport(filename: string) {
    return useQuery({
        queryKey: ['report', filename],
        queryFn: () => getReport(filename),
        enabled: !!filename,
    });
}

// ── Cache ─────────────────────────────────────────────────────────────────────

export function useCacheStats() {
    return useQuery({
        queryKey: ['cache-stats'],
        queryFn: getCacheStats,
    });
}

// ── AI ────────────────────────────────────────────────────────────────────────

export function useAINicheInsights(topN = 5) {
    return useQuery({
        queryKey: ['ai-niche-insights', topN],
        queryFn: () => getAINicheInsights(topN),
        enabled: false, // manual trigger
    });
}

export function useAIVideoStrategy(niche: string) {
    return useQuery({
        queryKey: ['ai-video-strategy', niche],
        queryFn: () => getAIVideoStrategy(niche),
        enabled: false,
    });
}

export function useAITrendForecast() {
    return useQuery({
        queryKey: ['ai-trend-forecast'],
        queryFn: getAITrendForecast,
        enabled: false,
    });
}
