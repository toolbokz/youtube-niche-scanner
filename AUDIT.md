# Growth Strategist — Comprehensive Codebase Audit

**Generated:** Audit of every module and file in the repository.

---

## Table of Contents

1. [File-by-File Inventory](#1-file-by-file-inventory)
2. [Cross-Cutting Issues](#2-cross-cutting-issues)
3. [Pipeline Wiring Verification](#3-pipeline-wiring-verification)
4. [Frontend ↔ Backend Schema Mismatches](#4-frontend--backend-schema-mismatches)
5. [API Endpoint Inventory](#5-api-endpoint-inventory)
6. [Dead Code & Unused Modules](#6-dead-code--unused-modules)
7. [Missing Dependencies](#7-missing-dependencies)
8. [Configuration Gaps](#8-configuration-gaps)
9. [Test Coverage Assessment](#9-test-coverage-assessment)
10. [Documentation Drift](#10-documentation-drift)
11. [Priority Fix List](#11-priority-fix-list)

---

## 1. File-by-File Inventory

### Root Files

| File | Lines | Summary | Issues |
|------|------:|---------|--------|
| `main.py` | 15 | Entry point — calls `cli()` | None |
| `config.yaml` | ~90 | Default dev config matching Settings defaults | Missing `vertex_ai:` section (relies on Python defaults) |
| `pyproject.toml` | 16 | Project metadata, pytest asyncio_mode=auto, mypy strict | No `[project.dependencies]` — relies on `requirements.txt` |
| `requirements.txt` | 32 | All Python deps | **Missing `Pillow`** (used by `thumbnail_analysis`); **missing `tenacity`** (imported in `base.py`) |
| `Dockerfile` | 22 | Python 3.11-slim, installs deps, creates data dirs, CMD serve | No `EXPOSE 8000` directive; no health check |
| `README.md` | 315 | Project documentation | **Stale tech stack** — lists Plotly Dash, dash-cytoscape, NetworkX, dash-bootstrap-components; frontend is actually Next.js/React. **Ranking weights in the docs differ from code.** **API table incomplete.** |
| `PERFORMANCE.md` | 186 | Performance optimization guide | Accurate and well-maintained |

### `app/` — Core

| File | Lines | Summary | Issues |
|------|------:|---------|--------|
| `app/__init__.py` | 4 | Version string `1.0.0` | None |
| `app/core/__init__.py` | 7 | Re-exports from models + `get_cache` | Wildcard `from .models import *`  — exports ~40 symbols implicitly; prefer explicit exports |
| `app/core/models.py` | ~280 | All 30+ Pydantic v2 schemas (enums, connector results, analysis metrics, scoring, strategy, channel, report) | `SearchResult` has `published_date: str` but `youtube_api.py` tries to set `published_at`, `like_count`, `comment_count` — **fields silently dropped by Pydantic v2** (data lost). `NicheReport.discovery_insights` declared but never populated by any engine. |
| `app/core/pipeline.py` | ~270 | `PipelineOrchestrator` — 11-step async pipeline with bounded parallel niche analysis (Semaphore=6) | Solid. Uses `asyncio.gather` effectively. All 18 engines imported and wired. |
| `app/core/cache.py` | 339 | Multi-tier cache: LRU memory (4096) → Redis (optional) → disk (orjson, 256-shard) | Well-implemented. `_RedisLayer` gracefully falls back on import/connection failure. |
| `app/core/logging.py` | ~40 | structlog configuration with `setup_logging()` / `get_logger()` | None |

### `app/config/`

| File | Lines | Summary | Issues |
|------|------:|---------|--------|
| `app/config/__init__.py` | 5 | Re-exports Settings, load/reset | None |
| `app/config/settings.py` | ~240 | Pydantic Settings with 10 config sub-models, YAML loading, `_ENV_MAP` for `GS_*` env overrides | `VertexAIConfig.client_id` field exists but has no practical use (Vertex AI uses service account credentials, not client ID). Ranking weights in README (demand=0.30, competition=0.25) don't match code (demand=0.25, competition=0.20). |

### `app/database/`

| File | Lines | Summary | Issues |
|------|------:|---------|--------|
| `app/database/__init__.py` | 30 | Re-exports all ORM models + DB functions | None |
| `app/database/models.py` | ~220 | SQLAlchemy ORM: 7 tables (KeywordRecord, NicheRecord, VideoIdeaRecord, SearchResultRecord, TrendRecord, AnalysisRun, AIInsightRecord), composite indexes, SQLite WAL pragmas | **`NicheRecord` missing columns** — no `viral_opportunity_score` or `topic_velocity_score`, but `NicheScore` Pydantic model has them and the ranking engine populates them. DB schema is stale. |

### `app/api/`

| File | Lines | Summary | Issues |
|------|------:|---------|--------|
| `app/api/__init__.py` | 4 | Imports `app` and `create_app` | None |
| `app/api/routes.py` | 576 | FastAPI app with 15 endpoints, CORS, GZip, SecurityHeaders, Server-Timing middleware, ORJSONResponse | `AnalyzeResponse` / `AnalyzeRequest` Pydantic models defined inline — could live in `core/models.py`. `_bg_tasks` dict for async pipeline tracking has no eviction/cleanup of completed tasks (memory leak for long-running servers). |

### `app/ai/`

| File | Lines | Summary | Issues |
|------|------:|---------|--------|
| `app/ai/__init__.py` | 2 | Empty docstring | None |
| `app/ai/client.py` | ~180 | `VertexAIClient` — lazy-init Gemini 2.0 Flash + Pro, JSON parser | Solid. `_parse_json_response` handles fenced and plain JSON. Singleton via `get_ai_client()`. |
| `app/ai/service.py` | ~300 | Service layer with DB-backed caching. Functions: `analyze_niches`, `interpret_viral_opportunities`, `generate_video_strategy`, `analyze_thumbnail_patterns`, `forecast_trends`, `get_quick_niche_insight`, `run_full_ai_analysis` | Robust error handling. All AI calls cached in `AIInsightRecord`. `run_full_ai_analysis` parallelizes via `asyncio.gather`. |
| `app/ai/prompts/__init__.py` | 2 | Empty docstring | None |
| `app/ai/prompts/niche_analysis.py` | ~100 | `niche_analysis_prompt()` + `quick_niche_insight_prompt()` | None |
| `app/ai/prompts/strategy_generation.py` | ~100 | `video_strategy_prompt()` + `viral_opportunity_prompt()` | None |
| `app/ai/prompts/trend_interpretation.py` | ~80 | `trend_forecast_prompt()` | None |
| `app/ai/prompts/thumbnail_analysis_ai.py` | ~80 | `thumbnail_strategy_prompt()` | None |

### `app/connectors/`

| File | Lines | Summary | Issues |
|------|------:|---------|--------|
| `app/connectors/__init__.py` | ~5 | Re-exports | None |
| `app/connectors/base.py` | ~100 | ABC with httpx async client, rate limiting (asyncio.Lock), cache integration | **`tenacity` imported but retry decorator never applied** to any method. Dead import. |
| `app/connectors/google_trends.py` | ~130 | pytrends (sync, run in executor), momentum calc, batch support | `pytrends` is synchronous — correctly wrapped with `asyncio.to_thread`/executor. Good. |
| `app/connectors/youtube_search.py` | ~160 | Scrapes YouTube HTML, parses `ytInitialData` JSON | Brittle — any YouTube HTML change breaks this. No fallback. Expected for a scraper. |
| `app/connectors/youtube_api.py` | ~120 | YouTube Data API v3 (optional, requires API key) | **`SearchResult` field mismatch** — sets `published_at`, `like_count`, `comment_count` which DON'T exist on the Pydantic model. Pydantic v2 silently ignores extra fields → data is **lost**. |
| `app/connectors/youtube_autocomplete.py` | ~100 | YouTube suggest API (JSONP parsing), a-z prefix expansion | None |
| `app/connectors/keyword_scraper.py` | ~90 | Google + Bing autocomplete APIs, concurrent expansion | None |
| `app/connectors/reddit.py` | ~120 | Reddit public JSON API, 24h/7d post counts, spike detection, batch support | None |

### `app/` — Analysis Engines (18 total)

| File | Lines | Sync/Async | Summary | Issues |
|------|------:|:----------:|---------|--------|
| `app/discovery_engine/engine.py` | ~200 | Async | Auto-discovers trending topics from GT, YT autocomplete, Reddit, YT search. 20 hardcoded categories. | None |
| `app/keyword_expansion/engine.py` | ~80 | Async | Expands seeds via YT autocomplete + keyword scraper, question prefixes | None |
| `app/niche_clustering/engine.py` | ~180 | Sync | TF-IDF + AgglomerativeClustering (sklearn) | None |
| `app/competition_analysis/engine.py` | ~140 | Async | YouTube search → competition score from views, subs, saturation, production quality proxy | None |
| `app/virality_prediction/engine.py` | ~140 | Sync | Regex pattern matching for curiosity, emotion, shock, info asymmetry, novelty, relatability | None |
| `app/ctr_prediction/engine.py` | ~170 | Sync | Power words, curiosity triggers, title length, numbers/lists, pattern interrupts, visual concepts | None |
| `app/faceless_viability/engine.py` | ~130 | Sync | 6 format pattern lists, camera-required penalty | None |
| `app/ranking_engine/engine.py` | ~130 | Sync | 7-signal weighted scoring, reads weights from config | None |
| `app/trend_discovery/engine.py` | ~150 | Async | Multi-signal: GT(35%) + Reddit(20%) + autocomplete(20%) + velocity(25%) | None |
| `app/viral_opportunity_detector/engine.py` | ~190 | Async | Finds <50K sub channels with >500K view breakouts. Dual threshold with relaxed mode. | None |
| `app/topic_velocity/engine.py` | ~200 | Async | Weekly upload growth rate + acceleration. 5-week windows. | None |
| `app/thumbnail_analysis/engine.py` | 468 | Async | Downloads thumbnails, Pillow analysis (colors, text/face detection, contrast, brightness), style clustering | **`Pillow` not in `requirements.txt`** — graceful fallback to heuristic, but should be listed. |
| `app/thumbnail_strategy/engine.py` | ~170 | Sync | Emotion→visual concept mapping, color palettes, layout descriptions | None |
| `app/title_generation/engine.py` | ~120 | Sync | Curiosity gap, keyword-optimized, alternative title formulas | None |
| `app/description_generation/engine.py` | ~110 | Sync | SEO descriptions with intro, keyword block, chapters, CTA, affiliate positioning | None |
| `app/monetization_engine/engine.py` | ~150 | Sync | Affiliate products, sponsorship categories, digital products, lead magnets | None |
| `app/video_strategy/engine.py` | ~280 | Sync | `ChannelConcept` + `VideoIdea` generation | None |
| `app/video_strategy/blueprint.py` | ~200 | Sync | `BlueprintAssembler` orchestrates title, thumbnail, description, monetization engines | None |
| `app/report_generation/engine.py` | 481 | Sync | JSON + Markdown reports with comprehensive tables | None |

### `app/cli.py`

| File | Lines | Summary | Issues |
|------|------:|---------|--------|
| `app/cli.py` | 504 | Click CLI: `analyze`, `discover`, `generate-report` (stub), `cache-stats`, `clear-cache`, `ai-analyze`, `serve`, `health` | **`generate-report` is a stub** — prints "not yet implemented". |

### `frontend/` — Next.js Dashboard

| File | Lines | Summary | Issues |
|------|------:|---------|--------|
| `frontend/package.json` | 34 | Next 14, React 18, TanStack Query 5, Recharts 3, Zustand 5, Lucide icons | None |
| `frontend/src/app/layout.tsx` | 30 | Root layout: Inter font, Providers + AppShell wrapper, hardcoded `className="dark"` | None |
| `frontend/src/app/providers.tsx` | 36 | QueryClient config (staleTime 5m, gcTime 30m), theme side-effect | None |
| `frontend/src/app/page.tsx` | 230 | Dashboard: stat cards, score chart, top niches list, velocity, viral opps, faceless leaders | Uses `vel.growth_rate`, `vel.acceleration` — **will break** if `TopicVelocityResult` weekly volume field names differ (they do — see schema section) |
| `frontend/src/app/discover/page.tsx` | 325 | Discovery controls, seed keyword tags, sortable niche table, filters | Well-built. |
| `frontend/src/app/niches/[id]/page.tsx` | 230 | Niche detail: radar chart, velocity chart, channel concept, viral opps table, keywords | Uses `opp.upload_date` — **Python sends `video_age_days` instead** → renders as "—". Uses `channelConcept.target_audience` — **Python sends `audience` object** → renders undefined. |
| `frontend/src/app/strategy/page.tsx` | 280 | Video strategy: channel concepts, expandable blueprints | **Multiple broken field accesses**: `bp.title` (Python: `bp.video_idea.title`), `bp.topic`, `bp.ctr_score`, `bp.thumbnail_concept` (Python: `bp.thumbnail`), `bp.production_plan` (Python: `bp.low_cost_production`), `bp.seo_description` as string (Python: object), `bp.monetization_strategy` (Python: `bp.monetization`). |
| `frontend/src/app/reports/page.tsx` | 220 | Report explorer: list, detail view, download links, "Load into Dashboard" | Uses `as any` cast for loading report data — fragile but works. |
| `frontend/src/app/thumbnails/page.tsx` | 200 | Thumbnail insights: face freq, text usage, contrast, per-niche color donuts + style groups | Accesses `c.color || c.hex` for dominant colors — **Python sends dicts with `color` key** → works. Style group chart works. |
| `frontend/src/app/system/page.tsx` | 110 | System page: health status, cache stats, config display | None |
| `frontend/src/components/layout/app-shell.tsx` | 30 | Sidebar + Header + main content with sidebar width transition | None |
| `frontend/src/components/layout/sidebar.tsx` | 90 | 6-item nav, collapsible sidebar, logo | None |
| `frontend/src/components/layout/header.tsx` | 55 | Search input (non-functional), API status dot, theme toggle | **Search bar is non-functional** — no onSubmit handler, just decorative. `ml-64`/`ml-16` duplicated from AppShell — could cause double-margin on header. |
| `frontend/src/components/charts/score-chart.tsx` | 80 | Recharts horizontal BarChart, memo-wrapped | None |
| `frontend/src/components/charts/niche-radar.tsx` | 70 | Recharts RadarChart for 8-axis niche metrics | None |
| `frontend/src/components/charts/velocity-chart.tsx` | 80 | Recharts AreaChart for weekly upload volume | Uses `wv.week` and `wv.volume` — **Python sends `week_label` and `upload_count`** → chart renders with empty data. |
| `frontend/src/components/charts/thumbnail-donut.tsx` | 65 | Recharts PieChart donut | None |
| `frontend/src/components/ui/button.tsx` | ~50 | CVA-based Button with variants | None |
| `frontend/src/components/ui/card.tsx` | ~50 | Card family (Card, CardHeader, CardTitle, CardContent, CardDescription) | None |
| `frontend/src/components/ui/badge.tsx` | ~40 | Badge with success/warning/destructive/outline variants | None |
| `frontend/src/components/ui/input.tsx` | ~20 | Styled input | None |
| `frontend/src/components/ui/spinner.tsx` | ~40 | Spinner + LoadingScreen + EmptyState components | None |
| `frontend/src/components/ui/progress.tsx` | ~20 | Progress bar | **Not imported anywhere** — dead component |
| `frontend/src/services/api.ts` | ~100 | Fetch-based API client for all 12+ endpoints | None |
| `frontend/src/hooks/use-api.ts` | ~110 | 11 React Query hooks wrapping API calls | Query key + staleTime tuning per endpoint. Well-done. |
| `frontend/src/types/api.ts` | ~170 | TypeScript interfaces for all API types | **MAJOR: Extensive mismatches vs Python models** (detailed in Section 4) |
| `frontend/src/types/index.ts` | 3 | Barrel re-export | None |
| `frontend/src/store/app-store.ts` | ~50 | Zustand: analysisData, selectedNiche, sidebar, theme (localStorage) | None |
| `frontend/src/lib/utils.ts` | 40 | `cn()`, `formatNumber()`, `formatScore()`, `formatDate()`, `formatTimestamp()` | None |

### `tests/`

| File | Lines | Summary | Issues |
|------|------:|---------|--------|
| `tests/__init__.py` | 0 | Package marker | None |
| `tests/test_ai.py` | 365 | Client tests (JSON parsing, singleton, Flash/Pro), prompt structure tests, service integration (mocked), DB model + config verification | Comprehensive. All AI calls properly mocked. |
| `tests/test_cache.py` | 53 | set/get, miss, invalidate, stats, clear | Good basic coverage. |
| `tests/test_config.py` | 35 | Default settings, weights sum, connector configs, analysis config | Good. |
| `tests/test_database.py` | 65 | init_db, KeywordRecord, NicheRecord CRUD | Good but **doesn't test missing `viral_opportunity_score`/`topic_velocity_score` columns**. |
| `tests/test_engines.py` | 135 | Virality, CTR, Faceless, Clustering, Ranking engines | Good unit tests with synthetic data. |
| `tests/test_models.py` | 130 | Construction tests for all major Pydantic models | Good coverage. |
| `tests/test_new_engines.py` | 540 | Viral opportunity detector, topic velocity, thumbnail analysis, updated ranking, new model tests | Most comprehensive test file. Covers internals (age parsing, bucketing, score calc, anomaly detection, color quantization, face heuristic, style clustering). |
| `tests/test_reports.py` | 65 | JSON/Markdown report generation, save_all | Good. |
| `tests/test_strategy.py` | 140 | VideoStrategy, ThumbnailStrategy, TitleGeneration, DescriptionGeneration, Monetization, BlueprintAssembler | Good end-to-end coverage. |

### `scripts/`

| File | Lines | Summary | Issues |
|------|------:|---------|--------|
| `scripts/setup.sh` | 40 | Creates venv, installs deps, creates data dirs | None |
| `scripts/run_tests.sh` | 8 | Runs pytest | None |
| `scripts/benchmark.py` | 182 | Performance benchmark: health, cache, dashboard, reports, full pipeline latency | Well-structured with targets per endpoint. |

---

## 2. Cross-Cutting Issues

### CRITICAL

| # | Issue | Files Affected | Impact |
|---|-------|---------------|--------|
| C1 | **Frontend TypeScript types deeply mismatched vs Python Pydantic models** — at least 8 interfaces have wrong field names or structures | `frontend/src/types/api.ts` ↔ `app/core/models.py` | Strategy page, velocity chart, niche detail page render with undefined/missing data |
| C2 | **`youtube_api.py` sets non-existent fields** — `published_at`, `like_count`, `comment_count` don't exist on `SearchResult` model | `app/connectors/youtube_api.py` ↔ `app/core/models.py` | Data silently lost when YouTube Data API connector is enabled |
| C3 | **`NicheRecord` DB schema stale** — missing `viral_opportunity_score`, `topic_velocity_score` columns that `NicheScore` model has and ranking engine populates | `app/database/models.py` ↔ `app/core/models.py` | These scores can't be persisted to DB; queries filtering by them will fail |

### HIGH

| # | Issue | Files Affected | Impact |
|---|-------|---------------|--------|
| H1 | **`Pillow` not in `requirements.txt`** but imported by thumbnail_analysis | `requirements.txt`, `app/thumbnail_analysis/engine.py` | Falls back to heuristic mode — thumbnail analysis quality degraded |
| H2 | **`tenacity` imported but never used** in `base.py` | `app/connectors/base.py` | No retry logic on HTTP connectors — transient failures cause hard errors |
| H3 | **`generate-report` CLI command is a stub** | `app/cli.py` | Users see "not yet implemented" — feature gap |
| H4 | **`_bg_tasks` dict in routes.py never cleaned up** | `app/api/routes.py` | Memory leak for long-running API servers; completed tasks accumulate forever |
| H5 | **Header component duplicates sidebar margin** | `frontend/src/components/layout/header.tsx` | `ml-64`/`ml-16` applied to header which is already inside the shifted container from `app-shell.tsx` — potential double-offset |

### MEDIUM

| # | Issue | Files Affected | Impact |
|---|-------|---------------|--------|
| M1 | **`NicheReport.discovery_insights`** declared but never populated | `app/core/models.py` | Always empty dict in reports |
| M2 | **Search bar in header is decorative** — no submit handler | `frontend/src/components/layout/header.tsx` | UI element does nothing |
| M3 | **`progress.tsx` component never imported** | `frontend/src/components/ui/progress.tsx` | Dead code |
| M4 | **`VertexAIConfig.client_id`** field serves no purpose | `app/config/settings.py` | Confusing config option |
| M5 | **Wildcard import** in `app/core/__init__.py` | `app/core/__init__.py` | Exports ~40 symbols implicitly — pollutes namespace |

---

## 3. Pipeline Wiring Verification

**All 18 engines are properly wired into `pipeline.py`:**

| Step | Engine | Wired In | Method |
|------|--------|:--------:|--------|
| 1 | `DiscoveryEngine` | Yes | `run_discovery_pipeline()` / `run_full_pipeline()` |
| 2 | `KeywordExpansionEngine` | Yes | `run_full_pipeline()` step 2 |
| 3 | `NicheClusteringEngine` | Yes | `run_full_pipeline()` step 3 |
| 4 | `CompetitionAnalysisEngine` | Yes | `_analyze_single_niche()` |
| 5 | `ViralityPredictionEngine` | Yes | `_analyze_single_niche()` |
| 6 | `CTRPredictionEngine` | Yes | `_analyze_single_niche()` |
| 7 | `FacelessViabilityEngine` | Yes | `_analyze_single_niche()` |
| 8 | `ViralOpportunityDetector` | Yes | `_analyze_single_niche()` |
| 9 | `TopicVelocityEngine` | Yes | `_analyze_single_niche()` |
| 10 | `ThumbnailAnalysisEngine` | Yes | `_analyze_single_niche()` |
| 11 | `TrendDiscoveryEngine` | Yes | `run_full_pipeline()` (parallel with step 2) |
| 12 | `NicheRankingEngine` | Yes | `run_full_pipeline()` step 8 |
| 13 | `VideoStrategyEngine` | Yes | `run_full_pipeline()` step 9 |
| 14 | `BlueprintAssembler` | Yes | `run_full_pipeline()` step 10 |
| 15 | `TitleGenerationEngine` | Yes | Used *indirectly* via `BlueprintAssembler` |
| 16 | `ThumbnailStrategyGenerator` | Yes | Used *indirectly* via `BlueprintAssembler` |
| 17 | `DescriptionGenerationEngine` | Yes | Used *indirectly* via `BlueprintAssembler` |
| 18 | `MonetizationEngine` | Yes | Used *indirectly* via `BlueprintAssembler` |
| — | `ReportGenerationEngine` | Yes | `run_full_pipeline()` step 11 |

**Verdict: No orphaned engines.** All engines participate in the pipeline, either directly or indirectly through `BlueprintAssembler`.

---

## 4. Frontend ↔ Backend Schema Mismatches

This is the single most impactful issue in the codebase. The TypeScript interfaces in `frontend/src/types/api.ts` were written independently from the Python Pydantic models and have **drifted significantly**.

### 4.1 `VideoBlueprint` — SEVERELY MISMATCHED

| Aspect | Python (`core/models.py`) | TypeScript (`types/api.ts`) | Breaks? |
|--------|--------------------------|----------------------------|:-------:|
| Title access | `video_idea: VideoIdea` (nested) | `title: string` (flat) | **YES** — `bp.title` → undefined |
| Topic | `video_idea.topic` | `topic: string` (flat) | **YES** |
| CTR score | Not present | `ctr_score: number` | **YES** |
| Thumbnail | `thumbnail: ThumbnailConcept` | `thumbnail_concept: ThumbnailConcept` | **YES** — different key name |
| Script | `script_structure: ScriptStructure` (hook/intro/conflict/value/cta) | `script_structure: { hook, sections[] }` | **YES** — `sections` doesn't exist |
| Production | `low_cost_production: LowCostProduction` | `production_plan: ProductionPlan` | **YES** — completely different structure |
| SEO | `seo_description: SEODescription` (object) | `seo_description: string` | **YES** — object vs string |
| Monetization | `monetization: MonetizationStrategy` | `monetization_strategy: MonetizationStrategy` | **YES** — different key name |
| Extra titles | `curiosity_gap_headline`, `keyword_optimized_title`, `alternative_titles` | Not present | No (just missing data) |

**Impact:** The entire Strategy page renders blueprints with missing data. Title shows undefined, thumbnail concept is null, script structure shows nothing, production plan shows nothing.

### 4.2 `ChannelConcept` — MISMATCHED

| Aspect | Python | TypeScript | Breaks? |
|--------|--------|-----------|:-------:|
| Audience | `audience: AudiencePersona \| None` | `target_audience: string` + `audience_persona?: AudiencePersona` | **YES** — `target_audience` → undefined; `audience_persona` → undefined (Python sends `audience`) |
| Name ideas | `channel_name_ideas: list[str]` | Not present | No (missing data) |
| Monetization timeline | `monetization_timeline: list[str]` | Not present | No |
| Video ideas | `video_ideas: list[VideoIdea]` | Not present | No |

**Impact:** Strategy page and niche detail page show "undefined" for target audience.

### 4.3 `ViralOpportunity` — NAME MISMATCHES

| Aspect | Python | TypeScript | Breaks? |
|--------|--------|-----------|:-------:|
| Upload date | `video_age_days: int \| None` | `upload_date: string` | **YES** — niche detail shows "—" for all dates |
| View ratio | `views_to_sub_ratio: float` | `subscriber_view_ratio: number` | **YES** — not rendered on frontend so invisible, but data unavailable |

### 4.4 `WeeklyUploadVolume` / `WeeklyVolume` — NAME MISMATCHES

| Python field | TypeScript field | Breaks? |
|-------------|-----------------|:-------:|
| `week_label: str` | `week: string` | **YES** — velocity chart X-axis empty |
| `upload_count: int` | `volume: number` | **YES** — velocity chart Y-axis empty |

**Impact:** The velocity chart on niche detail page renders with no data points.

### 4.5 `ThumbnailConcept` — COMPLETELY DIFFERENT

| Python | TypeScript |
|--------|-----------|
| `emotion_trigger`, `contrast_strategy`, `visual_focal_point`, `text_overlay`, `color_palette`, `layout_concept` | `style`, `primary_color`, `emotion`, `contrast_level` |

**Impact:** Strategy page blueprint thumbnails show undefined for style and emotion.

### 4.6 `ScriptStructure` — DIFFERENT SHAPE

| Python | TypeScript |
|--------|-----------|
| `hook: str`, `intro: str`, `conflict: str`, `value_delivery: str`, `cta: str` | `hook: string`, `sections: string[]` |

**Impact:** `bp.script_structure.sections?.join(' → ')` renders nothing.

### 4.7 Types That DO Match Correctly

| Type | Status |
|------|--------|
| `NicheScore` | Matches well — all field names align |
| `TopicVelocityResult` (top-level) | `niche`, `growth_rate`, `acceleration`, `velocity_score` all match |
| `ThumbnailPatternResult` / `ThumbnailPattern` | Mostly matches (TS missing some fields but doesn't access them) |
| `ThumbnailStyleGroup` / `StyleGroup` | Fields match |
| `DominantColor` | Fields match |
| `AnalysisData` (envelope) | Top-level keys match `NicheReport` |

### 4.8 Recommended Fix

Create a single source of truth. Options:
1. **Generate TS types from Python models** — Use a tool like `pydantic-to-typescript` or write a script
2. **Manually align** — Update `frontend/src/types/api.ts` to match every Python model field name exactly
3. **Add a serialization layer** — Create a backend response transformer that maps Python models to the TS-expected shape

---

## 5. API Endpoint Inventory

| Method | Path | Handler | Auth | Frontend Uses? |
|--------|------|---------|:----:|:--------------:|
| GET | `/` | `root()` | No | No |
| GET | `/health` | `health_check()` | No | Yes — `useHealth()` |
| POST | `/analyze` | `run_analysis()` | No | Yes — `useAnalyze()` |
| POST | `/discover` | `run_discovery()` | No | Yes — `useDiscover()` |
| GET | `/niches` | `get_niches()` | No | No — not used by frontend |
| GET | `/cache/stats` | `cache_stats()` | No | Yes — `useCacheStats()` |
| GET | `/ai/niche-insights` | `ai_niche_insights()` | No | Yes — `useAINicheInsights()` |
| GET | `/ai/video-strategy` | `ai_video_strategy()` | No | Yes — `useAIVideoStrategy()` |
| GET | `/ai/trend-forecast` | `ai_trend_forecast()` | No | Yes — `useAITrendForecast()` |
| GET | `/reports` | `list_reports()` | No | Yes — `useReports()` |
| GET | `/reports/{filename}` | `get_report()` | No | Yes — `useReport()` |
| GET | `/reports/{filename}/download` | `download_report()` | No | Yes — `getReportDownloadUrl()` |
| POST | `/analyze/async` | `run_analysis_async()` | No | No |
| GET | `/tasks/{task_id}` | `get_task_status()` | No | No |
| GET | `/dashboard-data` | `dashboard_data()` | No | Yes — `useDashboardData()` |

**Unused by frontend:** `/`, `/niches`, `/analyze/async`, `/tasks/{task_id}` (the async analysis + polling endpoints have no frontend UI).

---

## 6. Dead Code & Unused Modules

| Item | Location | Status |
|------|----------|--------|
| `progress.tsx` | `frontend/src/components/ui/progress.tsx` | **Dead** — never imported |
| `tenacity` import | `app/connectors/base.py` | **Dead** — imported but retry decorator never used |
| `NicheReport.discovery_insights` | `app/core/models.py` | **Dead** — declared but never populated by any engine |
| `VertexAIConfig.client_id` | `app/config/settings.py` | **Vestigial** — Vertex AI auth doesn't use client IDs |
| `/niches` endpoint | `app/api/routes.py` | **Underused** — exists in API, not consumed by frontend |
| `/analyze/async` + `/tasks/{id}` | `app/api/routes.py` | **Underused** — async pipeline exists but no frontend polling UI |
| `generate-report` CLI command | `app/cli.py` | **Stub** — prints "not yet implemented" |
| Header search bar | `frontend/src/components/layout/header.tsx` | **Non-functional** — decorative input with no handler |

---

## 7. Missing Dependencies

| Package | Used In | In `requirements.txt`? | Impact |
|---------|---------|:----------------------:|--------|
| `Pillow` | `app/thumbnail_analysis/engine.py` | **NO** | Falls back to heuristic mode; thumbnail analysis quality reduced |
| `tenacity` | `app/connectors/base.py` (imported) | **NO** | Import succeeds on systems with tenacity installed coincidentally; otherwise `ImportError` at runtime |

**Note:** `tenacity` is imported at the top of `base.py` but never actually used as a decorator. If it's not installed, the import will crash when any connector is instantiated. It should either be added to requirements.txt and used, or the import should be removed.

---

## 8. Configuration Gaps

| Gap | Details |
|-----|---------|
| `config.yaml` missing `vertex_ai` section | Works (falls back to Python defaults: disabled), but users have no visibility into configurable Vertex AI options |
| Ranking weights inconsistency | `README.md` documents demand=0.30, competition=0.25; actual `settings.py` defaults are demand=0.25, competition=0.20; `config.yaml` has demand=0.25, competition=0.20 (matches code). README is wrong. |
| No `.env.example` file | Environment variable overrides (`GS_*`) documented nowhere except code comments in `settings.py` |
| No frontend `.env.example` | `NEXT_PUBLIC_API_URL` used in `api.ts` and `system/page.tsx` but no template file |
| Dockerfile missing `EXPOSE` | Standard practice to document exposed port |

---

## 9. Test Coverage Assessment

### Covered

| Area | Test File | Verdict |
|------|-----------|---------|
| AI client (JSON parsing, models, singleton) | `test_ai.py` | Good |
| AI prompts (all 4 template modules) | `test_ai.py` | Good |
| AI service (all 7 functions, mocked) | `test_ai.py` | Good |
| Cache (set/get/miss/invalidate/stats/clear) | `test_cache.py` | Good |
| Config (defaults, weights sum, connectors, analysis) | `test_config.py` | Good |
| Database (init, keyword/niche CRUD) | `test_database.py` | Basic |
| Virality/CTR/Faceless/Clustering/Ranking engines | `test_engines.py` | Good |
| All Pydantic models (construction + fields) | `test_models.py` | Good |
| Viral opportunity detector (internals + integration) | `test_new_engines.py` | Excellent |
| Topic velocity (internals + integration) | `test_new_engines.py` | Excellent |
| Thumbnail analysis (internals) | `test_new_engines.py` | Good |
| Updated ranking formula | `test_new_engines.py` | Good |
| Report generation (JSON/MD/save_all) | `test_reports.py` | Good |
| Strategy generators (all 6 + blueprint) | `test_strategy.py` | Good |

### NOT Covered

| Area | Note |
|------|------|
| **API endpoints** | No `test_api.py` — no tests for any FastAPI route. No TestClient usage. |
| **Pipeline orchestrator** | No `test_pipeline.py` — the central `PipelineOrchestrator` has zero tests. |
| **Connectors** | No tests for any of the 7 connectors (youtube_search, youtube_api, google_trends, reddit, etc.). All are network-dependent but could be tested with mocked httpx. |
| **CLI** | No `test_cli.py` — Click CLI has no tests. |
| **Discovery engine** | No tests for `DiscoveryEngine` (the auto-discovery entry point). |
| **Trend discovery engine** | No tests for multi-signal trend analysis. |
| **Frontend** | No frontend tests at all (no jest, no testing-library, no cypress/playwright). |
| **Database migrations** | No Alembic or migration tests — schema changes require manual DB recreation. |
| **Integration/E2E** | No end-to-end test running the full pipeline. |

---

## 10. Documentation Drift

| Document | Issue |
|----------|-------|
| `README.md` — Tech Stack | Lists **Plotly Dash**, **dash-cytoscape**, **NetworkX**, **dash-bootstrap-components** — none of these are used. Frontend is **Next.js + React** with **Recharts**, **TanStack Query**, **Zustand**. |
| `README.md` — Ranking weights | Shows `demand: 0.30, competition: 0.25, faceless: 0.05` — code actually uses `demand: 0.25, competition: 0.20, viral_opportunity: 0.10, topic_velocity: 0.05`. |
| `README.md` — API Endpoints table | Only lists 5 endpoints. Actual API has 15 endpoints including AI insights, reports CRUD, async pipeline, dashboard batch. |
| `README.md` — JSON Structure | Missing `viral_opportunities`, `topic_velocities`, `thumbnail_patterns`, `ai_insights` from the example output. |
| `config.yaml` | Missing `vertex_ai:` section that's configurable in `settings.py`. |

---

## 11. Priority Fix List

### P0 — Fix Immediately (breaks user-facing features)

1. **Align `frontend/src/types/api.ts` with Python models** — Fix `VideoBlueprint`, `ChannelConcept`, `ViralOpportunity`, `WeeklyVolume`, `ThumbnailConcept`, `ScriptStructure` field names. This breaks 3+ frontend pages.

2. **Fix `youtube_api.py` → `SearchResult` field mismatch** — Either add `published_at`, `like_count`, `comment_count` fields to the `SearchResult` model, or change the connector to use existing fields (`published_date`, drop like/comment).

3. **Add `Pillow` to `requirements.txt`** — Or document that it's optional and the heuristic fallback is expected.

### P1 — Fix Soon (data integrity / reliability)

4. **Add `viral_opportunity_score` and `topic_velocity_score` to `NicheRecord`** DB model — Keeps persistence layer aligned with the scoring engine.

5. **Remove or use `tenacity`** — Either remove the dead import from `base.py`, or properly apply retry decorators to connector HTTP calls.

6. **Add task cleanup to `_bg_tasks` in routes.py** — Evict completed tasks after a TTL (e.g., 1 hour) to prevent memory leaks.

7. **Fix header double-margin** — Remove `ml-64`/`ml-16` from `header.tsx` since `app-shell.tsx` already handles the offset.

### P2 — Fix When Possible (quality / completeness)

8. **Update `README.md`** — Fix tech stack (remove Dash/Cytoscape/NetworkX, add Next.js/Recharts/Zustand), update ranking weights, expand API table, update JSON example.

9. **Implement `generate-report` CLI command** — Currently a stub.

10. **Add API tests** — Create `test_api.py` using `httpx.AsyncClient` / FastAPI TestClient.

11. **Add pipeline orchestrator tests** — The core orchestration logic has zero coverage.

12. **Add `.env.example`** files for both backend and frontend.

13. **Wire up header search** — Either implement global search or remove the decorative input.

14. **Add `EXPOSE 8000`** to Dockerfile.

15. **Populate `NicheReport.discovery_insights`** or remove the field.

---

*End of audit.*
