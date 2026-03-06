"""Persistence helpers — save and retrieve analysis results from the database.

Functions in this module are called from API route handlers to ensure
that niche discovery results, video strategies, and compilation strategies
survive server restarts and are browsable from the frontend.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, desc

from app.core.logging import get_logger
from app.database.models import (
    AnalysisRun,
    CompilationStrategyRecord,
    NicheRecord,
    VideoIdeaRecord,
    VideoStrategyRecord,
    get_session,
)

logger = get_logger(__name__)


# ═══════════════════════════════════════════════════════════════════════
#  Niche Discovery Persistence
# ═══════════════════════════════════════════════════════════════════════

async def persist_analysis_run(
    seed_keywords: list[str],
    report_data: dict[str, Any],
    report_path: str | None = None,
) -> int | None:
    """Save a full analysis/discovery run to the database.

    Persists:
    - An ``AnalysisRun`` row tracking the pipeline execution.
    - ``NicheRecord`` rows for each discovered niche (upserted by name).
    - ``VideoIdeaRecord`` rows for each video blueprint.

    Returns the ``AnalysisRun.id`` on success, ``None`` on failure.
    """
    try:
        async for session in get_session():
            # 1. Create AnalysisRun
            top_niches = report_data.get("top_niches", [])
            metadata = report_data.get("metadata", {})

            run = AnalysisRun(
                seed_keywords=seed_keywords,
                status="completed",
                total_keywords=metadata.get("total_keywords_analyzed", 0),
                total_niches=len(top_niches),
                started_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc),
                report_path=report_path,
                run_metadata=metadata,
            )
            session.add(run)
            await session.flush()  # get run.id
            run_id = run.id

            # 2. Upsert NicheRecords
            niche_id_map: dict[str, int] = {}
            for niche_data in top_niches:
                niche_name = niche_data.get("niche", "")
                if not niche_name:
                    continue

                # Check if niche already exists
                stmt = select(NicheRecord).where(NicheRecord.name == niche_name)
                result = await session.execute(stmt)
                existing = result.scalar_one_or_none()

                if existing:
                    # Update scores
                    existing.keywords = niche_data.get("keywords", [])
                    existing.demand_score = niche_data.get("demand_score", 0.0)
                    existing.competition_score = niche_data.get("competition_score", 0.0)
                    existing.trend_momentum = niche_data.get("trend_momentum", 0.0)
                    existing.virality_score = niche_data.get("virality_score", 0.0)
                    existing.ctr_potential = niche_data.get("ctr_potential", 0.0)
                    existing.faceless_viability = niche_data.get("faceless_viability", 0.0)
                    existing.viral_opportunity_score = niche_data.get("viral_opportunity_score", 0.0)
                    existing.topic_velocity_score = niche_data.get("topic_velocity_score", 0.0)
                    existing.overall_score = niche_data.get("overall_score", 0.0)
                    existing.rank = niche_data.get("rank", 0)
                    existing.updated_at = datetime.now(timezone.utc)
                    niche_id_map[niche_name] = existing.id
                else:
                    niche_rec = NicheRecord(
                        name=niche_name,
                        keywords=niche_data.get("keywords", []),
                        demand_score=niche_data.get("demand_score", 0.0),
                        competition_score=niche_data.get("competition_score", 0.0),
                        trend_momentum=niche_data.get("trend_momentum", 0.0),
                        virality_score=niche_data.get("virality_score", 0.0),
                        ctr_potential=niche_data.get("ctr_potential", 0.0),
                        faceless_viability=niche_data.get("faceless_viability", 0.0),
                        viral_opportunity_score=niche_data.get("viral_opportunity_score", 0.0),
                        topic_velocity_score=niche_data.get("topic_velocity_score", 0.0),
                        overall_score=niche_data.get("overall_score", 0.0),
                        rank=niche_data.get("rank", 0),
                    )
                    session.add(niche_rec)
                    await session.flush()
                    niche_id_map[niche_name] = niche_rec.id

            # 3. Save VideoIdeaRecords from blueprints
            video_blueprints = report_data.get("video_blueprints", {})
            for niche_name, blueprints in video_blueprints.items():
                niche_id = niche_id_map.get(niche_name)
                if niche_id is None:
                    continue

                for bp in blueprints:
                    video_idea = bp.get("video_idea", {})
                    idea_rec = VideoIdeaRecord(
                        niche_id=niche_id,
                        title=video_idea.get("title", bp.get("keyword_optimized_title", "")),
                        topic=video_idea.get("topic", ""),
                        angle=video_idea.get("angle", ""),
                        target_keywords=video_idea.get("target_keywords", []),
                        blueprint=bp,
                    )
                    session.add(idea_rec)

            await session.commit()
            logger.info(
                "analysis_run_persisted",
                run_id=run_id,
                niches=len(niche_id_map),
                seeds=len(seed_keywords),
            )
            return run_id

    except Exception as exc:
        logger.error("persist_analysis_run_error", error=str(exc))
        return None


async def get_analysis_runs(
    limit: int = 50,
    status: str | None = None,
) -> list[dict[str, Any]]:
    """Retrieve past analysis runs."""
    try:
        async for session in get_session():
            stmt = select(AnalysisRun).order_by(desc(AnalysisRun.started_at)).limit(limit)
            if status:
                stmt = stmt.where(AnalysisRun.status == status)
            result = await session.execute(stmt)
            runs = result.scalars().all()
            return [
                {
                    "id": r.id,
                    "seed_keywords": r.seed_keywords,
                    "status": r.status,
                    "total_keywords": r.total_keywords,
                    "total_niches": r.total_niches,
                    "started_at": r.started_at.isoformat() if r.started_at else None,
                    "completed_at": r.completed_at.isoformat() if r.completed_at else None,
                    "report_path": r.report_path,
                    "metadata": r.run_metadata or {},
                }
                for r in runs
            ]
    except Exception as exc:
        logger.error("get_analysis_runs_error", error=str(exc))
        return []


async def get_persisted_niches(
    limit: int = 100,
    min_score: float = 0.0,
) -> list[dict[str, Any]]:
    """Retrieve persisted niches ordered by score."""
    try:
        async for session in get_session():
            stmt = (
                select(NicheRecord)
                .where(NicheRecord.overall_score >= min_score)
                .order_by(desc(NicheRecord.overall_score))
                .limit(limit)
            )
            result = await session.execute(stmt)
            niches = result.scalars().all()
            return [
                {
                    "id": n.id,
                    "niche": n.name,
                    "keywords": n.keywords or [],
                    "demand_score": n.demand_score,
                    "competition_score": n.competition_score,
                    "trend_momentum": n.trend_momentum,
                    "virality_score": n.virality_score,
                    "ctr_potential": n.ctr_potential,
                    "faceless_viability": n.faceless_viability,
                    "viral_opportunity_score": n.viral_opportunity_score,
                    "topic_velocity_score": n.topic_velocity_score,
                    "overall_score": n.overall_score,
                    "rank": n.rank,
                    "created_at": n.created_at.isoformat() if n.created_at else None,
                    "updated_at": n.updated_at.isoformat() if n.updated_at else None,
                }
                for n in niches
            ]
    except Exception as exc:
        logger.error("get_persisted_niches_error", error=str(exc))
        return []


async def get_video_ideas_for_niche(niche_name: str, limit: int = 50) -> list[dict[str, Any]]:
    """Retrieve persisted video ideas for a niche."""
    try:
        async for session in get_session():
            # Find niche by name
            stmt = select(NicheRecord).where(NicheRecord.name == niche_name)
            result = await session.execute(stmt)
            niche = result.scalar_one_or_none()
            if not niche:
                return []

            stmt2 = (
                select(VideoIdeaRecord)
                .where(VideoIdeaRecord.niche_id == niche.id)
                .order_by(desc(VideoIdeaRecord.created_at))
                .limit(limit)
            )
            result2 = await session.execute(stmt2)
            ideas = result2.scalars().all()
            return [
                {
                    "id": idea.id,
                    "niche": niche_name,
                    "title": idea.title,
                    "topic": idea.topic,
                    "angle": idea.angle,
                    "target_keywords": idea.target_keywords or [],
                    "blueprint": idea.blueprint or {},
                    "created_at": idea.created_at.isoformat() if idea.created_at else None,
                }
                for idea in ideas
            ]
    except Exception as exc:
        logger.error("get_video_ideas_error", error=str(exc))
        return []


# ═══════════════════════════════════════════════════════════════════════
#  Video Strategy Persistence
# ═══════════════════════════════════════════════════════════════════════

async def persist_video_strategy(
    niche: str,
    keywords: list[str],
    strategy: dict[str, Any],
) -> int | None:
    """Save a video strategy to the database.

    Returns the record ID on success, None on failure.
    """
    try:
        video_ideas = strategy.get("video_ideas", [])
        count = len(video_ideas) if isinstance(video_ideas, list) else 0

        async for session in get_session():
            rec = VideoStrategyRecord(
                niche=niche,
                keywords=keywords,
                strategy=strategy,
                video_count=count,
            )
            session.add(rec)
            await session.commit()
            logger.info("video_strategy_persisted", niche=niche, ideas=count)
            return rec.id
    except Exception as exc:
        logger.error("persist_video_strategy_error", error=str(exc))
        return None


async def get_video_strategies(
    niche: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Retrieve past video strategies, optionally filtered by niche."""
    try:
        async for session in get_session():
            stmt = (
                select(VideoStrategyRecord)
                .order_by(desc(VideoStrategyRecord.created_at))
                .limit(limit)
            )
            if niche:
                stmt = stmt.where(VideoStrategyRecord.niche == niche)
            result = await session.execute(stmt)
            rows = result.scalars().all()
            return [
                {
                    "id": r.id,
                    "niche": r.niche,
                    "keywords": r.keywords or [],
                    "strategy": r.strategy or {},
                    "video_count": r.video_count,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in rows
            ]
    except Exception as exc:
        logger.error("get_video_strategies_error", error=str(exc))
        return []


# ═══════════════════════════════════════════════════════════════════════
#  Compilation Strategy Persistence
# ═══════════════════════════════════════════════════════════════════════

async def persist_compilation_strategy(
    niche: str,
    keywords: list[str],
    strategy_data: dict[str, Any],
) -> int | None:
    """Save a compilation strategy to the database.

    Returns the record ID on success, None on failure.
    """
    try:
        async for session in get_session():
            rec = CompilationStrategyRecord(
                niche=niche,
                keywords=keywords,
                strategy=strategy_data,
                compilation_score=strategy_data.get("compilation_score", 0.0),
                total_source_videos=strategy_data.get("total_source_videos_found", 0),
            )
            session.add(rec)
            await session.commit()
            logger.info(
                "compilation_strategy_persisted",
                niche=niche,
                score=rec.compilation_score,
            )
            return rec.id
    except Exception as exc:
        logger.error("persist_compilation_strategy_error", error=str(exc))
        return None


async def get_compilation_strategies(
    niche: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Retrieve past compilation strategies, optionally filtered by niche."""
    try:
        async for session in get_session():
            stmt = (
                select(CompilationStrategyRecord)
                .order_by(desc(CompilationStrategyRecord.created_at))
                .limit(limit)
            )
            if niche:
                stmt = stmt.where(CompilationStrategyRecord.niche == niche)
            result = await session.execute(stmt)
            rows = result.scalars().all()
            return [
                {
                    "id": r.id,
                    "niche": r.niche,
                    "keywords": r.keywords or [],
                    "strategy": r.strategy or {},
                    "compilation_score": r.compilation_score,
                    "total_source_videos": r.total_source_videos,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in rows
            ]
    except Exception as exc:
        logger.error("get_compilation_strategies_error", error=str(exc))
        return []
