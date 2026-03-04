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

            return AnalyzeResponse(
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

            return AnalyzeResponse(
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
