"""Video Factory — Job Manager.

Manages compilation video factory jobs with concurrent execution,
progress tracking, background worker support, **and SQLite persistence**
so that completed/failed jobs survive server restarts.
"""
from __future__ import annotations

import asyncio
import threading
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, delete as sa_delete, update as sa_update

from app.core.logging import get_logger
from app.database.models import VideoFactoryJobRecord, get_session
from app.video_factory.models import (
    JobStatus,
    FactoryJob,
    VideoFactoryOutput,
    VideoSettings,
)

logger = get_logger(__name__)

# Max concurrent video factory jobs
_MAX_CONCURRENT_JOBS = 2


# ── Helpers: convert between Pydantic ↔ DB row ────────────────────────────────

def _job_to_record(job: FactoryJob) -> dict[str, Any]:
    """Convert a FactoryJob to a dict suitable for a DB row."""
    return {
        "job_id": job.job_id,
        "niche": job.niche,
        "status": job.status.value,
        "progress_pct": job.progress_pct,
        "current_stage": job.current_stage,
        "stages_completed": job.stages_completed,
        "error": job.error,
        "config": job.config,
        "settings_json": job.settings.model_dump() if job.settings else {},
        "output_json": job.output.model_dump(mode="json") if job.output else {},
        "created_at": job.created_at,
        "updated_at": job.updated_at,
        "completed_at": job.completed_at,
    }


def _record_to_job(row: VideoFactoryJobRecord) -> FactoryJob:
    """Reconstruct a FactoryJob from a DB row."""
    settings = VideoSettings(**(row.settings_json or {}))
    output = None
    if row.output_json:
        try:
            output = VideoFactoryOutput(**row.output_json)
        except Exception:
            output = None

    return FactoryJob(
        job_id=row.job_id,
        niche=row.niche,
        status=JobStatus(row.status),
        progress_pct=row.progress_pct or 0.0,
        current_stage=row.current_stage or "",
        stages_completed=row.stages_completed or [],
        output=output,
        created_at=row.created_at or datetime.now(timezone.utc),
        updated_at=row.updated_at or datetime.now(timezone.utc),
        completed_at=row.completed_at,
        error=row.error or "",
        config=row.config or {},
        settings=settings,
    )


class FactoryJobManager:
    """Manages video factory jobs with background processing
    and SQLite persistence.

    Running jobs are kept in-memory for live progress updates.
    Completed/failed jobs are persisted to the database so they
    appear after a server restart.
    """

    def __init__(self) -> None:
        # In-memory cache for *running* jobs only (live progress)
        self._active_jobs: dict[str, FactoryJob] = {}
        self._semaphore = asyncio.Semaphore(_MAX_CONCURRENT_JOBS)
        self._tasks: dict[str, asyncio.Task] = {}
        # Thread-safe lock for progress updates from worker threads
        self._lock = threading.Lock()

    # ── Public API (all async) ─────────────────────────────────────────

    async def cleanup_orphaned_jobs(self) -> int:
        """Mark any queued/in-progress jobs as failed on startup.

        These are jobs from a previous server session whose background
        tasks no longer exist.  Returns the number of jobs cleaned up.
        """
        orphan_statuses = [
            s.value for s in (
                JobStatus.QUEUED,
                JobStatus.FETCHING_STRATEGY,
                JobStatus.DOWNLOADING_VIDEOS,
                JobStatus.EXTRACTING_SEGMENTS,
                JobStatus.VALIDATING_CLIPS,
                JobStatus.COPYRIGHT_CHECK,
                JobStatus.BUILDING_TIMELINE,
                JobStatus.ASSEMBLING_VIDEO,
                JobStatus.GENERATING_THUMBNAIL,
                JobStatus.GENERATING_METADATA,
                JobStatus.CLEANING_TEMP,
            )
        ]
        count = 0
        async for session in get_session():
            rows = (
                await session.execute(
                    select(VideoFactoryJobRecord).where(
                        VideoFactoryJobRecord.status.in_(orphan_statuses)
                    )
                )
            ).scalars().all()
            for row in rows:
                row.status = JobStatus.FAILED.value
                row.error = "Server restarted — job was orphaned"
                row.updated_at = datetime.now(timezone.utc)
                count += 1
            await session.commit()

        if count:
            logger.info("orphaned_jobs_cleaned", count=count)
        return count

    async def get_job(self, job_id: str) -> FactoryJob | None:
        """Get a job by ID — checks in-memory first, then DB."""
        # Fast path: running job in memory
        if job_id in self._active_jobs:
            return self._active_jobs[job_id]

        # Slow path: completed/failed → DB
        async for session in get_session():
            row = (
                await session.execute(
                    select(VideoFactoryJobRecord).where(
                        VideoFactoryJobRecord.job_id == job_id
                    )
                )
            ).scalar_one_or_none()
            if row:
                return _record_to_job(row)
        return None

    async def list_jobs(
        self,
        status_filter: JobStatus | None = None,
        limit: int = 50,
    ) -> list[FactoryJob]:
        """List jobs from DB + in-memory active jobs, newest first."""
        jobs_map: dict[str, FactoryJob] = {}

        # 1. Load from DB
        async for session in get_session():
            stmt = select(VideoFactoryJobRecord).order_by(
                VideoFactoryJobRecord.created_at.desc()
            )
            if status_filter:
                stmt = stmt.where(
                    VideoFactoryJobRecord.status == status_filter.value
                )
            stmt = stmt.limit(limit)
            rows = (await session.execute(stmt)).scalars().all()
            for row in rows:
                jobs_map[row.job_id] = _record_to_job(row)

        # 2. Overlay in-memory active jobs (they have fresher progress)
        for jid, job in self._active_jobs.items():
            if status_filter and job.status != status_filter:
                continue
            jobs_map[jid] = job

        # Sort newest first and limit
        result = sorted(jobs_map.values(), key=lambda j: j.created_at, reverse=True)
        return result[:limit]

    async def submit_job(
        self,
        niche: str,
        settings: VideoSettings | None = None,
        config: dict[str, Any] | None = None,
    ) -> FactoryJob:
        """Submit a new compilation video factory job.

        Persists to DB immediately, then starts background processing.
        """
        job_id = uuid.uuid4().hex[:12]
        vs = settings or VideoSettings()

        job = FactoryJob(
            job_id=job_id,
            niche=niche,
            status=JobStatus.QUEUED,
            progress_pct=0.0,
            current_stage="queued",
            config=config or {},
            settings=vs,
        )

        # Persist to DB
        await self._save_job(job)

        # Keep in memory for live progress
        self._active_jobs[job_id] = job

        logger.info("factory_job_submitted", job_id=job_id, niche=niche)

        # Start background processing
        task = asyncio.create_task(self._run_job(job_id, niche, vs))
        self._tasks[job_id] = task

        return job

    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a running job."""
        task = self._tasks.get(job_id)
        job = self._active_jobs.get(job_id)

        if task and not task.done():
            task.cancel()
            if job:
                job.status = JobStatus.FAILED
                job.error = "Cancelled by user"
                job.updated_at = datetime.now(timezone.utc)
                await self._persist_job(job)
                self._active_jobs.pop(job_id, None)
            logger.info("factory_job_cancelled", job_id=job_id)
            return True

        return False

    async def delete_job(self, job_id: str) -> bool:
        """Delete a job from both memory and database."""
        self._active_jobs.pop(job_id, None)
        self._tasks.pop(job_id, None)

        async for session in get_session():
            await session.execute(
                sa_delete(VideoFactoryJobRecord).where(
                    VideoFactoryJobRecord.job_id == job_id
                )
            )
            await session.commit()
            return True
        return False

    # ── Background runner ──────────────────────────────────────────────

    async def _run_job(
        self,
        job_id: str,
        niche: str,
        settings: VideoSettings,
    ) -> None:
        """Run a job in the background with concurrency control."""
        async with self._semaphore:
            job = self._active_jobs.get(job_id)
            if not job:
                return

            try:
                from app.video_factory.factory_orchestrator import FactoryOrchestrator

                orchestrator = FactoryOrchestrator(settings=settings)

                # Thread-safe progress tracking
                def _on_progress(stage: str, pct: float) -> None:
                    with self._lock:
                        if job_id in self._active_jobs:
                            active = self._active_jobs[job_id]
                            active.current_stage = stage
                            active.progress_pct = pct
                            active.updated_at = datetime.now(timezone.utc)
                            if stage not in active.stages_completed and pct > 0:
                                if active.stages_completed:
                                    if active.stages_completed[-1] != stage:
                                        active.stages_completed.append(stage)
                                else:
                                    active.stages_completed.append(stage)

                orchestrator.set_progress_callback(_on_progress)

                # Run the orchestrator directly in the current event loop.
                # The orchestrator's stages are async; FFmpeg/yt-dlp calls
                # inside use asyncio.create_subprocess_exec which is non-blocking.
                output = await orchestrator.run(
                    niche=niche,
                    job_id=job_id,
                    settings=settings,
                )

                job.output = output
                job.status = JobStatus.COMPLETED
                job.progress_pct = 100.0
                job.current_stage = "completed"
                job.completed_at = datetime.now(timezone.utc)
                job.updated_at = datetime.now(timezone.utc)

                logger.info("factory_job_completed", job_id=job_id, niche=niche)

            except Exception as exc:
                job.status = JobStatus.FAILED
                job.error = str(exc)
                job.current_stage = "failed"
                job.updated_at = datetime.now(timezone.utc)
                logger.error("factory_job_failed", job_id=job_id, error=str(exc))

            finally:
                # Persist final state to DB and remove from active cache
                await self._persist_job(job)
                self._active_jobs.pop(job_id, None)
                self._tasks.pop(job_id, None)

    # ── DB helpers ─────────────────────────────────────────────────────

    async def _save_job(self, job: FactoryJob) -> None:
        """Insert a new job into the database."""
        async for session in get_session():
            record = VideoFactoryJobRecord(**_job_to_record(job))
            session.add(record)
            await session.commit()

    async def _persist_job(self, job: FactoryJob) -> None:
        """Update an existing job row in the database."""
        values = _job_to_record(job)
        job_id = values.pop("job_id")
        async for session in get_session():
            await session.execute(
                sa_update(VideoFactoryJobRecord)
                .where(VideoFactoryJobRecord.job_id == job_id)
                .values(**values)
            )
            await session.commit()


# ── Singleton ──────────────────────────────────────────────────────────────────

_manager: FactoryJobManager | None = None


def get_job_manager() -> FactoryJobManager:
    """Get or create the global FactoryJobManager singleton."""
    global _manager
    if _manager is None:
        _manager = FactoryJobManager()
    return _manager
