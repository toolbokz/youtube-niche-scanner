"""SQLAlchemy database models and session management."""
from __future__ import annotations

from datetime import datetime
from typing import AsyncGenerator

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    JSON,
    Boolean,
    Index,
)
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config.settings import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


# ── ORM Models ─────────────────────────────────────────────────────────────────

class KeywordRecord(Base):
    __tablename__ = "keywords"

    id = Column(Integer, primary_key=True, autoincrement=True)
    keyword = Column(String(500), nullable=False, index=True)
    source = Column(String(100), default="seed")
    parent_keyword = Column(String(500), nullable=True)
    cluster_id = Column(Integer, nullable=True, index=True)
    search_volume_proxy = Column(Float, default=0.0)
    trend_momentum = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_keyword_source", "keyword", "source"),
    )


class NicheRecord(Base):
    __tablename__ = "niches"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(500), nullable=False, unique=True)
    keywords = Column(JSON, default=list)
    demand_score = Column(Float, default=0.0)
    competition_score = Column(Float, default=0.0)
    trend_momentum = Column(Float, default=0.0)
    virality_score = Column(Float, default=0.0)
    ctr_potential = Column(Float, default=0.0)
    faceless_viability = Column(Float, default=0.0)
    overall_score = Column(Float, default=0.0)
    rank = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_niche_score", "overall_score"),
    )


class VideoIdeaRecord(Base):
    __tablename__ = "video_ideas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    niche_id = Column(Integer, nullable=False, index=True)
    title = Column(String(500), nullable=False)
    topic = Column(String(500), default="")
    angle = Column(String(500), default="")
    target_keywords = Column(JSON, default=list)
    blueprint = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)


class SearchResultRecord(Base):
    __tablename__ = "search_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    query = Column(String(500), nullable=False, index=True)
    title = Column(String(500), default="")
    channel_name = Column(String(300), default="")
    channel_subscribers = Column(Integer, nullable=True)
    view_count = Column(Integer, nullable=True)
    published_at = Column(DateTime, nullable=True)
    video_id = Column(String(20), default="")
    duration_seconds = Column(Integer, nullable=True)
    collected_at = Column(DateTime, default=datetime.utcnow)


class TrendRecord(Base):
    __tablename__ = "trends"

    id = Column(Integer, primary_key=True, autoincrement=True)
    keyword = Column(String(500), nullable=False, index=True)
    source = Column(String(100), default="google_trends")
    direction = Column(String(20), default="stable")
    momentum_score = Column(Float, default=0.0)
    interest_data = Column(JSON, default=list)
    related_queries = Column(JSON, default=list)
    collected_at = Column(DateTime, default=datetime.utcnow)


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    seed_keywords = Column(JSON, default=list)
    status = Column(String(50), default="pending")
    total_keywords = Column(Integer, default=0)
    total_niches = Column(Integer, default=0)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    report_path = Column(String(500), nullable=True)
    run_metadata = Column("metadata", JSON, default=dict)


# ── Engine / Session ───────────────────────────────────────────────────────────

_engine = None
_session_factory = None


def _get_async_url(url: str) -> str:
    """Convert sync DB URL to async equivalent."""
    if url.startswith("sqlite:///"):
        return url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


async def init_db(url: str | None = None) -> None:
    """Initialize database engine and create tables."""
    global _engine, _session_factory

    if url is None:
        url = get_settings().database.url

    async_url = _get_async_url(url)
    _engine = create_async_engine(async_url, echo=get_settings().database.echo)
    _session_factory = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)

    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("database_initialized", url=async_url)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session."""
    if _session_factory is None:
        await init_db()
    assert _session_factory is not None
    async with _session_factory() as session:
        yield session


async def close_db() -> None:
    """Close database engine."""
    global _engine, _session_factory
    if _engine:
        await _engine.dispose()
        _engine = None
        _session_factory = None
