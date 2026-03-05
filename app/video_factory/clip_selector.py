"""Video Factory — Step 4: Clip Selection.

Identifies and maps visual content for each script section.
Sources include stock footage search queries, YouTube references,
and existing compilation clips.
"""
from __future__ import annotations

import json
from typing import Any

from app.core.logging import get_logger
from app.video_factory.models import (
    VideoScript,
    VideoConcept,
    ClipSource,
    ClipSelectionResult,
)
from app.video_factory.prompts import clip_selection_prompt

logger = get_logger(__name__)


class ClipSelector:
    """Select visual clips for each script section."""

    async def select(
        self,
        niche: str,
        script: VideoScript,
        concept: VideoConcept,
    ) -> ClipSelectionResult:
        """Select clips for each section of the script.

        Parameters
        ----------
        niche : str
            Target niche.
        script : VideoScript
            The video script to find clips for.
        concept : VideoConcept
            The video concept for context.

        Returns
        -------
        ClipSelectionResult
            Clips mapped to each script section.
        """
        logger.info("clip_selection_start", niche=niche, sections=len(script.sections))

        clips: list[ClipSource] = []

        # Try AI-powered clip suggestion
        try:
            ai_clips = await self._ai_clip_selection(niche, script)
            if ai_clips:
                clips = ai_clips
        except Exception as exc:
            logger.warning("clip_selection_ai_failed", error=str(exc))

        # Fallback: generate clip suggestions from script content
        if not clips:
            clips = self._generate_default_clips(niche, script)

        # Try to find actual YouTube sources for clip suggestions
        enriched_clips = await self._enrich_with_youtube(niche, clips)

        total_duration = sum(c.duration_seconds for c in enriched_clips)
        script_duration = sum(s.duration_seconds for s in script.sections)
        coverage = min(100.0, (total_duration / max(script_duration, 1)) * 100)

        result = ClipSelectionResult(
            clips=enriched_clips,
            total_clips=len(enriched_clips),
            total_duration_seconds=round(total_duration, 2),
            coverage_pct=round(coverage, 1),
        )

        logger.info(
            "clip_selection_done",
            niche=niche,
            clips=result.total_clips,
            coverage=result.coverage_pct,
        )
        return result

    async def _ai_clip_selection(
        self, niche: str, script: VideoScript
    ) -> list[ClipSource]:
        """Use AI to suggest clips for each script section."""
        from app.ai.client import get_ai_client

        client = get_ai_client()
        sections_data = [s.model_dump() for s in script.sections]
        prompt = clip_selection_prompt(niche, sections_data)

        result = client.generate_json(prompt, temperature=0.5)
        if not result or not isinstance(result, list):
            return []

        clips = []
        for item in result:
            if not isinstance(item, dict):
                continue
            clips.append(ClipSource(
                section_index=item.get("section_index", 0),
                section_title=item.get("section_title", ""),
                source_type=item.get("source_type", "stock"),
                source_url="",
                source_video_id="",
                description=item.get("description", ""),
                duration_seconds=item.get("duration_seconds", 10),
                relevance_score=item.get("relevance_score", 0.8),
            ))
        return clips

    def _generate_default_clips(
        self, niche: str, script: VideoScript
    ) -> list[ClipSource]:
        """Generate default clip suggestions based on script sections."""
        clips = []
        for i, section in enumerate(script.sections):
            source_type = "stock"
            description = f"Visual content for: {section.section_title}"

            if section.section_type == "hook":
                description = f"Eye-catching opener related to {niche}"
            elif section.section_type == "intro":
                description = f"Channel branding and {niche} topic intro visuals"
            elif section.section_type == "cta":
                description = "Subscribe animation and end screen elements"
                source_type = "text_overlay"
            elif section.visual_notes:
                description = section.visual_notes

            clips.append(ClipSource(
                section_index=i,
                section_title=section.section_title,
                source_type=source_type,
                description=description,
                duration_seconds=max(section.duration_seconds, 5),
                relevance_score=0.7,
            ))
        return clips

    async def _enrich_with_youtube(
        self, niche: str, clips: list[ClipSource]
    ) -> list[ClipSource]:
        """Try to find actual YouTube videos matching clip descriptions."""
        try:
            from app.connectors.youtube_search import YouTubeSearchConnector
            from app.config import get_settings

            settings = get_settings()
            yt_search = YouTubeSearchConnector(settings.connectors.youtube_search)

            # Search for a few YouTube videos related to the niche
            results = await yt_search.search(niche, max_results=10)

            # Map results to clips that need YouTube sources
            for clip in clips:
                if clip.source_type == "youtube" and not clip.source_video_id:
                    for r in results:
                        if r.video_id and r.duration_seconds > 30:
                            clip.source_video_id = r.video_id
                            clip.source_url = f"https://youtube.com/watch?v={r.video_id}"
                            break

        except Exception as exc:
            logger.debug("youtube_enrichment_skipped", error=str(exc))

        return clips
