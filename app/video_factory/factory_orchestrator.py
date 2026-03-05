"""Video Factory — Factory Orchestrator.

Orchestrates the complete video production pipeline end-to-end:
concept → script → voiceover → clips → timeline → assembly →
subtitles → thumbnail → metadata → final render.
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

from app.core.logging import get_logger
from app.video_factory.models import (
    JobStatus,
    VideoConcept,
    VideoScript,
    VoiceConfig,
    VoiceoverResult,
    ClipSelectionResult,
    VideoTimeline,
    AssemblyConfig,
    AssemblyResult,
    SubtitleResult,
    ThumbnailResult,
    VideoMetadata,
    VideoFactoryOutput,
    FactoryJob,
)

logger = get_logger(__name__)

# Default output base directory
_OUTPUT_BASE = "data/video_factory"


class FactoryOrchestrator:
    """Orchestrates the complete video factory pipeline.

    Usage::

        orchestrator = FactoryOrchestrator()
        output = await orchestrator.run("passive income")
    """

    def __init__(
        self,
        output_base: str = _OUTPUT_BASE,
        voice_config: VoiceConfig | None = None,
        assembly_config: AssemblyConfig | None = None,
    ) -> None:
        self.output_base = output_base
        self.voice_config = voice_config or VoiceConfig()
        self.assembly_config = assembly_config or AssemblyConfig()
        self._progress_callback: Callable[[str, float], None] | None = None

    def set_progress_callback(self, callback: Callable[[str, float], None]) -> None:
        """Set a callback for progress updates: callback(stage_name, pct)."""
        self._progress_callback = callback

    def _report_progress(self, stage: str, pct: float) -> None:
        if self._progress_callback:
            self._progress_callback(stage, pct)

    async def run(
        self,
        niche: str,
        job_id: str | None = None,
        voice_config: VoiceConfig | None = None,
        assembly_config: AssemblyConfig | None = None,
    ) -> VideoFactoryOutput:
        """Run the complete video factory pipeline.

        Parameters
        ----------
        niche : str
            The YouTube niche to produce a video for.
        job_id : str, optional
            A pre-assigned job ID. One will be generated if not provided.
        voice_config : VoiceConfig, optional
            Override voiceover settings.
        assembly_config : AssemblyConfig, optional
            Override video assembly settings.

        Returns
        -------
        VideoFactoryOutput
            Complete output with paths to all generated assets.
        """
        job_id = job_id or uuid.uuid4().hex[:12]
        output_dir = os.path.join(self.output_base, job_id)
        os.makedirs(output_dir, exist_ok=True)

        vc = voice_config or self.voice_config
        ac = assembly_config or self.assembly_config

        output = VideoFactoryOutput(
            job_id=job_id,
            niche=niche,
            output_dir=output_dir,
            status=JobStatus.QUEUED,
        )

        t0 = time.time()
        logger.info("factory_pipeline_start", job_id=job_id, niche=niche)

        try:
            # ── Step 1: Concept Generation ────────────────────────────
            self._report_progress("generating_concept", 5)
            output.status = JobStatus.GENERATING_CONCEPT
            from app.video_factory.concept_engine import ConceptEngine

            concept_engine = ConceptEngine()
            concept = await concept_engine.generate(niche)
            output.concept = concept
            logger.info("factory_step_done", step="concept", elapsed=round(time.time() - t0, 1))

            # ── Step 2: Script Generation ─────────────────────────────
            self._report_progress("generating_script", 15)
            output.status = JobStatus.GENERATING_SCRIPT
            from app.video_factory.script_generator import ScriptGenerator

            script_gen = ScriptGenerator()
            script = await script_gen.generate(niche, concept)
            output.script = script
            logger.info("factory_step_done", step="script", elapsed=round(time.time() - t0, 1))

            # ── Step 3: Voiceover Generation ──────────────────────────
            self._report_progress("generating_voiceover", 30)
            output.status = JobStatus.GENERATING_VOICEOVER
            from app.video_factory.voice_generator import VoiceGenerator

            voice_gen = VoiceGenerator(config=vc)
            voiceover = await voice_gen.generate(script, output_dir)
            output.voiceover = voiceover
            logger.info("factory_step_done", step="voiceover", elapsed=round(time.time() - t0, 1))

            # ── Step 4: Clip Selection ────────────────────────────────
            self._report_progress("selecting_clips", 40)
            output.status = JobStatus.SELECTING_CLIPS
            from app.video_factory.clip_selector import ClipSelector

            clip_sel = ClipSelector()
            clip_result = await clip_sel.select(niche, script, concept)
            output.clip_selection = clip_result
            logger.info("factory_step_done", step="clips", elapsed=round(time.time() - t0, 1))

            # ── Step 5: Timeline Generation ───────────────────────────
            self._report_progress("assembling_video", 50)
            output.status = JobStatus.ASSEMBLING_VIDEO
            from app.video_factory.video_assembler import VideoAssembler

            assembler = VideoAssembler(config=ac)
            timeline = assembler.build_timeline(script, clip_result, voiceover)
            output.timeline = timeline

            # ── Step 6: Video Assembly ────────────────────────────────
            self._report_progress("assembling_video", 60)
            assembly = await assembler.assemble(timeline, voiceover, output_dir)
            output.assembly = assembly
            logger.info("factory_step_done", step="assembly", elapsed=round(time.time() - t0, 1))

            # ── Step 7: Subtitle Generation ───────────────────────────
            self._report_progress("generating_subtitles", 70)
            output.status = JobStatus.GENERATING_SUBTITLES
            from app.video_factory.subtitle_generator import SubtitleGenerator

            sub_gen = SubtitleGenerator()
            subtitles = await sub_gen.generate(
                script, voiceover, output_dir,
                embed_in_video=ac.embed_subtitles,
                video_path=assembly.draft_video_path,
            )
            output.subtitles = subtitles
            output.subtitles_path = subtitles.srt_path
            logger.info("factory_step_done", step="subtitles", elapsed=round(time.time() - t0, 1))

            # ── Step 8: Thumbnail Generation ──────────────────────────
            self._report_progress("generating_thumbnail", 80)
            output.status = JobStatus.GENERATING_THUMBNAIL
            from app.video_factory.thumbnail_generator import ThumbnailGenerator

            thumb_gen = ThumbnailGenerator()
            thumbnail = await thumb_gen.generate(niche, concept, output_dir)
            output.thumbnail = thumbnail
            output.thumbnail_path = thumbnail.thumbnail_path
            logger.info("factory_step_done", step="thumbnail", elapsed=round(time.time() - t0, 1))

            # ── Step 9: Metadata Generation ───────────────────────────
            self._report_progress("generating_metadata", 90)
            output.status = JobStatus.GENERATING_METADATA
            from app.video_factory.metadata_generator import MetadataGenerator

            meta_gen = MetadataGenerator()
            metadata = await meta_gen.generate(niche, concept, script, output_dir)
            output.metadata = metadata
            output.metadata_path = os.path.join(output_dir, "metadata.json")
            logger.info("factory_step_done", step="metadata", elapsed=round(time.time() - t0, 1))

            # ── Step 10: Final Render ─────────────────────────────────
            self._report_progress("rendering", 95)
            output.status = JobStatus.RENDERING

            # Rename draft to final video
            final_video = os.path.join(output_dir, "video.mp4")
            if os.path.exists(assembly.draft_video_path) and assembly.draft_video_path != final_video:
                shutil.copy2(assembly.draft_video_path, final_video)
            output.video_path = final_video

            # Write output manifest
            manifest = {
                "job_id": job_id,
                "niche": niche,
                "title": concept.title,
                "files": {
                    "video": "video.mp4",
                    "thumbnail": "thumbnail.png",
                    "subtitles": "subtitles.srt",
                    "metadata": "metadata.json",
                    "voiceover": "voiceover.wav",
                },
                "duration_seconds": timeline.total_duration_seconds,
                "created_at": datetime.utcnow().isoformat(),
                "pipeline_duration_seconds": round(time.time() - t0, 1),
            }
            with open(os.path.join(output_dir, "manifest.json"), "w") as f:
                json.dump(manifest, f, indent=2)

            # Mark complete
            output.status = JobStatus.COMPLETED
            output.completed_at = datetime.utcnow()
            self._report_progress("completed", 100)

            logger.info(
                "factory_pipeline_complete",
                job_id=job_id,
                niche=niche,
                duration=round(time.time() - t0, 1),
                video=final_video,
            )

        except Exception as exc:
            output.status = JobStatus.FAILED
            output.error = str(exc)
            logger.error(
                "factory_pipeline_failed",
                job_id=job_id,
                niche=niche,
                error=str(exc),
            )
            raise

        return output
