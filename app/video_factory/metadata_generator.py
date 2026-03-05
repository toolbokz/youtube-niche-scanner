"""Video Factory — Step 9: Metadata Generation.

Generates YouTube publishing assets: title, description, tags,
hashtags, chapters, and SEO keywords.
"""
from __future__ import annotations

import json
from typing import Any

from app.core.logging import get_logger
from app.video_factory.models import (
    VideoConcept,
    VideoScript,
    VideoMetadata,
)
from app.video_factory.prompts import metadata_generation_prompt

logger = get_logger(__name__)


class MetadataGenerator:
    """Generate YouTube publishing metadata."""

    async def generate(
        self,
        niche: str,
        concept: VideoConcept,
        script: VideoScript,
        output_dir: str,
    ) -> VideoMetadata:
        """Generate complete YouTube metadata.

        Parameters
        ----------
        niche : str
            Target niche.
        concept : VideoConcept
            Video concept.
        script : VideoScript
            Video script (for chapter timestamps).
        output_dir : str
            Directory for output files.

        Returns
        -------
        VideoMetadata
            Complete publishing metadata.
        """
        logger.info("metadata_generation_start", niche=niche)

        metadata = await self._generate_ai_metadata(niche, concept, script)

        # Write metadata JSON
        import os
        os.makedirs(output_dir, exist_ok=True)
        metadata_path = os.path.join(output_dir, "metadata.json")

        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata.model_dump(), f, indent=2, ensure_ascii=False)

        logger.info(
            "metadata_generation_done",
            niche=niche,
            tags=len(metadata.tags),
            chapters=len(metadata.chapters),
        )
        return metadata

    async def _generate_ai_metadata(
        self,
        niche: str,
        concept: VideoConcept,
        script: VideoScript,
    ) -> VideoMetadata:
        """Generate metadata using AI."""
        try:
            from app.ai.client import get_ai_client

            client = get_ai_client()
            sections_data = [s.model_dump() for s in script.sections]
            prompt = metadata_generation_prompt(
                niche, concept.title, sections_data, concept.model_dump()
            )
            result = client.generate_json(prompt, use_pro=True, temperature=0.5)

            if result and isinstance(result, dict):
                return VideoMetadata(
                    title=result.get("title", concept.title),
                    description=result.get("description", ""),
                    tags=result.get("tags", []),
                    hashtags=result.get("hashtags", []),
                    chapters=result.get("chapters", []),
                    category=result.get("category", "Education"),
                    language=result.get("language", "en"),
                    seo_keywords=result.get("seo_keywords", []),
                )

        except Exception as exc:
            logger.warning("metadata_ai_failed", error=str(exc))

        # Fallback metadata
        return self._fallback_metadata(niche, concept, script)

    def _fallback_metadata(
        self,
        niche: str,
        concept: VideoConcept,
        script: VideoScript,
    ) -> VideoMetadata:
        """Generate fallback metadata without AI."""
        # Build chapters from script sections
        chapters = []
        current_time = 0
        for section in script.sections:
            minutes = current_time // 60
            seconds = current_time % 60
            chapters.append({
                "time": f"{int(minutes)}:{int(seconds):02d}",
                "title": section.section_title,
            })
            current_time += section.duration_seconds

        # Build description
        chapter_text = "\n".join(
            f"{ch['time']} {ch['title']}" for ch in chapters
        )
        description = (
            f"{concept.engagement_hook}\n\n"
            f"In this video, we explore {niche} and reveal insights "
            f"that can change your perspective completely.\n\n"
            f"📋 Chapters:\n{chapter_text}\n\n"
            f"🔔 Subscribe for more {niche} content!\n"
            f"👍 Like this video if you found it valuable\n"
            f"💬 Comment below with your thoughts\n\n"
            f"#{''.join(niche.title().split())} #YouTube #Insights"
        )

        # Build tags
        words = niche.lower().split()
        tags = [
            niche,
            *words,
            f"{niche} explained",
            f"{niche} tips",
            f"{niche} guide",
            f"best {niche}",
            f"{niche} 2024",
            "tips and tricks",
            "how to",
            "guide",
            "tutorial",
        ]

        hashtags = [
            f"#{''.join(niche.title().split())}",
            "#YouTube",
            "#Tips",
        ]

        return VideoMetadata(
            title=concept.title,
            description=description,
            tags=tags[:25],
            hashtags=hashtags,
            chapters=chapters,
            category="Education",
            language="en",
            seo_keywords=words + [niche],
        )
