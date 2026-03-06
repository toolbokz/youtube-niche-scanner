"""FastAPI application and routes."""
from __future__ import annotations

import json as _json
import time
import traceback
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncGenerator

from fastapi import FastAPI, HTTPException, Query, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.middleware.gzip import GZipMiddleware
from starlette.responses import Response
from pydantic import BaseModel, Field

from app.config import get_settings
from app.core.logging import setup_logging, get_logger
from app.core.pipeline import PipelineOrchestrator
from app.database import init_db, close_db

logger = get_logger(__name__)

# ── Try orjson for fast serialisation ──────────────────────────────────────────
try:
    import orjson

    class ORJSONResponse(JSONResponse):
        """JSONResponse using orjson for ~5× faster serialisation."""
        media_type = "application/json"

        def render(self, content: Any) -> bytes:
            return orjson.dumps(content, option=orjson.OPT_NON_STR_KEYS | orjson.OPT_SERIALIZE_NUMPY)

    _DefaultJSON = ORJSONResponse
except ImportError:
    _DefaultJSON = JSONResponse  # type: ignore[assignment,misc]


# ── Request/Response Models ────────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    seed_keywords: list[str] = Field(..., min_length=1, description="Seed keywords to analyze")
    top_n: int = Field(default=10, ge=1, le=50, description="Number of top niches to return")
    videos_per_niche: int = Field(default=10, ge=1, le=30, description="Videos per niche")


class HealthResponse(BaseModel):
    status: str
    version: str


class AnalyzeResponse(BaseModel):
    status: str
    seed_keywords: list[str]
    top_niches: list[dict[str, Any]]
    channel_concepts: list[dict[str, Any]]
    video_blueprints: dict[str, list[dict[str, Any]]]
    viral_opportunities: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)
    topic_velocities: dict[str, dict[str, Any]] = Field(default_factory=dict)
    thumbnail_patterns: dict[str, dict[str, Any]] = Field(default_factory=dict)
    ai_insights: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any]


class DiscoverRequest(BaseModel):
    deep: bool = Field(default=False, description="Use deep discovery mode")
    max_seeds: int = Field(default=20, ge=5, le=100, description="Max auto-discovered seeds")
    top_n: int = Field(default=20, ge=1, le=50, description="Number of top niches to return")
    videos_per_niche: int = Field(default=10, ge=1, le=30, description="Videos per niche")


class AsyncAnalyzeRequest(BaseModel):
    """Fire-and-forget pipeline request — returns a task_id immediately."""
    seed_keywords: list[str] = Field(..., min_length=1)
    top_n: int = Field(default=10, ge=1, le=50)
    videos_per_niche: int = Field(default=10, ge=1, le=30)


class VideoFactoryStartRequest(BaseModel):
    """Request body for starting a compilation video factory job."""
    niche: str = Field(..., min_length=1, description="YouTube niche to produce a compilation video for")
    target_duration_minutes: int = Field(default=8, ge=3, le=15, description="Target video duration: 3 | 5 | 8 | 10 | 15")
    orientation: str = Field(default="landscape", description="Video orientation: landscape (16:9) | portrait (9:16)")
    transition_style: str = Field(default="crossfade", description="Transition style: crossfade | cut | fade")
    use_gpu: bool = Field(default=True, description="Use GPU acceleration for rendering")
    copyright_strict: bool = Field(default=False, description="Fail on copyright warnings")
    # Extended settings for CI → VF workflow
    enable_voiceover: bool = Field(default=False, description="Enable AI voiceover narration")
    enable_subtitles: bool = Field(default=False, description="Enable subtitle generation")
    enable_thumbnail: bool = Field(default=True, description="Generate a thumbnail")
    enable_background_music: bool = Field(default=False, description="Add background music track")
    enable_transitions: bool = Field(default=True, description="Enable transitions between clips")


class VideoFactoryJobResponse(BaseModel):
    """Video factory job status response."""
    job_id: str
    niche: str
    status: str
    progress_pct: float
    current_stage: str
    stages_completed: list[str]
    error: str = ""
    created_at: str
    updated_at: str
    completed_at: str | None = None
    output_files: dict[str, str] | None = None


# ── Background task tracker ────────────────────────────────────────────────────

_bg_tasks: dict[str, dict[str, Any]] = {}  # task_id → {status, result, ...}


# ── Application Lifecycle ──────────────────────────────────────────────────────

_pipeline: PipelineOrchestrator | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup/shutdown lifecycle."""
    global _pipeline
    settings = get_settings()
    setup_logging(settings.app.log_level)
    await init_db()
    _pipeline = PipelineOrchestrator()

    # Clean up jobs orphaned by previous server shutdown
    from app.video_factory.job_manager import get_job_manager
    cleaned = await get_job_manager().cleanup_orphaned_jobs()
    if cleaned:
        logger.info("orphaned_jobs_cleaned_on_startup", count=cleaned)

    logger.info("api_started", version=settings.app.version)
    yield
    if _pipeline:
        await _pipeline.close()
    await close_db()
    logger.info("api_shutdown")


# ── Security Headers Middleware ─────────────────────────────────────────────────

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to every response."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if get_settings().is_production:
            response.headers["Strict-Transport-Security"] = (
                "max-age=63072000; includeSubDomains; preload"
            )
        return response


class TimingMiddleware(BaseHTTPMiddleware):
    """Inject Server-Timing header and log request latency."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        t0 = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
        response.headers["Server-Timing"] = f"total;dur={elapsed_ms}"
        response.headers["X-Response-Time"] = f"{elapsed_ms}ms"
        if elapsed_ms > 500:
            logger.warning(
                "slow_request",
                path=request.url.path,
                method=request.method,
                duration_ms=elapsed_ms,
            )
        return response


# ── Structured Error Response ──────────────────────────────────────────────────

class ErrorResponse(BaseModel):
    """Standard error envelope returned by all error handlers."""
    error: str
    detail: str = ""
    status_code: int = 500


# ── FastAPI App ────────────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    """Create the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app.name,
        version=settings.app.version,
        description="YouTube Niche Discovery & Faceless Video Strategy Platform",
        lifespan=lifespan,
        default_response_class=_DefaultJSON,
        docs_url="/docs" if settings.app.debug else None,
        redoc_url="/redoc" if settings.app.debug else None,
    )

    # ── Global exception handlers ──────────────────────────────────────

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        """Return structured JSON for HTTP errors."""
        logger.warning(
            "http_error",
            path=request.url.path,
            status=exc.status_code,
            detail=str(exc.detail),
        )
        return _DefaultJSON(
            status_code=exc.status_code,
            content=ErrorResponse(
                error=f"HTTP {exc.status_code}",
                detail=str(exc.detail),
                status_code=exc.status_code,
            ).model_dump(),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Catch-all for unexpected errors — log full traceback, return safe JSON."""
        logger.error(
            "unhandled_error",
            path=request.url.path,
            method=request.method,
            error=str(exc),
            traceback=traceback.format_exc(),
        )
        detail = str(exc) if settings.app.debug else "An internal error occurred"
        return _DefaultJSON(
            status_code=500,
            content=ErrorResponse(
                error="Internal Server Error",
                detail=detail,
                status_code=500,
            ).model_dump(),
        )

    # GZip — compress responses > 500 bytes (huge win for large JSON payloads)
    app.add_middleware(GZipMiddleware, minimum_size=500)

    # CORS — allow frontend dev server and production origins
    cors_origins = settings.api.cors_origins
    if "http://localhost:3000" not in cors_origins and "*" not in cors_origins:
        cors_origins = [*cors_origins, "http://localhost:3000"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Security headers
    app.add_middleware(SecurityHeadersMiddleware)

    # Request timing / observability
    app.add_middleware(TimingMiddleware)

    # ── Routes ──

    @app.get("/", include_in_schema=False)
    async def root_info():
        """API root — return service info."""
        return {"service": settings.app.name, "version": settings.app.version, "docs": "/docs"}

    @app.get("/health", response_model=HealthResponse)
    async def health_check() -> HealthResponse:
        return HealthResponse(status="ok", version=settings.app.version)

    @app.post("/analyze", response_model=AnalyzeResponse)
    async def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
        """Run the full niche discovery pipeline."""
        if _pipeline is None:
            raise HTTPException(status_code=503, detail="Pipeline not initialized")

        try:
            report = await _pipeline.run_full_pipeline(
                seed_keywords=request.seed_keywords,
                top_n=request.top_n,
                videos_per_niche=request.videos_per_niche,
            )

            response = AnalyzeResponse(
                status="success",
                seed_keywords=report.seed_keywords,
                top_niches=[n.model_dump(mode="json") for n in report.top_niches],
                channel_concepts=[c.model_dump(mode="json") for c in report.channel_concepts],
                video_blueprints={
                    k: [bp.model_dump(mode="json") for bp in v]
                    for k, v in report.video_blueprints.items()
                },
                viral_opportunities={
                    k: [opp.model_dump(mode="json") for opp in v]
                    for k, v in report.viral_opportunities.items()
                },
                topic_velocities={
                    k: v.model_dump(mode="json")
                    for k, v in report.topic_velocities.items()
                },
                thumbnail_patterns={
                    k: v.model_dump(mode="json")
                    for k, v in report.thumbnail_patterns.items()
                },
                ai_insights=report.ai_insights,
                metadata=report.metadata,
            )

            # Persist to database (fire-and-forget, don't block response)
            try:
                from app.database.persistence import persist_analysis_run
                await persist_analysis_run(
                    seed_keywords=request.seed_keywords,
                    report_data=response.model_dump(mode="json"),
                )
            except Exception as persist_err:
                logger.warning("analyze_persist_error", error=str(persist_err))

            return response
        except Exception as e:
            logger.error("analyze_error", error=str(e))
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/discover", response_model=AnalyzeResponse)
    async def discover(request: DiscoverRequest) -> AnalyzeResponse:
        """Automatic niche discovery — no seed keywords required.

        Scans Google Trends, YouTube, Reddit, and autocomplete to find
        trending topics automatically, then runs the full pipeline.
        """
        if _pipeline is None:
            raise HTTPException(status_code=503, detail="Pipeline not initialized")

        try:
            report = await _pipeline.run_discovery_pipeline(
                max_seeds=request.max_seeds,
                deep=request.deep,
                top_n=request.top_n,
                videos_per_niche=request.videos_per_niche,
            )

            response = AnalyzeResponse(
                status="success",
                seed_keywords=report.seed_keywords,
                top_niches=[n.model_dump(mode="json") for n in report.top_niches],
                channel_concepts=[c.model_dump(mode="json") for c in report.channel_concepts],
                video_blueprints={
                    k: [bp.model_dump(mode="json") for bp in v]
                    for k, v in report.video_blueprints.items()
                },
                viral_opportunities={
                    k: [opp.model_dump(mode="json") for opp in v]
                    for k, v in report.viral_opportunities.items()
                },
                topic_velocities={
                    k: v.model_dump(mode="json")
                    for k, v in report.topic_velocities.items()
                },
                thumbnail_patterns={
                    k: v.model_dump(mode="json")
                    for k, v in report.thumbnail_patterns.items()
                },
                ai_insights=report.ai_insights,
                metadata=report.metadata,
            )

            # Persist to database
            try:
                from app.database.persistence import persist_analysis_run
                await persist_analysis_run(
                    seed_keywords=report.seed_keywords,
                    report_data=response.model_dump(mode="json"),
                )
            except Exception as persist_err:
                logger.warning("discover_persist_error", error=str(persist_err))

            return response
        except Exception as e:
            logger.error("discover_error", error=str(e))
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/niches")
    async def list_niches(
        keywords: str = Query(..., description="Comma-separated seed keywords"),
        top_n: int = Query(default=10, ge=1, le=50),
    ) -> dict[str, Any]:
        """Quick niche discovery with GET request."""
        if _pipeline is None:
            raise HTTPException(status_code=503, detail="Pipeline not initialized")

        seeds = [k.strip() for k in keywords.split(",") if k.strip()]
        if not seeds:
            raise HTTPException(status_code=400, detail="No keywords provided")

        report = await _pipeline.run_full_pipeline(seed_keywords=seeds, top_n=top_n)

        return {
            "top_niches": [n.model_dump(mode="json") for n in report.top_niches],
            "metadata": report.metadata,
        }

    @app.get("/cache/stats")
    async def cache_stats() -> dict[str, Any]:
        """Get cache statistics."""
        from app.core.cache import get_cache
        cache = get_cache()
        return cache.stats()

    # ── AI-powered analysis endpoints ──────────────────────────────────

    @app.get("/ai/niche-insights")
    async def ai_niche_insights(
        top_n: int = Query(default=5, ge=1, le=20, description="Number of top niches to analyze"),
    ) -> dict[str, Any]:
        """Get AI-powered niche insights using Gemini.

        Requires a prior /analyze or /discover run so report data is available.
        """
        from app.ai.service import analyze_niches
        if _pipeline is None:
            raise HTTPException(status_code=503, detail="Pipeline not initialized")

        # Use the latest report from the report engine
        report_dir = Path(get_settings().reports.output_directory)
        latest = _latest_report_json(report_dir)
        if latest is None:
            raise HTTPException(status_code=404, detail="No analysis report found. Run /analyze first.")

        niches = latest.get("top_niches", [])[:top_n]
        if not niches:
            raise HTTPException(status_code=404, detail="No niches in the latest report")

        result = await analyze_niches(niches)
        if "error" in result:
            raise HTTPException(status_code=503, detail=result["error"])
        return {"status": "success", "niche_insights": result}

    @app.get("/ai/video-strategy")
    async def ai_video_strategy(
        niche: str = Query(..., description="Niche name to generate strategy for"),
        count: int = Query(default=15, ge=1, le=30, description="Number of video ideas"),
    ) -> dict[str, Any]:
        """Generate AI video strategy ideas for a niche."""
        from app.ai.service import generate_video_strategy

        report_dir = Path(get_settings().reports.output_directory)
        latest = _latest_report_json(report_dir)

        keywords: list[str] = []
        if latest:
            for n in latest.get("top_niches", []):
                if n.get("niche", "").lower() == niche.lower():
                    keywords = n.get("keywords", [])
                    break

        result = await generate_video_strategy(niche, keywords, count=count)
        if "error" in result:
            raise HTTPException(status_code=503, detail=result["error"])

        # Persist video strategy to database
        try:
            from app.database.persistence import persist_video_strategy
            await persist_video_strategy(niche, keywords, result)
        except Exception as persist_err:
            logger.warning("video_strategy_persist_error", error=str(persist_err))

        return {"status": "success", "video_strategy": result}

    @app.get("/ai/trend-forecast")
    async def ai_trend_forecast() -> dict[str, Any]:
        """Forecast trends using AI based on topic velocity data."""
        from app.ai.service import forecast_trends

        report_dir = Path(get_settings().reports.output_directory)
        latest = _latest_report_json(report_dir)
        if latest is None:
            raise HTTPException(status_code=404, detail="No analysis report found. Run /analyze first.")

        velocities = latest.get("topic_velocities", {})
        if not velocities:
            raise HTTPException(status_code=404, detail="No velocity data in the latest report")

        niches = latest.get("top_niches", [])[:5]
        result = await forecast_trends(velocities, niches)
        if "error" in result:
            raise HTTPException(status_code=503, detail=result["error"])
        return {"status": "success", "trend_forecast": result}

    # ── Compilation Video Intelligence ───────────────────────────────

    @app.get("/compilation-strategy")
    async def compilation_strategy(
        niche: str = Query(..., description="Niche name to generate compilation strategy for"),
        keywords: str = Query(default="", description="Comma-separated keywords (optional)"),
        use_ai: bool = Query(default=True, description="Enable AI refinement"),
    ) -> dict[str, Any]:
        """Generate a compilation video strategy for a niche.

        Discovers the best source videos, recommends clip segments,
        assembles a paced timeline, and (optionally) refines via AI.
        """
        from app.compilation_engine.engine import CompilationAnalyzer
        from app.connectors.youtube_search import YouTubeSearchConnector

        if _pipeline is None:
            raise HTTPException(status_code=503, detail="Pipeline not initialized")

        kw_list = [k.strip() for k in keywords.split(",") if k.strip()]

        # Try to find stored keywords for this niche from latest report
        if not kw_list:
            report_dir = Path(get_settings().reports.output_directory)
            latest = _latest_report_json(report_dir)
            if latest:
                for n in latest.get("top_niches", []):
                    if n.get("niche", "").lower() == niche.lower():
                        kw_list = n.get("keywords", [])
                        break

        try:
            analyzer = CompilationAnalyzer(_pipeline.yt_search)
            strategy = await analyzer.analyze(niche, kw_list, use_ai=use_ai)
            strategy_dict = strategy.model_dump(mode="json")

            # Persist compilation strategy to database
            try:
                from app.database.persistence import persist_compilation_strategy
                await persist_compilation_strategy(niche, kw_list, strategy_dict)
            except Exception as persist_err:
                logger.warning("compilation_strategy_persist_error", error=str(persist_err))

            return {
                "status": "success",
                "compilation_strategy": strategy_dict,
            }
        except Exception as e:
            logger.error("compilation_strategy_error", niche=niche, error=str(e))
            raise HTTPException(status_code=500, detail=str(e))

    # ── History / Persistence endpoints ────────────────────────────────

    @app.get("/discoveries")
    async def list_discoveries(
        limit: int = Query(default=50, ge=1, le=200),
    ) -> dict[str, Any]:
        """List past analysis/discovery runs persisted in the database."""
        from app.database.persistence import get_analysis_runs
        runs = await get_analysis_runs(limit=limit)
        return {"discoveries": runs, "total": len(runs)}

    @app.get("/persisted-niches")
    async def list_persisted_niches(
        limit: int = Query(default=100, ge=1, le=500),
        min_score: float = Query(default=0.0, ge=0.0),
    ) -> dict[str, Any]:
        """List niches persisted from past analysis runs."""
        from app.database.persistence import get_persisted_niches
        niches = await get_persisted_niches(limit=limit, min_score=min_score)
        return {"niches": niches, "total": len(niches)}

    @app.get("/persisted-niches/{niche_name}/video-ideas")
    async def list_niche_video_ideas(
        niche_name: str,
        limit: int = Query(default=50, ge=1, le=200),
    ) -> dict[str, Any]:
        """List video ideas (blueprints) for a persisted niche."""
        from app.database.persistence import get_video_ideas_for_niche
        ideas = await get_video_ideas_for_niche(niche_name, limit=limit)
        return {"niche": niche_name, "video_ideas": ideas, "total": len(ideas)}

    @app.get("/video-strategies")
    async def list_video_strategies(
        niche: str = Query(default="", description="Filter by niche (optional)"),
        limit: int = Query(default=50, ge=1, le=200),
    ) -> dict[str, Any]:
        """List past AI video strategies persisted in the database."""
        from app.database.persistence import get_video_strategies
        niche_filter = niche if niche else None
        strategies = await get_video_strategies(niche=niche_filter, limit=limit)
        return {"video_strategies": strategies, "total": len(strategies)}

    @app.get("/compilation-strategies")
    async def list_compilation_strategies(
        niche: str = Query(default="", description="Filter by niche (optional)"),
        limit: int = Query(default=50, ge=1, le=200),
    ) -> dict[str, Any]:
        """List past compilation strategies persisted in the database."""
        from app.database.persistence import get_compilation_strategies
        niche_filter = niche if niche else None
        strategies = await get_compilation_strategies(niche=niche_filter, limit=limit)
        return {"compilation_strategies": strategies, "total": len(strategies)}

    # ── Reports endpoints ──────────────────────────────────────────────

    @app.get("/reports")
    async def list_reports(
        search: str = Query(default="", description="Search term to filter reports"),
        limit: int = Query(default=50, ge=1, le=200),
    ) -> dict[str, Any]:
        """List saved analysis reports."""
        report_dir = Path(get_settings().reports.output_directory)
        if not report_dir.is_dir():
            return {"reports": []}

        reports = []
        for f in sorted(report_dir.glob("*.json"), reverse=True)[:limit]:
            try:
                data = _json.loads(f.read_text())
                summary = {
                    "filename": f.name,
                    "seed_keywords": data.get("seed_keywords", []),
                    "niche_count": len(data.get("top_niches", [])),
                    "metadata": data.get("metadata", {}),
                    "created": f.stat().st_mtime,
                }
                if search and search.lower() not in _json.dumps(summary).lower():
                    continue
                reports.append(summary)
            except Exception:
                continue
        return {"reports": reports}

    @app.get("/reports/{filename}")
    async def get_report(filename: str) -> dict[str, Any]:
        """Get a single report by filename."""
        report_dir = Path(get_settings().reports.output_directory)
        path = report_dir / filename
        if not path.exists() or not path.suffix == ".json":
            raise HTTPException(status_code=404, detail="Report not found")
        try:
            data = _json.loads(path.read_text())
            return {"status": "success", "report": data}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/reports/{filename}/download")
    async def download_report(
        filename: str,
        format: str = Query(default="json", description="json or markdown"),
    ) -> Response:
        """Download a report in JSON or Markdown format."""
        report_dir = Path(get_settings().reports.output_directory)

        if format == "markdown":
            md_name = filename.replace(".json", ".md")
            path = report_dir / md_name
            if path.exists():
                return Response(
                    content=path.read_text(),
                    media_type="text/markdown",
                    headers={"Content-Disposition": f'attachment; filename="{md_name}"'},
                )
            raise HTTPException(status_code=404, detail="Markdown report not found")

        path = report_dir / filename
        if not path.exists():
            raise HTTPException(status_code=404, detail="Report not found")
        return Response(
            content=path.read_text(),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    # ── Background / async pipeline ───────────────────────────────────

    @app.post("/analyze/async")
    async def analyze_async(
        request: AsyncAnalyzeRequest,
        background_tasks: BackgroundTasks,
    ) -> dict[str, Any]:
        """Fire-and-forget pipeline — returns task_id immediately.

        Poll GET /tasks/{task_id} for status and results.
        """
        import uuid

        if _pipeline is None:
            raise HTTPException(status_code=503, detail="Pipeline not initialized")

        task_id = uuid.uuid4().hex[:12]
        _bg_tasks[task_id] = {"status": "running", "started": time.time()}

        async def _run() -> None:
            try:
                report = await _pipeline.run_full_pipeline(
                    seed_keywords=request.seed_keywords,
                    top_n=request.top_n,
                    videos_per_niche=request.videos_per_niche,
                )
                _bg_tasks[task_id] = {
                    "status": "completed",
                    "started": _bg_tasks[task_id]["started"],
                    "finished": time.time(),
                    "result": {
                        "seed_keywords": report.seed_keywords,
                        "niche_count": len(report.top_niches),
                        "metadata": report.metadata,
                    },
                }
            except Exception as exc:
                _bg_tasks[task_id] = {
                    "status": "failed",
                    "started": _bg_tasks[task_id]["started"],
                    "finished": time.time(),
                    "error": str(exc),
                }

        background_tasks.add_task(_run)
        return {"task_id": task_id, "status": "accepted"}

    @app.get("/tasks/{task_id}")
    async def get_task_status(task_id: str) -> dict[str, Any]:
        """Poll background pipeline task status."""
        if task_id not in _bg_tasks:
            raise HTTPException(status_code=404, detail="Task not found")
        return {"task_id": task_id, **_bg_tasks[task_id]}

    # ── Dashboard batch endpoint ──────────────────────────────────────

    @app.get("/dashboard-data")
    async def dashboard_data() -> dict[str, Any]:
        """Single aggregated endpoint for the frontend dashboard.

        Returns the latest report summary, cache stats, and health
        in one round-trip instead of 3+ separate calls.
        """
        from app.core.cache import get_cache

        result: dict[str, Any] = {
            "health": {"status": "ok", "version": get_settings().app.version},
            "cache": get_cache().stats(),
        }

        # Latest report summary
        report_dir = Path(get_settings().reports.output_directory)
        latest = _latest_report_json(report_dir)
        if latest:
            result["latest_report"] = {
                "seed_keywords": latest.get("seed_keywords", []),
                "niche_count": len(latest.get("top_niches", [])),
                "top_niches": latest.get("top_niches", [])[:5],
                "metadata": latest.get("metadata", {}),
            }
        else:
            result["latest_report"] = None

        # Recent reports list (last 10)
        if report_dir.is_dir():
            reports = []
            for f in sorted(report_dir.glob("*.json"), reverse=True)[:10]:
                try:
                    data = _json.loads(f.read_text())
                    reports.append({
                        "filename": f.name,
                        "seed_keywords": data.get("seed_keywords", []),
                        "niche_count": len(data.get("top_niches", [])),
                        "created": f.stat().st_mtime,
                    })
                except Exception:
                    continue
            result["recent_reports"] = reports
        else:
            result["recent_reports"] = []

        return result

    # ── Video Factory endpoints ────────────────────────────────────────

    @app.post("/video-factory/start")
    async def video_factory_start(body: VideoFactoryStartRequest) -> dict[str, Any]:
        """Start a new compilation video factory job.

        Launches the compilation pipeline in the background:
        strategy → download → extract → validate → copyright → timeline → assemble → thumbnail → metadata.
        Returns a job_id for polling progress via /video-factory/status/{job_id}.
        """
        from app.video_factory.job_manager import get_job_manager
        from app.video_factory.models import VideoSettings, VideoOrientation

        manager = get_job_manager()

        orientation = (
            VideoOrientation.PORTRAIT
            if body.orientation == "portrait"
            else VideoOrientation.LANDSCAPE
        )

        settings = VideoSettings(
            target_duration_minutes=body.target_duration_minutes,
            orientation=orientation,
            transition_style=body.transition_style,
            use_gpu=body.use_gpu,
            copyright_strict=body.copyright_strict,
            enable_voiceover=body.enable_voiceover,
            enable_subtitles=body.enable_subtitles,
            enable_thumbnail=body.enable_thumbnail,
            enable_background_music=body.enable_background_music,
            enable_transitions=body.enable_transitions,
        )

        job = await manager.submit_job(
            niche=body.niche,
            settings=settings,
        )

        return {
            "status": "accepted",
            "job_id": job.job_id,
            "niche": job.niche,
            "message": f"Compilation video job started for niche: {body.niche}",
        }

    @app.get("/video-factory/status/{job_id}")
    async def video_factory_status(job_id: str) -> dict[str, Any]:
        """Get the status of a compilation video factory job."""
        from app.video_factory.job_manager import get_job_manager

        manager = get_job_manager()
        job = await manager.get_job(job_id)

        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        output_files = None
        if job.output and job.status.value == "completed":
            output_files = {
                "video": job.output.video_path,
                "thumbnail": job.output.thumbnail_path,
                "metadata": job.output.metadata_path,
            }

        # Build clips list for the frontend clip editor
        clips = None
        if job.output and job.output.extraction.clips:
            clips = [
                {
                    "clip_id": c.clip_id,
                    "source_video_id": c.source_video_id,
                    "duration_seconds": c.duration_seconds,
                    "segment_type": c.segment_type,
                    "energy_level": c.energy_level,
                    "position": c.position,
                    "is_valid": c.is_valid,
                }
                for c in job.output.extraction.clips
            ]

        return {
            "job_id": job.job_id,
            "niche": job.niche,
            "status": job.status.value,
            "progress_pct": job.progress_pct,
            "current_stage": job.current_stage,
            "stages_completed": job.stages_completed,
            "error": job.error,
            "created_at": job.created_at.isoformat(),
            "updated_at": job.updated_at.isoformat(),
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "output_files": output_files,
            "clips": clips,
            "strategy": (
                job.output.strategy_summary
                if job.output and job.output.strategy_summary
                else None
            ),
            "metadata": (
                job.output.metadata.model_dump()
                if job.output and job.output.metadata and job.output.metadata.title
                else None
            ),
            "copyright_report": (
                job.output.copyright_report.model_dump()
                if job.output and job.output.copyright_report
                else None
            ),
            "timeline_info": (
                {
                    "entries": len(job.output.timeline.entries),
                    "total_duration": job.output.timeline.total_duration_seconds,
                    "target_duration": job.output.timeline.target_duration_seconds,
                }
                if job.output and job.output.timeline.entries
                else None
            ),
            "settings": job.settings.model_dump() if job.settings else None,
        }

    @app.get("/video-factory/download/{job_id}")
    async def video_factory_download(
        job_id: str,
        file: str = Query(default="video", description="File to download: video | thumbnail | subtitles | metadata"),
    ) -> Response:
        """Download a video factory output file."""
        from app.video_factory.job_manager import get_job_manager

        manager = get_job_manager()
        job = await manager.get_job(job_id)

        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        if job.status.value != "completed" or not job.output:
            raise HTTPException(status_code=400, detail="Job not completed yet")

        file_map = {
            "video": (job.output.video_path, "video/mp4", "video.mp4"),
            "thumbnail": (job.output.thumbnail_path, "image/png", "thumbnail.png"),
            "metadata": (job.output.metadata_path, "application/json", "metadata.json"),
        }

        if file not in file_map:
            raise HTTPException(status_code=400, detail=f"Unknown file type: {file}")

        file_path, media_type, filename = file_map[file]

        if not file_path or not Path(file_path).exists():
            raise HTTPException(status_code=404, detail=f"File not found: {file}")

        from starlette.responses import FileResponse
        return FileResponse(
            path=file_path,
            media_type=media_type,
            filename=filename,
        )

    @app.get("/video-factory/jobs")
    async def video_factory_list_jobs(
        status: str = Query(default="", description="Filter by status"),
        limit: int = Query(default=50, ge=1, le=200),
    ) -> dict[str, Any]:
        """List all video factory jobs."""
        from app.video_factory.job_manager import get_job_manager
        from app.video_factory.models import JobStatus

        manager = get_job_manager()

        status_filter = None
        if status:
            try:
                status_filter = JobStatus(status)
            except ValueError:
                pass

        jobs = await manager.list_jobs(status_filter=status_filter, limit=limit)

        return {
            "jobs": [
                {
                    "job_id": j.job_id,
                    "niche": j.niche,
                    "status": j.status.value,
                    "progress_pct": j.progress_pct,
                    "current_stage": j.current_stage,
                    "created_at": j.created_at.isoformat(),
                    "error": j.error,
                }
                for j in jobs
            ],
            "total": len(jobs),
        }

    @app.post("/video-factory/cancel/{job_id}")
    async def video_factory_cancel(job_id: str) -> dict[str, Any]:
        """Cancel a running video factory job."""
        from app.video_factory.job_manager import get_job_manager

        manager = get_job_manager()
        cancelled = await manager.cancel_job(job_id)

        if not cancelled:
            raise HTTPException(status_code=400, detail="Job cannot be cancelled (not running or not found)")

        return {"status": "cancelled", "job_id": job_id}

    # ── Video Factory — Create from CI strategy ────────────────────────

    @app.post("/video-factory/create")
    async def video_factory_create(body: VideoFactoryStartRequest) -> dict[str, Any]:
        """Create a video from Compilation Intelligence results.

        Same as /video-factory/start but exposed as a dedicated
        endpoint for the CI → VF workflow. Accepts the full
        expanded settings payload.
        """
        from app.video_factory.job_manager import get_job_manager
        from app.video_factory.models import VideoSettings, VideoOrientation

        manager = get_job_manager()

        orientation = (
            VideoOrientation.PORTRAIT
            if body.orientation == "portrait"
            else VideoOrientation.LANDSCAPE
        )

        settings = VideoSettings(
            target_duration_minutes=body.target_duration_minutes,
            orientation=orientation,
            transition_style=body.transition_style if body.enable_transitions else "cut",
            use_gpu=body.use_gpu,
            copyright_strict=body.copyright_strict,
            enable_voiceover=body.enable_voiceover,
            enable_subtitles=body.enable_subtitles,
            enable_thumbnail=body.enable_thumbnail,
            enable_background_music=body.enable_background_music,
            enable_transitions=body.enable_transitions,
        )

        job = await manager.submit_job(niche=body.niche, settings=settings)

        return {
            "status": "accepted",
            "job_id": job.job_id,
            "niche": job.niche,
            "settings": settings.model_dump(),
            "message": f"Compilation video job created for niche: {body.niche}",
        }

    # ── Video Factory — Preview / stream ───────────────────────────────

    @app.get("/video-factory/preview/{job_id}")
    async def video_factory_preview(job_id: str) -> dict[str, Any]:
        """Get preview metadata for a completed video factory job.

        Returns metadata, streaming URL, and asset info for the
        frontend video player and preview screen.
        """
        from app.video_factory.job_manager import get_job_manager

        manager = get_job_manager()
        job = await manager.get_job(job_id)

        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        if not job.output or job.status.value != "completed":
            raise HTTPException(status_code=400, detail="Job not completed yet")

        video_path = Path(job.output.video_path) if job.output.video_path else None
        thumb_path = Path(job.output.thumbnail_path) if job.output.thumbnail_path else None

        video_size_mb = 0.0
        video_exists = False
        if video_path and video_path.exists():
            video_exists = True
            video_size_mb = round(video_path.stat().st_size / (1024 * 1024), 2)

        return {
            "job_id": job_id,
            "niche": job.niche,
            "status": "ready" if video_exists else "unavailable",
            "stream_url": f"/video-factory/stream/{job_id}" if video_exists else None,
            "download_url": f"/video-factory/download/{job_id}?file=video" if video_exists else None,
            "thumbnail_url": f"/video-factory/download/{job_id}?file=thumbnail" if thumb_path and thumb_path.exists() else None,
            "video_size_mb": video_size_mb,
            "metadata": (
                job.output.metadata.model_dump()
                if job.output.metadata and job.output.metadata.title
                else None
            ),
            "timeline_info": (
                {
                    "entries": len(job.output.timeline.entries),
                    "total_duration": job.output.timeline.total_duration_seconds,
                    "target_duration": job.output.timeline.target_duration_seconds,
                }
                if job.output.timeline.entries
                else None
            ),
            "clips_used": job.output.assembly.clips_used if job.output.assembly else 0,
            "copyright_safe": (
                job.output.copyright_report.is_safe
                if job.output.copyright_report
                else True
            ),
            "settings": job.settings.model_dump() if job.settings else None,
            "created_at": job.created_at.isoformat(),
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        }

    @app.get("/video-factory/stream/{job_id}")
    async def video_factory_stream(job_id: str, request: Request) -> Response:
        """Stream a completed video with HTTP Range request support.

        Enables the HTML5 <video> element to seek and play instantly
        without downloading the entire file first.
        """
        from app.video_factory.job_manager import get_job_manager

        manager = get_job_manager()
        job = await manager.get_job(job_id)

        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        if not job.output or job.status.value != "completed" or not job.output.video_path:
            raise HTTPException(status_code=400, detail="Video not available")

        video_path = Path(job.output.video_path)
        if not video_path.exists():
            raise HTTPException(status_code=404, detail="Video file not found on disk")

        file_size = video_path.stat().st_size
        range_header = request.headers.get("range")

        if range_header:
            # Parse Range: bytes=start-end
            range_spec = range_header.replace("bytes=", "")
            parts = range_spec.split("-")
            start = int(parts[0]) if parts[0] else 0
            end = int(parts[1]) if parts[1] else file_size - 1
            end = min(end, file_size - 1)
            content_length = end - start + 1

            def _iter_range():
                with open(video_path, "rb") as f:
                    f.seek(start)
                    remaining = content_length
                    while remaining > 0:
                        chunk = f.read(min(65536, remaining))
                        if not chunk:
                            break
                        remaining -= len(chunk)
                        yield chunk

            from starlette.responses import StreamingResponse
            return StreamingResponse(
                _iter_range(),
                status_code=206,
                media_type="video/mp4",
                headers={
                    "Content-Range": f"bytes {start}-{end}/{file_size}",
                    "Accept-Ranges": "bytes",
                    "Content-Length": str(content_length),
                    "Cache-Control": "no-cache",
                },
            )
        else:
            # Full file response
            from starlette.responses import FileResponse
            return FileResponse(
                path=str(video_path),
                media_type="video/mp4",
                headers={
                    "Accept-Ranges": "bytes",
                    "Content-Length": str(file_size),
                },
            )

    # ── Video Factory — Delete ─────────────────────────────────────────

    @app.delete("/video-factory/delete/{job_id}")
    async def video_factory_delete(job_id: str) -> dict[str, Any]:
        """Delete a video factory job and all its output files.

        Removes the job from memory and deletes the output directory
        (data/compiled_videos/{job_id}/) if it exists.
        """
        import shutil
        from app.video_factory.job_manager import get_job_manager

        manager = get_job_manager()
        job = await manager.get_job(job_id)

        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        # Delete output files from disk
        files_deleted = False
        if job.output and job.output.output_dir:
            output_dir = Path(job.output.output_dir)
            if output_dir.exists():
                shutil.rmtree(output_dir, ignore_errors=True)
                files_deleted = True

        # Remove from DB + memory
        await manager.delete_job(job_id)

        logger.info("factory_job_deleted", job_id=job_id, files_deleted=files_deleted)

        return {
            "status": "deleted",
            "job_id": job_id,
            "files_deleted": files_deleted,
        }

    # ══════════════════════════════════════════════════════════════════
    #  VIDEO EDITOR — Timeline editing & preview rendering endpoints
    # ══════════════════════════════════════════════════════════════════

    class EditorTimelineSaveRequest(BaseModel):
        """Request body to save an editor timeline for a job."""
        job_id: str = Field(..., description="The job to save timeline for")
        clips: list[dict[str, Any]] = Field(default_factory=list)
        transitions: list[dict[str, Any]] = Field(default_factory=list)
        markers: list[dict[str, Any]] = Field(default_factory=list)
        text_overlays: list[dict[str, Any]] = Field(default_factory=list)
        orientation: str = Field(default="horizontal")
        resolution: str = Field(default="1080p")
        target_duration_seconds: float = Field(default=480)
        max_scene_duration: float | None = None
        background_audio: str = Field(default="none")

    class EditorRenderRequest(BaseModel):
        """Request body to trigger a render from the editor."""
        job_id: str = Field(..., description="Source job ID")
        is_preview: bool = Field(default=False, description="Quick 720p preview or full render")
        clips: list[dict[str, Any]] = Field(default_factory=list)
        transitions: list[dict[str, Any]] = Field(default_factory=list)
        markers: list[dict[str, Any]] = Field(default_factory=list)
        text_overlays: list[dict[str, Any]] = Field(default_factory=list)
        orientation: str = Field(default="horizontal")
        resolution: str = Field(default="1080p")
        target_duration_seconds: float = Field(default=480)
        max_scene_duration: float | None = None
        background_audio: str = Field(default="none")

    @app.get("/video-editor/clips/{job_id}")
    async def editor_get_clips(job_id: str) -> dict[str, Any]:
        """Get clip library for a completed job.

        Returns all extracted clips with file paths for the
        editor clip library panel.
        """
        from app.video_factory.job_manager import get_job_manager

        manager = get_job_manager()
        job = await manager.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        if not job.output:
            raise HTTPException(status_code=400, detail="Job has no output yet")

        clips = []
        for c in (job.output.extraction.clips or []):
            clips.append({
                "clip_id": c.clip_id,
                "source_video_id": c.source_video_id,
                "source_file_path": c.file_path,
                "start_seconds": c.start_seconds,
                "end_seconds": c.end_seconds,
                "duration_seconds": c.duration_seconds,
                "segment_type": c.segment_type,
                "energy_level": c.energy_level,
                "position": c.position,
                "is_valid": c.is_valid,
                "width": c.width,
                "height": c.height,
                "file_size_mb": c.file_size_mb,
            })

        # Also include the compiled timeline order
        timeline_entries = []
        if job.output.timeline and job.output.timeline.entries:
            for e in job.output.timeline.entries:
                timeline_entries.append({
                    "position": e.position,
                    "clip_id": e.clip_id,
                    "clip_file_path": e.clip_file_path,
                    "source_video_id": e.source_video_id,
                    "start_seconds": e.start_seconds,
                    "end_seconds": e.end_seconds,
                    "duration_seconds": e.duration_seconds,
                    "segment_type": e.segment_type,
                    "energy_level": e.energy_level,
                    "transition": e.transition,
                })

        return {
            "job_id": job_id,
            "niche": job.niche,
            "clips": clips,
            "timeline": timeline_entries,
            "total_duration": job.output.timeline.total_duration_seconds if job.output.timeline else 0,
            "settings": job.settings.model_dump() if job.settings else None,
        }

    @app.post("/video-editor/save-timeline")
    async def editor_save_timeline(body: EditorTimelineSaveRequest) -> dict[str, Any]:
        """Save the current editor timeline state.

        Persists the timeline configuration to disk so it can
        be reloaded later.
        """
        import json as json_mod

        job_dir = Path("data/video_factory") / body.job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        timeline_path = job_dir / "editor_timeline.json"

        timeline_data = body.model_dump()
        with open(timeline_path, "w") as f:
            json_mod.dump(timeline_data, f, indent=2)

        logger.info("editor_timeline_saved", job_id=body.job_id, clips=len(body.clips))

        return {
            "status": "saved",
            "job_id": body.job_id,
            "clips_count": len(body.clips),
            "file": str(timeline_path),
        }

    @app.get("/video-editor/load-timeline/{job_id}")
    async def editor_load_timeline(job_id: str) -> dict[str, Any]:
        """Load a previously saved editor timeline."""
        import json as json_mod

        timeline_path = Path("data/video_factory") / job_id / "editor_timeline.json"

        if not timeline_path.exists():
            return {"job_id": job_id, "found": False, "timeline": None}

        with open(timeline_path) as f:
            data = json_mod.load(f)

        return {"job_id": job_id, "found": True, "timeline": data}

    # In-memory tracker for editor renders
    _editor_renders: dict[str, dict[str, Any]] = {}

    @app.post("/video-editor/render")
    async def editor_render(body: EditorRenderRequest, background_tasks: BackgroundTasks) -> dict[str, Any]:
        """Trigger a render from the editor timeline.

        Runs asynchronously in the background. Returns a render_id
        for polling status. Preview renders use 720p / ultrafast.
        """
        import uuid
        from app.video_factory.timeline_engine import TimelineEngine

        render_id = str(uuid.uuid4())[:12]
        render_type = "preview" if body.is_preview else "final"

        # Parse the payload
        engine = TimelineEngine(output_dir="data/video_factory")
        payload = body.model_dump()
        payload["is_preview"] = body.is_preview

        _editor_renders[render_id] = {
            "render_id": render_id,
            "job_id": body.job_id,
            "type": render_type,
            "status": "queued",
            "progress_pct": 0.0,
            "output_path": None,
            "error": None,
        }

        async def _do_render():
            try:
                _editor_renders[render_id]["status"] = "rendering"
                config = TimelineEngine.parse_timeline_payload(payload)

                def _on_progress(pct: float):
                    _editor_renders[render_id]["progress_pct"] = pct

                output = await engine.render(
                    config=config,
                    job_id=f"{body.job_id}_editor_{render_id}",
                    on_progress=_on_progress,
                )
                _editor_renders[render_id]["status"] = "completed"
                _editor_renders[render_id]["progress_pct"] = 100.0
                _editor_renders[render_id]["output_path"] = output
            except Exception as exc:
                logger.error("editor_render_failed", render_id=render_id, error=str(exc))
                _editor_renders[render_id]["status"] = "failed"
                _editor_renders[render_id]["error"] = str(exc)

        background_tasks.add_task(_do_render)

        return {
            "render_id": render_id,
            "job_id": body.job_id,
            "type": render_type,
            "status": "queued",
        }

    @app.get("/video-editor/render-status/{render_id}")
    async def editor_render_status(render_id: str) -> dict[str, Any]:
        """Poll editor render progress."""
        info = _editor_renders.get(render_id)
        if not info:
            raise HTTPException(status_code=404, detail="Render not found")
        return info

    @app.get("/video-editor/render-stream/{render_id}")
    async def editor_render_stream(render_id: str, request: Request) -> Response:
        """Stream a rendered editor video with Range support."""
        info = _editor_renders.get(render_id)
        if not info:
            raise HTTPException(status_code=404, detail="Render not found")
        if info["status"] != "completed" or not info["output_path"]:
            raise HTTPException(status_code=400, detail="Render not ready")

        video_path = Path(info["output_path"])
        if not video_path.exists():
            raise HTTPException(status_code=404, detail="Rendered file not found")

        file_size = video_path.stat().st_size
        range_header = request.headers.get("range")

        if range_header:
            range_spec = range_header.replace("bytes=", "")
            parts = range_spec.split("-")
            start = int(parts[0]) if parts[0] else 0
            end = int(parts[1]) if parts[1] else file_size - 1
            end = min(end, file_size - 1)
            content_length = end - start + 1

            def _iter_range():
                with open(video_path, "rb") as f:
                    f.seek(start)
                    remaining = content_length
                    while remaining > 0:
                        chunk = f.read(min(65536, remaining))
                        if not chunk:
                            break
                        remaining -= len(chunk)
                        yield chunk

            from starlette.responses import StreamingResponse
            return StreamingResponse(
                _iter_range(),
                status_code=206,
                media_type="video/mp4",
                headers={
                    "Content-Range": f"bytes {start}-{end}/{file_size}",
                    "Accept-Ranges": "bytes",
                    "Content-Length": str(content_length),
                },
            )
        else:
            from starlette.responses import FileResponse
            return FileResponse(
                path=str(video_path),
                media_type="video/mp4",
                headers={"Accept-Ranges": "bytes", "Content-Length": str(file_size)},
            )

    return app


def _latest_report_json(report_dir: Path) -> dict[str, Any] | None:
    """Load the most recent JSON report file."""
    if not report_dir.is_dir():
        return None

    json_files = sorted(report_dir.glob("*.json"), reverse=True)
    if not json_files:
        return None

    try:
        with open(json_files[0]) as f:
            return _json.load(f)  # type: ignore[no-any-return]
    except Exception:
        return None


app = create_app()
