"""Video Factory — Compilation Pipeline Orchestrator.

Orchestrates the complete compilation video production pipeline:

1. Detect Hardware            (GPU encoders, CPU cores)
2. Fetch Compilation Strategy  (via CompilationAnalyzer)
3. Download Source Videos      (via YouTubeDownloader)
4. Extract Segments            (stream copy — no encoding)
5. Validate Clips              (via ClipValidator)
6. Copyright Safety Check      (via CopyrightGuard)
7. Build Compilation Timeline  (via CompilationAssembler)
8. Assemble & Encode Video     (**single-pass** encoding, GPU-accelerated)
9. Generate Thumbnail          (via ThumbnailGenerator)
10. Generate Metadata          (via MetadataGenerator)
11. Cleanup Temp Files

**Optimised architecture:**
- Clip extraction uses **stream copy** (``-c copy``) — zero encoding overhead.
- Clips are extracted **in parallel** (bounded by CPU cores).
- The **only encoding step** is final assembly — one pass.
- GPU acceleration is **auto-detected** (NVENC → QSV → VideoToolbox → CPU).
- The ``veryfast`` CPU preset reduces CPU encoding time by ~40-60%.

**No slides, text panels, or placeholder footage are generated.**
If real video segments cannot be obtained the pipeline FAILS.
"""
from __future__ import annotations

import asyncio
import json
import os
import shutil
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from app.config.settings import get_settings
from app.connectors.youtube_search import YouTubeSearchConnector
from app.core.logging import get_logger
from app.video_factory.models import (
    JobStatus,
    VideoSettings,
    AssemblyConfig,
    AssemblyResult,
    CompilationTimeline,
    CopyrightIssueInfo,
    CopyrightReportInfo,
    DownloadedVideoInfo,
    DownloadStageResult,
    ExtractedClipInfo,
    ExtractionStageResult,
    ThumbnailResult,
    VideoFactoryOutput,
    VideoMetadata,
)

logger = get_logger(__name__)

# Default output base directory
_OUTPUT_BASE = "data/video_factory"


class FactoryOrchestrator:
    """Orchestrates the compilation video production pipeline.

    Usage::

        orchestrator = FactoryOrchestrator()
        output = await orchestrator.run("funny cats")
    """

    def __init__(
        self,
        output_base: str = _OUTPUT_BASE,
        settings: VideoSettings | None = None,
        yt_search: YouTubeSearchConnector | None = None,
    ) -> None:
        self.output_base = output_base
        self.settings = settings or VideoSettings()
        self._progress_callback: Callable[[str, float], None] | None = None

        if yt_search is not None:
            self._yt_search = yt_search
        else:
            cfg = get_settings()
            self._yt_search = YouTubeSearchConnector(cfg.connectors.youtube_search)

    def set_progress_callback(self, callback: Callable[[str, float], None]) -> None:
        """Set a callback for progress updates: callback(stage_name, pct)."""
        self._progress_callback = callback

    def _report(self, stage: str, pct: float) -> None:
        if self._progress_callback:
            self._progress_callback(stage, pct)

    async def run(
        self,
        niche: str,
        job_id: str | None = None,
        settings: VideoSettings | None = None,
    ) -> VideoFactoryOutput:
        """Run the complete compilation pipeline.

        Parameters
        ----------
        niche : str
            The YouTube niche / topic.
        job_id : str, optional
            Pre-assigned job ID.
        settings : VideoSettings, optional
            Override video settings.

        Returns
        -------
        VideoFactoryOutput
            Complete output with path to the final video.

        Raises
        ------
        RuntimeError
            If any critical stage fails (downloading, extraction, assembly).
        """
        job_id = job_id or uuid.uuid4().hex[:12]
        output_dir = os.path.join(self.output_base, job_id)
        os.makedirs(output_dir, exist_ok=True)

        vs = settings or self.settings

        output = VideoFactoryOutput(
            job_id=job_id,
            niche=niche,
            output_dir=output_dir,
            status=JobStatus.QUEUED,
            settings=vs,
        )

        t0 = time.time()
        logger.info("compilation_pipeline_start", job_id=job_id, niche=niche)

        try:
            # ── Step 0: Detect Hardware ────────────────────────────────
            from app.video_factory.hardware_detector import get_hardware_capabilities

            vp_cfg = get_settings().video_processing
            hw = await get_hardware_capabilities(
                prefer_encoder=vp_cfg.gpu_encoder if vp_cfg.enable_gpu_acceleration else "libx264",
            )
            logger.info(
                "hardware_ready",
                encoder=hw.recommended_encoder,
                gpus=hw.available_gpu_encoders,
                cpus=hw.cpu_count,
                parallel_clips=vp_cfg.max_parallel_clip_tasks or hw.max_parallel_clips,
            )

            # ── Step 1: Fetch Compilation Strategy ────────────────────
            self._report("fetching_strategy", 5)
            output.status = JobStatus.FETCHING_STRATEGY

            strategy = await self._fetch_strategy(niche)
            output.strategy_summary = {
                "niche": strategy.niche,
                "source_videos_found": strategy.total_source_videos_found,
                "segments_recommended": len(strategy.recommended_segments),
                "compilation_score": strategy.compilation_score,
                "title": strategy.final_video_concept.title,
                "description": strategy.final_video_concept.description,
            }
            logger.info("step_done", step="strategy", elapsed=round(time.time() - t0, 1))

            # ── Step 2: Download Source Videos ────────────────────────
            self._report("downloading_videos", 15)
            output.status = JobStatus.DOWNLOADING_VIDEOS

            source_videos_data = [
                sv.model_dump() for sv in strategy.source_videos
            ]
            download_result = await self._download_videos(source_videos_data, job_id, vs)
            output.downloads = download_result
            logger.info(
                "step_done", step="download",
                downloaded=len(download_result.downloaded),
                elapsed=round(time.time() - t0, 1),
            )

            # Build video_id → file_path lookup
            source_lookup = {
                d.video_id: d.file_path for d in download_result.downloaded
            }
            # Build video_id → duration lookup
            source_durations = {
                d.video_id: d.duration_seconds for d in download_result.downloaded
            }

            # ── Step 3: Extract Segments ──────────────────────────────
            self._report("extracting_segments", 35)
            output.status = JobStatus.EXTRACTING_SEGMENTS

            segments_data = [seg.model_dump() for seg in strategy.recommended_segments]
            # Add position from video_structure if available
            structure_positions: dict[str, int] = {}
            for item in strategy.video_structure:
                if item.segment and item.segment.source_video_id:
                    key = f"{item.segment.source_video_id}:{item.segment.timestamp_start}"
                    structure_positions[key] = item.position

            for seg in segments_data:
                key = f"{seg['source_video_id']}:{seg['timestamp_start']}"
                if key in structure_positions:
                    seg["position"] = structure_positions[key]

            extraction_result = await self._extract_segments(
                segments_data, source_lookup, job_id, vs, vp_cfg, hw,
            )
            output.extraction = extraction_result
            logger.info(
                "step_done", step="extraction",
                clips=len(extraction_result.clips),
                elapsed=round(time.time() - t0, 1),
            )

            # ── Step 4: Validate Clips ────────────────────────────────
            self._report("validating_clips", 50)
            output.status = JobStatus.VALIDATING_CLIPS

            validated_clips = await self._validate_clips(extraction_result, vs)
            # Update extraction result clip validity
            valid_ids = {v.clip_id for v in validated_clips if v.is_valid}
            for clip in output.extraction.clips:
                clip.is_valid = clip.clip_id in valid_ids

            logger.info(
                "step_done", step="validation",
                valid=len(valid_ids),
                elapsed=round(time.time() - t0, 1),
            )

            if not valid_ids:
                raise RuntimeError("No clips passed validation — cannot assemble video")

            # ── Step 5: Copyright Safety Check ────────────────────────
            self._report("copyright_check", 55)
            output.status = JobStatus.COPYRIGHT_CHECK

            copyright_report = self._copyright_check(
                extraction_result, source_durations, vs,
            )
            output.copyright_report = copyright_report

            if not copyright_report.is_safe and vs.copyright_strict:
                raise RuntimeError(
                    f"Copyright check failed in strict mode: "
                    f"{[i.message for i in copyright_report.issues if i.severity == 'error']}"
                )

            logger.info(
                "step_done", step="copyright",
                safe=copyright_report.is_safe,
                elapsed=round(time.time() - t0, 1),
            )

            # ── Step 6: Build Timeline ────────────────────────────────
            self._report("building_timeline", 60)
            output.status = JobStatus.BUILDING_TIMELINE

            valid_clips = [c for c in output.extraction.clips if c.is_valid]
            timeline = self._build_timeline(valid_clips, vs)
            output.timeline = timeline

            logger.info(
                "step_done", step="timeline",
                entries=len(timeline.entries),
                duration=timeline.total_duration_seconds,
                elapsed=round(time.time() - t0, 1),
            )

            # ── Step 7: Assemble Video ────────────────────────────────
            self._report("assembling_video", 70)
            output.status = JobStatus.ASSEMBLING_VIDEO

            assembly = await self._assemble_video(timeline, output_dir, vs, hw, vp_cfg)
            output.assembly = assembly
            logger.info(
                "step_done", step="assembly",
                size_mb=assembly.file_size_mb,
                elapsed=round(time.time() - t0, 1),
            )

            # ── Step 8: Thumbnail Generation ──────────────────────────
            self._report("generating_thumbnail", 80)
            output.status = JobStatus.GENERATING_THUMBNAIL

            try:
                thumbnail = await self._generate_thumbnail(
                    niche, strategy.final_video_concept.title, output_dir,
                )
                output.thumbnail = thumbnail
                output.thumbnail_path = thumbnail.thumbnail_path
            except Exception as exc:
                logger.warning("thumbnail_generation_failed", error=str(exc))
                # Thumbnail failure is non-fatal

            logger.info("step_done", step="thumbnail", elapsed=round(time.time() - t0, 1))

            # ── Step 9: Metadata Generation ───────────────────────────
            self._report("generating_metadata", 90)
            output.status = JobStatus.GENERATING_METADATA

            try:
                metadata = await self._generate_metadata(
                    niche, strategy, output_dir,
                )
                output.metadata = metadata
                output.metadata_path = os.path.join(output_dir, "metadata.json")
            except Exception as exc:
                logger.warning("metadata_generation_failed", error=str(exc))
                # Use strategy data as fallback metadata
                output.metadata = VideoMetadata(
                    title=strategy.final_video_concept.title,
                    description=strategy.final_video_concept.description,
                    tags=strategy.final_video_concept.tags,
                )
                output.metadata_path = os.path.join(output_dir, "metadata.json")

            # Save metadata JSON
            meta_path = os.path.join(output_dir, "metadata.json")
            with open(meta_path, "w") as f:
                json.dump(output.metadata.model_dump(), f, indent=2)

            logger.info("step_done", step="metadata", elapsed=round(time.time() - t0, 1))

            # ── Step 10: Cleanup & Finalize ───────────────────────────
            self._report("cleaning_temp", 95)
            output.status = JobStatus.CLEANING_TEMP

            # Move draft video to final location
            final_video = os.path.join(output_dir, "video.mp4")
            if os.path.exists(assembly.draft_video_path) and assembly.draft_video_path != final_video:
                shutil.copy2(assembly.draft_video_path, final_video)
            output.video_path = final_video

            # Clean up temp files (source videos, intermediate clips)
            self._cleanup_temp(output_dir)

            # Write manifest
            manifest = {
                "job_id": job_id,
                "niche": niche,
                "title": output.metadata.title or strategy.final_video_concept.title,
                "pipeline": "compilation",
                "files": {
                    "video": "video.mp4",
                    "thumbnail": "thumbnail.png",
                    "metadata": "metadata.json",
                },
                "clips_used": len(timeline.entries),
                "source_videos_used": len(download_result.downloaded),
                "duration_seconds": timeline.total_duration_seconds,
                "created_at": datetime.utcnow().isoformat(),
                "pipeline_duration_seconds": round(time.time() - t0, 1),
            }
            with open(os.path.join(output_dir, "manifest.json"), "w") as f:
                json.dump(manifest, f, indent=2)

            # Mark complete
            output.status = JobStatus.COMPLETED
            output.completed_at = datetime.utcnow()
            self._report("completed", 100)

            logger.info(
                "compilation_pipeline_complete",
                job_id=job_id,
                niche=niche,
                duration=round(time.time() - t0, 1),
                video=final_video,
                clips=len(timeline.entries),
            )

        except Exception as exc:
            output.status = JobStatus.FAILED
            output.error = str(exc)
            logger.error(
                "compilation_pipeline_failed",
                job_id=job_id,
                niche=niche,
                error=str(exc),
            )
            raise

        return output

    # ══════════════════════════════════════════════════════════════════
    #  Private stage implementations
    # ══════════════════════════════════════════════════════════════════

    async def _fetch_strategy(self, niche: str, keywords: list[str] | None = None):
        """Fetch a CompilationStrategy from the Compilation Intelligence engine."""
        from app.compilation_engine.engine import CompilationAnalyzer

        analyzer = CompilationAnalyzer(self._yt_search)
        strategy = await analyzer.analyze(niche, keywords or [niche])
        if not strategy.recommended_segments:
            raise RuntimeError(
                f"Compilation Intelligence returned no recommended segments for '{niche}'"
            )
        return strategy

    async def _download_videos(
        self,
        source_videos: list[dict[str, Any]],
        job_id: str,
        vs: VideoSettings,
    ) -> DownloadStageResult:
        """Download source videos from YouTube."""
        from app.video_factory.youtube_downloader import YouTubeDownloader

        downloader = YouTubeDownloader(
            max_height=vs.max_source_resolution,
            output_base=self.output_base,
        )
        result = await downloader.download_source_videos(source_videos, job_id)

        return DownloadStageResult(
            downloaded=[
                DownloadedVideoInfo(
                    video_id=d.video_id,
                    title=d.title,
                    file_path=d.file_path,
                    duration_seconds=d.duration_seconds,
                    width=d.width,
                    height=d.height,
                    file_size_mb=d.file_size_mb,
                )
                for d in result.downloaded
            ],
            failed=result.failed,
            source_dir=result.source_dir,
            total_size_mb=result.total_size_mb,
        )

    async def _extract_segments(
        self,
        segments: list[dict[str, Any]],
        source_lookup: dict[str, str],
        job_id: str,
        vs: VideoSettings,
        vp_cfg: Any = None,
        hw: Any = None,
    ) -> ExtractionStageResult:
        """Extract clip segments using stream copy + parallel extraction."""
        from app.video_factory.segment_extractor import SegmentExtractor

        # Determine stream copy mode from config
        use_stream_copy = True
        max_parallel = 4
        if vp_cfg is not None:
            use_stream_copy = vp_cfg.enable_stream_copy
            max_parallel = vp_cfg.max_parallel_clip_tasks or (
                hw.max_parallel_clips if hw else 4
            )

        extractor = SegmentExtractor(
            output_base=self.output_base,
            reencode=not use_stream_copy,
            target_resolution=vs.resolution,
            max_parallel=max_parallel,
        )
        result = await extractor.extract_segments(segments, source_lookup, job_id)

        return ExtractionStageResult(
            clips=[
                ExtractedClipInfo(
                    clip_id=c.clip_id,
                    source_video_id=c.source_video_id,
                    file_path=c.clip_file_path,
                    start_seconds=c.start_seconds,
                    end_seconds=c.end_seconds,
                    duration_seconds=c.duration_seconds,
                    segment_type=c.segment_type,
                    energy_level=c.energy_level,
                    position=c.position,
                    width=c.width,
                    height=c.height,
                    file_size_mb=c.file_size_mb,
                    is_valid=c.is_valid,
                )
                for c in result.clips
            ],
            failed=result.failed,
            clips_dir=result.clips_dir,
            total_duration_seconds=result.total_duration_seconds,
            total_size_mb=result.total_size_mb,
        )

    async def _validate_clips(
        self,
        extraction: ExtractionStageResult,
        vs: VideoSettings,
    ) -> list:
        """Validate all extracted clips."""
        from app.video_factory.clip_validator import ClipValidator

        validator = ClipValidator(
            require_audio=vs.include_audio_from_clips,
            target_resolution=vs.resolution,
        )
        clip_data = [
            {"clip_id": c.clip_id, "file_path": c.file_path}
            for c in extraction.clips
        ]
        return await validator.validate_clips(clip_data)

    def _copyright_check(
        self,
        extraction: ExtractionStageResult,
        source_durations: dict[str, float],
        vs: VideoSettings,
    ) -> CopyrightReportInfo:
        """Run copyright safety analysis."""
        from app.video_factory.copyright_guard import CopyrightGuard

        guard = CopyrightGuard(strict=vs.copyright_strict)
        clips_data = [
            {
                "clip_id": c.clip_id,
                "source_video_id": c.source_video_id,
                "duration_seconds": c.duration_seconds,
                "start_seconds": c.start_seconds,
                "end_seconds": c.end_seconds,
            }
            for c in extraction.clips if c.is_valid
        ]
        report = guard.analyze(clips_data, source_durations)

        return CopyrightReportInfo(
            is_safe=report.is_safe,
            issues=[
                CopyrightIssueInfo(
                    severity=i.severity,
                    source_video_id=i.source_video_id,
                    clip_id=i.clip_id,
                    message=i.message,
                    recommendation=i.recommendation,
                )
                for i in report.issues
            ],
            unique_sources=report.unique_sources,
            source_usage=report.source_usage,
        )

    def _build_timeline(
        self,
        valid_clips: list[ExtractedClipInfo],
        vs: VideoSettings,
    ) -> CompilationTimeline:
        """Build the compilation timeline."""
        from app.video_factory.video_assembler import CompilationAssembler

        assembler = CompilationAssembler(settings=vs)
        return assembler.build_timeline(valid_clips)

    async def _assemble_video(
        self,
        timeline: CompilationTimeline,
        output_dir: str,
        vs: VideoSettings,
        hw: Any = None,
        vp_cfg: Any = None,
    ) -> AssemblyResult:
        """Assemble the final video with single-pass encoding."""
        from app.video_factory.video_assembler import CompilationAssembler

        # Determine encoder and presets from hardware + config
        encoder = "libx264"
        cpu_preset = "veryfast"
        gpu_preset = "fast"
        crf = 20

        if vp_cfg is not None:
            cpu_preset = vp_cfg.cpu_preset
            gpu_preset = vp_cfg.gpu_preset
            crf = vp_cfg.crf
            if vp_cfg.enable_gpu_acceleration and hw and hw.recommended_encoder != "libx264":
                encoder = hw.recommended_encoder

        assembler = CompilationAssembler(
            settings=vs,
            encoder=encoder,
            cpu_preset=cpu_preset,
            gpu_preset=gpu_preset,
            crf=crf,
        )
        return await assembler.assemble(timeline, output_dir)

    async def _generate_thumbnail(
        self,
        niche: str,
        title: str,
        output_dir: str,
    ) -> ThumbnailResult:
        """Generate a thumbnail for the compilation video."""
        from app.video_factory.thumbnail_generator import ThumbnailGenerator

        # Create a minimal concept-like object for the existing generator
        from types import SimpleNamespace
        concept = SimpleNamespace(
            title=title,
            concept=f"Compilation video about {niche}",
            target_audience="YouTube viewers",
            engagement_hook=title,
        )
        gen = ThumbnailGenerator()
        return await gen.generate(niche, concept, output_dir)

    async def _generate_metadata(
        self,
        niche: str,
        strategy,
        output_dir: str,
    ) -> VideoMetadata:
        """Generate YouTube metadata from the compilation strategy."""
        fvc = strategy.final_video_concept
        eg = strategy.editing_guidance

        # Build a basic metadata from strategy info
        tags = list(fvc.tags) if fvc.tags else []
        if niche not in tags:
            tags.insert(0, niche)
        tags = tags[:30]  # YouTube limit

        description_parts = [
            fvc.description,
            "",
            f"Niche: {niche}",
            f"Target audience: {fvc.target_audience}",
            "",
            "Source videos used in this compilation are credited to their original creators.",
        ]

        # Add source credits
        for src in strategy.source_videos[:10]:
            if src.title and src.channel_name:
                description_parts.append(f"• {src.title} by {src.channel_name}")

        return VideoMetadata(
            title=fvc.title or f"Best {niche} Compilation",
            description="\n".join(description_parts),
            tags=tags,
            hashtags=[f"#{t.replace(' ', '')}" for t in tags[:5]],
            category="Entertainment",
        )

    @staticmethod
    def _cleanup_temp(output_dir: str) -> None:
        """Remove temporary files (source videos, intermediate clips)."""
        for subdir in ("source_videos", "clips"):
            path = os.path.join(output_dir, subdir)
            if os.path.isdir(path):
                try:
                    shutil.rmtree(path)
                    logger.info("temp_cleaned", dir=subdir)
                except Exception as exc:
                    logger.warning("temp_cleanup_failed", dir=subdir, error=str(exc))

        # Remove concat list and draft
        for fname in ("_concat_list.txt", "draft_video.mp4"):
            fpath = os.path.join(output_dir, fname)
            if os.path.exists(fpath):
                try:
                    os.remove(fpath)
                except Exception:
                    pass
