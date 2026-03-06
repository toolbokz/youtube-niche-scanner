# Architecture & Stabilization Audit — Growth Strategist

## Table of Contents

1. [System Architecture](#system-architecture)
2. [Core Pipeline Flow](#core-pipeline-flow)
3. [Video Factory Pipeline](#video-factory-pipeline)
4. [API Layer](#api-layer)
5. [Data Layer](#data-layer)
6. [AI Integration](#ai-integration)
7. [Bugs Found & Fixed](#bugs-found--fixed)
8. [Performance Improvements](#performance-improvements)
9. [Stability Improvements](#stability-improvements)
10. [Test Coverage](#test-coverage)
11. [Codebase Cleanup](#codebase-cleanup)

---

## System Architecture

```
┌──────────────┐    ┌──────────────┐    ┌──────────────────┐
│   Next.js    │──→ │  FastAPI API  │──→ │  Pipeline Orch.  │
│  Frontend    │←── │  35+ routes   │←── │  11-step engine  │
└──────────────┘    └──────┬───────┘    └────────┬─────────┘
                           │                     │
                    ┌──────┴───────┐    ┌────────┴─────────┐
                    │   Database    │    │   5 Connectors   │
                    │ SQLite + WAL  │    │   14+ Engines    │
                    └──────────────┘    └──────────────────┘
```

### Tech Stack
- **Backend**: Python 3.12, FastAPI, asyncio, SQLAlchemy (async)
- **Frontend**: Next.js 14, React, TypeScript, TailwindCSS, shadcn/ui, TanStack Query, Zustand
- **AI**: Google Vertex AI (Gemini 2.0 Flash + Pro) via lazy-init singleton
- **Video**: FFmpeg (GPU-accelerated: NVENC/QSV/VideoToolbox), yt-dlp
- **Cache**: 3-tier (LRU memory → Redis → disk with orjson)
- **Database**: SQLite with WAL + PRAGMA (default), PostgreSQL support
- **Config**: 4-tier priority: env vars (GS_*) > .env > config.yaml > built-in defaults

### Module Map

| Module | Purpose | Key Files |
|--------|---------|-----------|
| `app/core/` | Pipeline orchestrator, models, cache, logging | `pipeline.py`, `models.py`, `cache.py` |
| `app/connectors/` | Data fetching (YouTube, Google Trends, Reddit) | `base.py`, 6 connector files |
| `app/ai/` | Vertex AI client + service layer with DB-backed cache | `client.py`, `service.py` |
| `app/api/` | FastAPI routes (35+ endpoints) with middleware | `routes.py` |
| `app/database/` | SQLAlchemy ORM (10 tables) + CRUD helpers | `models.py`, `persistence.py` |
| `app/video_factory/` | 10-stage video compilation pipeline | 14 files |
| `app/config/` | Settings management with 60+ env var mappings | `settings.py` |
| `app/*_engine/` | 14+ analysis engines (ranking, CTR, virality, etc.) | `engine.py` each |

---

## Core Pipeline Flow

The `PipelineOrchestrator` runs an 11-step niche discovery pipeline with maximum parallelism:

```
Steps 1-2 (parallel):  Keyword Expansion ∥ Trend Discovery
Step 3  (CPU-only):     Niche Clustering (TF-IDF + Agglomerative)
Steps 4-7 (parallel):  Per-niche analysis (bounded by Semaphore(6))
  └── Competition ∥ Viral Opportunities ∥ Topic Velocity ∥ Thumbnail Analysis
  └── Virality ∥ CTR ∥ Faceless Viability (sync, CPU-light)
Step 8:                 Niche Ranking (weighted composite)
Step 8b (optional):     AI Enhancement (Gemini Pro, if configured)
Steps 9-10 (parallel):  Strategy + Blueprint Generation (run_in_executor)
Step 11:                Report Generation (JSON + Markdown)
```

### Key Design Decisions
- **Demand vs Trend separation**: `demand_score` uses keyword expansion breadth (number of autocomplete suggestions), `trend_momentum` uses Google Trends momentum data. Previously these were the same value.
- **Bounded concurrency**: `_NICHE_CONCURRENCY = 6` via asyncio.Semaphore prevents HTTP connection storms.
- **Strategy generation in executor**: CPU-bound strategy generation runs in thread pool via `loop.run_in_executor()`.

---

## Video Factory Pipeline

10-stage compilation video production, fully async:

```
1. Hardware Detection   → GPU encoders, CPU cores, memory
2. Fetch Strategy       → CompilationAnalyzer → AI-enhanced segments
3. Download Videos      → yt-dlp (parallel, Sem(3), 10min timeout)
4. Extract Segments     → FFmpeg stream-copy (parallel, bounded, 5min timeout)
5. Validate Clips       → ffprobe (parallel, Sem(8), 30s timeout)
6. Copyright Check      → Per-source usage analysis
7. Build Timeline       → Order clips, cap to target duration
8. Assemble Video       → FFmpeg concat demuxer, single-pass encode (30min timeout)
9. Generate Thumbnail   → Pillow-based generation
10. Generate Metadata   → AI-powered YouTube metadata
11. Cleanup Temp Files  → Remove source videos, intermediate clips
```

### Performance Architecture
- **Stream copy extraction**: Clips extracted with `-c copy` (no encoding) — 10x faster
- **Single-pass encoding**: Only the final assembly step encodes
- **GPU auto-detection**: NVENC → QSV → VideoToolbox → CPU fallback chain
- **All subprocesses use `asyncio.create_subprocess_exec`**: Non-blocking

### Job Management
- `FactoryJobManager`: In-memory for live progress + SQLite persistence for history
- Max 2 concurrent jobs via `asyncio.Semaphore`
- Thread-safe progress callback via `threading.Lock`
- Orphaned job cleanup on server startup

---

## API Layer

35+ FastAPI endpoints organized by domain:

| Group | Endpoints | Notes |
|-------|-----------|-------|
| Core Analysis | `/api/analyze`, `/api/discover` | Pipeline execution |
| Niches | `/api/niches`, `/api/niches/{id}` | CRUD + ranking |
| Strategy | `/api/strategy/*` | Video/channel strategy |
| Video Factory | `/api/video-factory/*` | Job CRUD, progress |
| Reports | `/api/reports/*` | JSON/Markdown reports |
| AI | `/api/ai/*` | Direct AI endpoints |
| System | `/api/health`, `/api/cache/*` | Monitoring |

### Middleware Stack
1. **GZipMiddleware** — Response compression (min 500 bytes)
2. **CORSMiddleware** — Cross-origin for frontend
3. **SecurityHeadersMiddleware** — X-Content-Type, X-Frame, HSTS
4. **TimingMiddleware** — Server-Timing header, slow request logging (>500ms)

### Response Serialization
- **orjson** (if available) for ~5x faster JSON serialization
- Automatic fallback to stdlib `json`

---

## Data Layer

### Database Schema (10 tables)

| Table | Purpose |
|-------|---------|
| `keywords` | Discovered keywords with source, cluster, trend data |
| `niches` | Clustered niches with 8-dimensional scores |
| `video_ideas` | Generated video concepts per niche |
| `search_results` | Cached YouTube search data |
| `trends` | Google Trends time-series data |
| `analysis_runs` | Pipeline execution history |
| `ai_insights` | Cached AI analysis results |
| `video_strategies` | Channel/video strategy documents |
| `compilation_strategies` | Video factory compilation plans |
| `video_factory_jobs` | Job persistence (status, progress, output) |

### Optimizations
- **WAL mode** + PRAGMA tuning for concurrent reads
- **Indexed**: keyword/source, niche/score, updated_at columns
- **Async**: aiosqlite via SQLAlchemy async engine

### Cache Architecture
```
Tier 1: LRU Memory (4096 items)     ~0.001ms
Tier 2: Redis (optional, localhost)   ~0.5ms
Tier 3: Disk (orjson, sharded dirs)   ~2ms
```
- SHA-256 key hashing with 256 shard directories
- Configurable TTL (default 24h)
- Fire-and-forget Redis backfill from disk hits

---

## AI Integration

### Vertex AI Client (`app/ai/client.py`)
- **Lazy initialization**: SDK only loads on first call
- **Singleton pattern**: Single client instance globally
- **Async wrappers**: `agenerate_flash`, `agenerate_pro`, `agenerate_json` run sync SDK in thread executor
- **Retry logic**: 3 attempts with exponential backoff for transient network errors
- **JSON parsing**: Strips markdown fences, handles malformed responses

### Service Layer (`app/ai/service.py`)
- 7 public functions: niche analysis, viral opportunities, video strategy, thumbnail patterns, trend forecasting, quick insights, compilation strategy
- **DB-backed caching**: AI results stored in `ai_insights` table with 24h TTL
- **Parallel execution**: `run_full_ai_analysis` runs independent AI calls concurrently

---

## Bugs Found & Fixed

### Critical

| Bug | Impact | Fix |
|-----|--------|-----|
| **Nested event loop in job_manager** | `asyncio.run()` inside executor created separate loop, breaking DB/connector sharing | Direct `await orchestrator.run()` in current loop |
| **Thread-unsafe progress callback** | Progress mutations from worker threads without sync | Added `threading.Lock` |

### High

| Bug | Impact | Fix |
|-----|--------|-----|
| **Demand/trend double-counting** | Same value used for both (40% effective weight for demand) | Separate `demand_map` (expansion breadth) and `trend_map` (Google Trends) |
| **Faceless viability excluded** | Computed but never used in ranking formula | Now contributes 5% weight |
| **Blocking AI calls** | Sync Gemini SDK blocked event loop, negating gather parallelism | Async wrappers via `run_in_executor` |
| **CTR self-fulfilling scores** | Generated titles with power words, then scored those same titles | Keywords scored separately from synthetic titles |
| **Clustering mutation** | `merge_small_clusters` mutated input Pydantic models in-place | Creates new `KeywordCluster` instances |
| **Unbounded parallelism** | Keyword expansion could fire 400+ concurrent HTTP requests | `Semaphore(8)` bounds concurrency |
| **Topic velocity bucket overflow** | All videos >28 days lumped into one bucket, distorting growth rate | Videos >4 weeks discarded |

### Medium

| Bug | Impact | Fix |
|-----|--------|-----|
| **Sync AI in compilation** | `generate_compilation_strategy` used sync `generate_json` | Changed to `await client.agenerate_json` |
| **No subprocess timeouts** | Stuck FFmpeg/yt-dlp hangs pipeline forever | Timeouts: 5min (clips), 30min (encode), 10min (download), 30s (probe) |
| **Sequential clip validation** | ffprobe calls run one-by-one | Parallel with `Semaphore(8)` + `asyncio.gather` |
| **Sequential video downloads** | Downloads run one-by-one | Parallel with `Semaphore(3)` + `asyncio.gather` |

### Low

| Bug | Impact | Fix |
|-----|--------|-----|
| **`datetime.utcnow()` (25+ instances)** | Deprecated in Python 3.12, returns naive datetime | All → `datetime.now(timezone.utc)` |
| **`asyncio.get_event_loop()`** | Deprecated, may create new loop | → `asyncio.get_running_loop()` |
| **Hardcoded "2024"** | CTR, metadata, compilation outdated | → `datetime.now().year` |
| **Dead imports** | BeautifulSoup, json, datetime in various files | Removed |
| **35+ unused imports** | Code hygiene | Removed across 26 files |

---

## Performance Improvements

| Area | Before | After |
|------|--------|-------|
| Video downloads | Sequential | Parallel (Semaphore(3)) |
| Clip validation | Sequential ffprobe | Parallel (Semaphore(8) + gather) |
| Keyword expansion | Unbounded (400+ concurrent) | Bounded (Semaphore(8)) |
| AI calls | Sync (blocking event loop) | Async (run_in_executor) |
| FFmpeg extraction | No timeout | 5 min timeout + kill |
| FFmpeg assembly | No timeout | 30 min timeout + kill |
| yt-dlp download | No timeout | 10 min timeout + kill |
| ffprobe validation | No timeout | 30 sec timeout |
| HTTP connector calls | No retry | 3 retries with exponential backoff |
| AI generation | No retry | 3 retries with exponential backoff |

---

## Stability Improvements

1. **Tenacity retry decorators** on all HTTP fetch methods (`_fetch`, `_fetch_json`) in `BaseConnector` — retries on `ConnectError`, `ReadTimeout`, `ConnectTimeout` with exponential backoff
2. **Tenacity retry on AI generation** — `generate_flash` and `generate_pro` retry on `ConnectionError`, `TimeoutError`, `OSError`
3. **Subprocess timeout + kill** — All FFmpeg, ffprobe, yt-dlp subprocesses have timeout guards that kill the process if it exceeds the limit
4. **Graceful shutdown** — Pipeline connectors closed on app shutdown, DB connections closed, orphaned jobs marked as failed on startup
5. **Thread-safe job manager** — Progress callback protected by `threading.Lock`

---

## Test Coverage

### Test Suite: 291 tests, all passing

| Test File | Tests | Coverage Area |
|-----------|-------|---------------|
| `test_ai.py` | 29 | Vertex AI client, service functions, mocking |
| `test_cache.py` | 18 | LRU memory, disk, async, invalidation |
| `test_compilation.py` | 25 | Compilation engine, strategy, scoring |
| `test_config.py` | 24 | Settings, env vars, YAML loading |
| `test_database.py` | 15 | ORM models, persistence CRUD |
| `test_engines.py` | 42 | All 14+ analysis engines |
| `test_models.py` | 23 | Pydantic model construction |
| `test_new_engines.py` | 35 | Viral opp, velocity, thumbnail, ranking |
| `test_reports.py` | 10 | JSON/Markdown report generation |
| `test_stabilization_fixes.py` | 21 | **NEW** — Validates all audit fixes |
| `test_strategy.py` | 12 | Video/channel strategy engines |
| `test_video_factory.py` | 18 | Factory models, orchestrator, jobs |
| `test_video_processing.py` | 19 | FFmpeg, hardware, assembler, scheduler |

### New Stabilization Tests (21 tests)

Tests cover every major fix:
- Timezone-aware datetimes across DB, models, reports
- Faceless viability contribution to ranking
- Demand/trend signal separation
- Immutable cluster merging
- Async AI service calls
- Subprocess timeouts
- Parallel clip validation
- Parallel video downloads
- Dynamic year in CTR
- Topic velocity bucket handling
- Bounded keyword expansion
- Thread-safe job manager
- Video assembler timeout

---

## Codebase Cleanup

- **35 unused imports removed** across 26 files
- **All `__pycache__` directories cleaned** (1700+ stale cache dirs)
- **Zero syntax errors** verified across all `.py` files
- **Zero remaining deprecated patterns**: no `utcnow()`, no `get_event_loop()`, no hardcoded `2024`
