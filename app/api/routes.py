"""FastAPI application and routes."""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncGenerator

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response
from pydantic import BaseModel, Field

from app.config import get_settings
from app.core.logging import setup_logging, get_logger
from app.core.pipeline import PipelineOrchestrator
from app.database import init_db, close_db

logger = get_logger(__name__)

# Resolve paths relative to this file
_APP_DIR = Path(__file__).resolve().parent.parent
_STATIC_DIR = _APP_DIR / "static"
_TEMPLATE_DIR = _APP_DIR / "templates"


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
    metadata: dict[str, Any]


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


# ── FastAPI App ────────────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    """Create the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app.name,
        version=settings.app.version,
        description="YouTube Niche Discovery & Faceless Video Strategy Platform",
        lifespan=lifespan,
        docs_url="/docs" if settings.app.debug else None,
        redoc_url="/redoc" if settings.app.debug else None,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.api.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Security headers
    app.add_middleware(SecurityHeadersMiddleware)

    # Mount static assets (CSS, JS)
    if _STATIC_DIR.is_dir():
        app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")

    # ── Routes ──

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    async def dashboard() -> HTMLResponse:
        """Serve the web dashboard."""
        index_path = _TEMPLATE_DIR / "index.html"
        if not index_path.exists():
            raise HTTPException(status_code=404, detail="Dashboard template not found")
        return HTMLResponse(content=index_path.read_text(encoding="utf-8"))

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
                metadata=report.metadata,
            )
        except Exception as e:
            logger.error("analyze_error", error=str(e))
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

    return app


app = create_app()
