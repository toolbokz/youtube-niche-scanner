import type {
    HealthResponse,
    AnalyzeRequest,
    AnalyzeResponse,
    DiscoverRequest,
    ReportSummary,
    ReportDetail,
} from '@/types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
    const res = await fetch(`${API_BASE}${path}`, {
        headers: { 'Content-Type': 'application/json' },
        ...options,
    });
    if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `API error: ${res.status}`);
    }
    return res.json();
}

// ── Health ────────────────────────────────────────────────────────────────────

export async function getHealth(): Promise<HealthResponse> {
    return request<HealthResponse>('/health');
}

// ── Analysis ──────────────────────────────────────────────────────────────────

export async function runAnalysis(params: AnalyzeRequest): Promise<AnalyzeResponse> {
    return request<AnalyzeResponse>('/analyze', {
        method: 'POST',
        body: JSON.stringify(params),
    });
}

export async function runDiscover(params: DiscoverRequest = {}): Promise<AnalyzeResponse> {
    return request<AnalyzeResponse>('/discover', {
        method: 'POST',
        body: JSON.stringify(params),
    });
}

// ── Niches (quick GET) ────────────────────────────────────────────────────────

export async function getNiches(keywords: string, topN = 10) {
    return request<{ top_niches: AnalyzeResponse['top_niches']; metadata: Record<string, unknown> }>(
        `/niches?keywords=${encodeURIComponent(keywords)}&top_n=${topN}`
    );
}

// ── Reports ───────────────────────────────────────────────────────────────────

export async function getReports(search = ''): Promise<{ reports: ReportSummary[] }> {
    const q = search ? `?search=${encodeURIComponent(search)}` : '';
    return request(`/reports${q}`);
}

export async function getReport(filename: string): Promise<ReportDetail> {
    return request(`/reports/${encodeURIComponent(filename)}`);
}

export function getReportDownloadUrl(filename: string, format: 'json' | 'markdown' = 'json') {
    return `${API_BASE}/reports/${encodeURIComponent(filename)}/download?format=${format}`;
}

// ── Cache ─────────────────────────────────────────────────────────────────────

export async function getCacheStats() {
    return request<Record<string, unknown>>('/cache/stats');
}

// ── AI endpoints ──────────────────────────────────────────────────────────────

export async function getAINicheInsights(topN = 5) {
    return request<{ status: string; niche_insights: Record<string, unknown> }>(
        `/ai/niche-insights?top_n=${topN}`
    );
}

export async function getAIVideoStrategy(niche: string, count = 15) {
    return request<{ status: string; video_strategy: Record<string, unknown> }>(
        `/ai/video-strategy?niche=${encodeURIComponent(niche)}&count=${count}`
    );
}

export async function getAITrendForecast() {
    return request<{ status: string; trend_forecast: Record<string, unknown> }>('/ai/trend-forecast');
}
