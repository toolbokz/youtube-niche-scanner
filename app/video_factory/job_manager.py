"""Video Factory — Job Manager.

Manages video factory jobs with concurrent execution,
progress tracking, and background worker support.
"""
from __future__ import annotations

import asyncio
import time
import uuid
from datetime import datetime
from typing import Any

from app.core.logging import get_logger
from app.video_factory.models import (
    JobStatus,
    FactoryJob,
    VideoFactoryOutput,
    VoiceConfig,
    AssemblyConfig,
)

logger = get_logger(__name__)

# Max concurrent video factory jobs
_MAX_CONCURRENT_JOBS = 2


class FactoryJobManager:
    """Manages video factory jobs with background processing.

    Supports queuing, parallel execution (up to _MAX_CONCURRENT_JOBS),
    and progress tracking via polling.
    """

    def __init__(self) -> None:
        self._jobs: dict[str, FactoryJob] = {}
        self._semaphore = asyncio.Semaphore(_MAX_CONCURRENT_JOBS)
        self._tasks: dict[str, asyncio.Task] = {}

    @property
    def jobs(self) -> dict[str, FactoryJob]:
        return self._jobs

    def get_job(self, job_id: str) -> FactoryJob | None:
        """Get a job by ID."""
        return self._jobs.get(job_id)

    def list_jobs(
        self,
        status_filter: JobStatus | None = None,
        limit: int = 50,
    ) -> list[FactoryJob]:
        """List jobs, optionally filtered by status."""
        jobs = list(self._jobs.values())
        if status_filter:
            jobs = [j for j in jobs if j.status == status_filter]
        jobs.sort(key=lambda j: j.created_at, reverse=True)
        return jobs[:limit]

    async def submit_job(
        self,
        niche: str,
        voice_config: VoiceConfig | None = None,
        assembly_config: AssemblyConfig | None = None,
        config: dict[str, Any] | None = None,
    ) -> FactoryJob:
        """Submit a new video factory job.

        The job starts processing in the background immediately
        (subject to concurrency limits).

        Parameters
        ----------
        niche : str
            The niche to produce a video for.
        voice_config : VoiceConfig, optional
            Voice synthesis configuration.
        assembly_config : AssemblyConfig, optional
            Video assembly configuration.
        config : dict, optional
            Extra configuration.

        Returns
        -------
        FactoryJob
            The created job with its ID and initial status.
        """
        job_id = uuid.uuid4().hex[:12]

        job = FactoryJob(
            job_id=job_id,
            niche=niche,
            status=JobStatus.QUEUED,
            progress_pct=0.0,
            current_stage="queued",
            config=config or {},
        )
        self._jobs[job_id] = job

        logger.info("factory_job_submitted", job_id=job_id, niche=niche)

        # Start background processing
        task = asyncio.create_task(
            self._run_job(job_id, niche, voice_config, assembly_config)
        )
        self._tasks[job_id] = task

        return job

    async def _run_job(
        self,
        job_id: str,
        niche: str,
        voice_config: VoiceConfig | None,
        assembly_config: AssemblyConfig | None,
    ) -> None:
        """Run a job in the background with concurrency control.

        The pipeline contains synchronous blocking calls (Vertex AI SDK,
        ffmpeg, etc.) so we run the orchestrator in a thread to avoid
        blocking the async event loop.
        """
        async with self._semaphore:
            job = self._jobs.get(job_id)
            if not job:
                return

            try:
                from app.video_factory.factory_orchestrator import FactoryOrchestrator

                orchestrator = FactoryOrchestrator(
                    voice_config=voice_config,
                    assembly_config=assembly_config,
                )

                # Wire up progress tracking
                def _on_progress(stage: str, pct: float) -> None:
                    if job_id in self._jobs:
                        self._jobs[job_id].current_stage = stage
                        self._jobs[job_id].progress_pct = pct
                        self._jobs[job_id].updated_at = datetime.utcnow()
                        if stage not in self._jobs[job_id].stages_completed and pct > 0:
                            if self._jobs[job_id].stages_completed:
                                prev = self._jobs[job_id].stages_completed[-1]
                                if prev != stage:
                                    self._jobs[job_id].stages_completed.append(stage)
                            else:
                                self._jobs[job_id].stages_completed.append(stage)

                orchestrator.set_progress_callback(_on_progress)

                # Run in a thread so synchronous AI/ffmpeg calls
                # don't block the event loop.
                loop = asyncio.get_running_loop()
                output = await loop.run_in_executor(
                    None,
                    lambda: asyncio.run(
                        orchestrator.run(
                            niche=niche,
                            job_id=job_id,
                            voice_config=voice_config,
                            assembly_config=assembly_config,
                        )
                    ),
                )

                job.output = output
                job.status = JobStatus.COMPLETED
                job.progress_pct = 100.0
                job.current_stage = "completed"
                job.completed_at = datetime.utcnow()
                job.updated_at = datetime.utcnow()

                logger.info("factory_job_completed", job_id=job_id, niche=niche)

            except Exception as exc:
                job.status = JobStatus.FAILED
                job.error = str(exc)
                job.current_stage = "failed"
                job.updated_at = datetime.utcnow()
                logger.error("factory_job_failed", job_id=job_id, error=str(exc))

    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a running job."""
        task = self._tasks.get(job_id)
        job = self._jobs.get(job_id)

        if task and not task.done():
            task.cancel()
            if job:
                job.status = JobStatus.FAILED
                job.error = "Cancelled by user"
                job.updated_at = datetime.utcnow()
            logger.info("factory_job_cancelled", job_id=job_id)
            return True

        return False

    def cleanup_old_jobs(self, max_age_hours: int = 24) -> int:
        """Remove completed/failed jobs older than max_age_hours."""
        cutoff = datetime.utcnow()
        removed = 0

        for job_id in list(self._jobs.keys()):
            job = self._jobs[job_id]
            if job.status in (JobStatus.COMPLETED, JobStatus.FAILED):
                age_hours = (cutoff - job.created_at).total_seconds() / 3600
                if age_hours > max_age_hours:
                    del self._jobs[job_id]
                    self._tasks.pop(job_id, None)
                    removed += 1

        return removed


# ── Singleton ──────────────────────────────────────────────────────────────────

_manager: FactoryJobManager | None = None


def get_job_manager() -> FactoryJobManager:
    """Get or create the global FactoryJobManager singleton."""
    global _manager
    if _manager is None:
        _manager = FactoryJobManager()
    return _manager
