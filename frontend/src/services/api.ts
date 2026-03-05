import type {
    HealthResponse,
    AnalyzeRequest,
    AnalyzeResponse,
    DiscoverRequest,
    ReportSummary,
    ReportDetail,
    CompilationStrategy,
    VideoFactoryStartRequest,
    VideoFactoryStartResponse,
    VideoFactoryJobStatus,
    VideoFactoryJobSummary,
    VideoFactoryPreview,
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

// ── Compilation Video Intelligence ────────────────────────────────────────────

export async function getCompilationStrategy(
    niche: string,
    keywords: string[] = [],
    useAI = true,
) {
    const params = new URLSearchParams({ niche });
    if (keywords.length > 0) params.set('keywords', keywords.join(','));
    if (!useAI) params.set('use_ai', 'false');
    return request<{ status: string; compilation_strategy: CompilationStrategy }>(
        `/compilation-strategy?${params.toString()}`
    );
}

// ── Dashboard batch ───────────────────────────────────────────────────────────

export async function getDashboardData() {
    return request<{
        health: { status: string; version: string };
        cache: Record<string, unknown>;
        latest_report: Record<string, unknown> | null;
        recent_reports: Array<Record<string, unknown>>;
    }>('/dashboard-data');
}

// ── Video Factory ─────────────────────────────────────────────────────────────

export async function startVideoFactory(
    params: VideoFactoryStartRequest,
): Promise<VideoFactoryStartResponse> {
    return request<VideoFactoryStartResponse>('/video-factory/start', {
        method: 'POST',
        body: JSON.stringify(params),
    });
}

export async function getVideoFactoryStatus(
    jobId: string,
): Promise<VideoFactoryJobStatus> {
    return request<VideoFactoryJobStatus>(`/video-factory/status/${jobId}`);
}

export async function getVideoFactoryJobs(
    status = '',
    limit = 50,
): Promise<{ jobs: VideoFactoryJobSummary[]; total: number }> {
    const params = new URLSearchParams();
    if (status) params.set('status', status);
    params.set('limit', String(limit));
    return request(`/video-factory/jobs?${params.toString()}`);
}

export async function cancelVideoFactoryJob(jobId: string) {
    return request<{ status: string; job_id: string }>(`/video-factory/cancel/${jobId}`, {
        method: 'POST',
    });
}

export function getVideoFactoryDownloadUrl(jobId: string, file: 'video' | 'thumbnail' | 'metadata') {
    return `${API_BASE}/video-factory/download/${jobId}?file=${file}`;
}

export function getVideoFactoryStreamUrl(jobId: string) {
    return `${API_BASE}/video-factory/stream/${jobId}`;
}

export async function createVideoFromCI(
    params: VideoFactoryStartRequest,
): Promise<VideoFactoryStartResponse> {
    return request<VideoFactoryStartResponse>('/video-factory/create', {
        method: 'POST',
        body: JSON.stringify(params),
    });
}

export async function getVideoFactoryPreview(
    jobId: string,
): Promise<VideoFactoryPreview> {
    return request<VideoFactoryPreview>(`/video-factory/preview/${jobId}`);
}

export async function deleteVideoFactoryJob(
    jobId: string,
): Promise<{ status: string; job_id: string; files_deleted: boolean }> {
    return request(`/video-factory/delete/${jobId}`, { method: 'DELETE' });
}
