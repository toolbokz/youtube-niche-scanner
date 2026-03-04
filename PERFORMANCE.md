# Performance Optimization Guide

This document details all performance optimizations applied to the Growth Strategist platform, covering backend, frontend, and infrastructure layers.

## Targets

| Metric | Target | Layer |
|--------|--------|-------|
| API response (cached reads) | < 200 ms | Backend |
| Discovery pipeline wall-clock | 50% reduction | Backend |
| Frontend initial load | < 2 seconds | Frontend |
| Dashboard interaction latency | < 150 ms | Frontend |
| AI analysis operations | Minimized & cached | Backend |

---

## Backend Optimizations

### 1. Multi-Tier Cache (`app/core/cache.py`)

Replaced the single-layer flat-file JSON cache with a three-tier architecture:

| Tier | Technology | Latency | TTL |
|------|-----------|---------|-----|
| L1 | In-memory LRU (OrderedDict, 4096 entries) | ~0 ms | Per-process |
| L2 | Redis async (optional, graceful fallback) | ~1 ms | Configurable |
| L3 | Disk (orjson binary, sharded 256 dirs) | ~5 ms | File-based |

Key features:
- **orjson serialization** — ~5× faster than stdlib json
- **LRU eviction** — oldest entries evicted when memory limit reached
- **Sharded disk layout** — `key[:2]/key.bin` prevents single-directory inode pressure
- **Hit-rate tracking** — `cache.stats()` exposes hits/misses per tier
- **Backward compatible** — reads legacy `.json` files if `.bin` not found

### 2. Pipeline Parallelization (`app/core/pipeline.py`)

The orchestrator now runs independent steps concurrently:

```
BEFORE (sequential):
  Step 1 → Step 2 → Step 3 → [Step 4 niche-1] → [Step 4 niche-2] → ... → Step 10

AFTER (parallel):
  [Step 1 + Step 2] concurrent ─────────────────────────────┐
  Step 3 (clustering) ──────────────────────────────────────┤
  [All niches: Steps 4-7] bounded parallel (Semaphore=6) ──┤
  Step 8 (ranking) ─────────────────────────────────────────┤
  [Steps 9 + 10] concurrent via executor ───────────────────┘
```

Each niche's 4 async sub-tasks (competition, viral, velocity, thumbnail) also fire concurrently within `_analyze_single_niche()`.

### 3. Connector & Engine Parallelization

All batch methods converted from sequential loops to `asyncio.gather`:

| Module | Method | Before | After |
|--------|--------|--------|-------|
| `keyword_expansion` | `expand_seed()` | 8 sequential calls | 1× gather (all concurrent) |
| `keyword_expansion` | `expand_batch()` | N sequential seeds | All seeds concurrent |
| `keyword_scraper` | `expand_all_sources()` | Google → Bing serial | Both concurrent |
| `discovery_engine` | `discover_topics()` | 4 sources serial | All 4 concurrent |
| `trend_discovery` | `discover_trends()` | N keywords serial | All concurrent |
| `competition_analysis` | `analyze_niche()` | 5 keywords serial | All 5 concurrent |
| `google_trends` | `get_batch_trends()` | N keywords serial | All concurrent |
| `reddit` | `get_batch_signals()` | N keywords serial | All concurrent |

### 4. AI Service Parallelization (`app/ai/service.py`)

`run_full_ai_analysis()` previously ran 5+ AI calls sequentially (niche analysis, 3× viral interpretation, video strategy, thumbnail strategy, trend forecast). Now fires all independent AI calls via `asyncio.gather`, reducing wall-clock time from ~5× serial to ~1× (bounded by the slowest Gemini call).

### 5. Database Optimization (`app/database/models.py`)

**Composite indexes** added for frequent query patterns:
- `idx_niche_name_score` (name, overall_score) — dashboard sorting
- `idx_niche_updated` (updated_at) — freshness checks
- `idx_search_query_collected` (query, collected_at) — time-bounded searches
- `idx_trend_keyword_collected` (keyword, collected_at) — trend freshness
- `idx_trend_momentum` (momentum_score) — top-trending queries
- `idx_run_status_started` (status, started_at) — task queue polling
- `idx_ai_type_niche` (analysis_type, niche) — AI cache lookups

**SQLite WAL mode** enabled via PRAGMA:
- `journal_mode=WAL` — concurrent reads during writes
- `synchronous=NORMAL` — safe but faster sync
- `cache_size=-64000` — 64 MB page cache
- `temp_store=MEMORY` — temp tables in RAM
- `mmap_size=268435456` — 256 MB memory-mapped I/O

**PostgreSQL connection pooling** (when not using SQLite):
- `pool_size=10`, `max_overflow=20`
- `pool_pre_ping=True` — detect stale connections
- `pool_recycle=1800` — refresh connections every 30 min

### 6. Network Layer (`app/api/routes.py`)

- **GZip compression** via `GZipMiddleware(minimum_size=500)` — compresses JSON responses > 500 bytes (~70% smaller for large reports)
- **orjson response class** (`ORJSONResponse`) — ~5× faster JSON serialization with numpy/non-string-key support
- **Server-Timing header** — every response includes `Server-Timing: total;dur=X` for client-side performance monitoring
- **Slow request logging** — requests > 500 ms automatically flagged in logs

### 7. New API Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /dashboard-data` | Batch endpoint combining health + cache stats + latest report + recent reports in one round-trip |
| `POST /analyze/async` | Fire-and-forget pipeline — returns `task_id` immediately |
| `GET /tasks/{task_id}` | Poll background task status |

---

## Frontend Optimizations

### 1. Code Splitting (Dynamic Imports)

All Recharts components (~200 KB) are lazy-loaded via `next/dynamic`:

```tsx
const ScoreDistributionChart = dynamic(
    () => import('@/components/charts/score-chart').then(m => ({ default: m.ScoreDistributionChart })),
    { ssr: false, loading: () => <div className="h-[300px] animate-pulse rounded-lg bg-muted" /> }
);
```

Applied to: Dashboard (`page.tsx`), Discover, Niche Detail, Thumbnails pages.

### 2. TanStack Query Cache Tuning

| Query | staleTime | gcTime | Rationale |
|-------|-----------|--------|-----------|
| Default | 5 min | 30 min | General data |
| Health | 30 s | — | Needs freshness |
| Reports list | 10 min | — | Rarely changes |
| Individual report | 30 min | — | Immutable once saved |
| AI insights | 15 min | 1 hour | Expensive to regenerate |
| Dashboard batch | 2 min | — | Moderate freshness |

### 3. React.memo

All chart components wrapped with `React.memo` to prevent re-renders when parent state changes but chart data hasn't:

- `ScoreDistributionChart`
- `NicheRadar`
- `VelocityChart`
- `ThumbnailDonut`

### 4. Dashboard Batch Endpoint

Frontend can now call `GET /dashboard-data` to get health + cache + recent reports + latest report summary in a single HTTP round-trip instead of 3-4 separate calls.

---

## Benchmarking

Run the benchmark suite:

```bash
# Start the API server
uvicorn app.api.routes:app --host 0.0.0.0 --port 8000

# In another terminal
python scripts/benchmark.py --base-url http://localhost:8000 --iterations 10
```

Output includes min/mean/p95/max latencies per endpoint, pass/fail against targets, and GZip compression info.

---

## Configuration

New optional settings in `config.yaml`:

```yaml
database:
  pool_size: 10          # PostgreSQL only (SQLite uses WAL mode)

cache:
  memory_max_items: 4096  # L1 LRU cache size
  redis_url: null         # Set to redis://localhost:6379 to enable L2
```

New dependencies:
- `orjson>=3.9.0` — fast JSON serialization (optional, falls back to stdlib)
- `redis>=5.0.0` — async Redis client for L2 cache (optional)
