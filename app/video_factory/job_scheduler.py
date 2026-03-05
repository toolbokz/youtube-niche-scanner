"""Video Factory — Job Scheduler.

A resource-aware job queue that limits concurrent video rendering
jobs, monitors system load, and pauses new jobs when the machine
is under heavy load.

This turns the Video Factory into a **mini automated video production
server** capable of processing multiple jobs simultaneously without
overloading the system.
"""
from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Callable, Coroutine

from app.config.settings import get_settings
from app.core.logging import get_logger
from app.video_factory.hardware_detector import get_system_load

logger = get_logger(__name__)


class JobScheduler:
    """Resource-aware video job scheduler.

    Parameters
    ----------
    max_concurrent : int
        Maximum number of video jobs running at the same time.
    cpu_threshold : float
        Pause new jobs when CPU load exceeds this percentage.
    memory_threshold : float
        Pause new jobs when memory usage exceeds this percentage.
    poll_interval : float
        Seconds between system load checks when throttled.
    """

    def __init__(
        self,
        max_concurrent: int = 2,
        cpu_threshold: float = 90.0,
        memory_threshold: float = 85.0,
        poll_interval: float = 5.0,
    ) -> None:
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self.max_concurrent = max_concurrent
        self.cpu_threshold = cpu_threshold
        self.memory_threshold = memory_threshold
        self.poll_interval = poll_interval

        # Tracking
        self._active_count = 0
        self._queued_count = 0
        self._total_submitted = 0
        self._lock = asyncio.Lock()

    # ── Public API ─────────────────────────────────────────────────────

    @property
    def active_jobs(self) -> int:
        return self._active_count

    @property
    def queued_jobs(self) -> int:
        return self._queued_count

    @property
    def stats(self) -> dict[str, Any]:
        load = get_system_load()
        return {
            "active_jobs": self._active_count,
            "queued_jobs": self._queued_count,
            "max_concurrent": self.max_concurrent,
            "total_submitted": self._total_submitted,
            "cpu_percent": load["cpu_percent"],
            "memory_percent": load["memory_percent"],
            "throttled": self._is_overloaded(load),
        }

    async def schedule(
        self,
        coro_factory: Callable[[], Coroutine[Any, Any, Any]],
    ) -> asyncio.Task:
        """Schedule a coroutine to run when resources permit.

        The coroutine factory is called only when the job is actually
        started (not when queued).  This prevents premature resource
        allocation.

        Parameters
        ----------
        coro_factory
            A zero-argument callable that returns a coroutine.

        Returns
        -------
        asyncio.Task
            The background task wrapping the job.
        """
        async with self._lock:
            self._total_submitted += 1
            self._queued_count += 1

        task = asyncio.create_task(self._run_with_limits(coro_factory))
        return task

    # ── Internal ───────────────────────────────────────────────────────

    async def _run_with_limits(
        self,
        coro_factory: Callable[[], Coroutine[Any, Any, Any]],
    ) -> Any:
        """Wait for a semaphore slot + acceptable system load, then run."""
        # Wait for concurrency slot
        async with self._semaphore:
            # Wait for system load to be acceptable
            await self._wait_for_resources()

            async with self._lock:
                self._queued_count -= 1
                self._active_count += 1

            logger.info(
                "job_started",
                active=self._active_count,
                queued=self._queued_count,
            )

            try:
                return await coro_factory()
            finally:
                async with self._lock:
                    self._active_count -= 1

                logger.info(
                    "job_finished",
                    active=self._active_count,
                    queued=self._queued_count,
                )

    async def _wait_for_resources(self) -> None:
        """Block until system load is below thresholds."""
        while True:
            load = get_system_load()
            if not self._is_overloaded(load):
                return

            logger.info(
                "scheduler_throttled",
                cpu=load["cpu_percent"],
                memory=load["memory_percent"],
                cpu_threshold=self.cpu_threshold,
                memory_threshold=self.memory_threshold,
            )
            await asyncio.sleep(self.poll_interval)

    def _is_overloaded(self, load: dict[str, float]) -> bool:
        """Return True if the system is under too much load."""
        return (
            load["cpu_percent"] > self.cpu_threshold
            or load["memory_percent"] > self.memory_threshold
        )


# ── Singleton ──────────────────────────────────────────────────────────────────

_scheduler: JobScheduler | None = None


def get_job_scheduler() -> JobScheduler:
    """Get or create the global JobScheduler singleton.

    Reads settings from ``video_processing`` config section.
    """
    global _scheduler
    if _scheduler is None:
        settings = get_settings()
        vp = settings.video_processing
        _scheduler = JobScheduler(
            max_concurrent=vp.max_concurrent_video_jobs,
            cpu_threshold=vp.cpu_load_pause_threshold,
            memory_threshold=vp.memory_load_pause_threshold,
        )
    return _scheduler
