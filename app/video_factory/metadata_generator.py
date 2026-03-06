"""Video Factory — Metadata Generation.

Generates YouTube publishing assets: title, description, tags,
hashtags, chapters, and SEO keywords.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from app.core.logging import get_logger
from app.video_factory.models import (
    VideoMetadata,
)

logger = get_logger(__name__)


class MetadataGenerator:
    """Generate YouTube publishing metadata."""

    async def generate(
        self,
        niche: str,
        concept: Any,
        script: Any,
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
        concept: Any,
        script: Any,
    ) -> VideoMetadata:
        """Generate metadata using AI."""
        title = getattr(concept, "title", str(concept))
        try:
            from app.ai.client import get_ai_client

            client = get_ai_client()
            sections_data = [s.model_dump() for s in script.sections] if hasattr(script, "sections") else []
            concept_data = concept.model_dump() if hasattr(concept, "model_dump") else {"title": title}
            prompt = (
                f"Generate YouTube metadata for a video about '{niche}'. "
                f"Title: '{title}'. Sections: {json.dumps(sections_data[:5])}. "
                f"Return JSON with: title, description, tags (list), hashtags (list), "
                f"chapters (list of {{time, title}}), category, language, seo_keywords (list)."
            )
            result = client.generate_json(prompt, use_pro=True, temperature=0.5)

            if result and isinstance(result, dict):
                return VideoMetadata(
                    title=result.get("title", title),
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
        concept: Any,
        script: Any,
    ) -> VideoMetadata:
        """Generate fallback metadata without AI."""
        title = getattr(concept, "title", str(concept))
        engagement_hook = getattr(concept, "engagement_hook", f"Discover the best of {niche}")
        sections = getattr(script, "sections", [])

        # Build chapters from script sections
        chapters = []
        current_time = 0
        for section in sections:
            minutes = current_time // 60
            seconds = current_time % 60
            section_title = getattr(section, "section_title", str(section))
            duration = getattr(section, "duration_seconds", 30)
            chapters.append({
                "time": f"{int(minutes)}:{int(seconds):02d}",
                "title": section_title,
            })
            current_time += duration

        # Build description
        chapter_text = "\n".join(
            f"{ch['time']} {ch['title']}" for ch in chapters
        )
        description = (
            f"{engagement_hook}\n\n"
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
            f"{niche} {datetime.now().year}",
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
            title=title,
            description=description,
            tags=tags[:25],
            hashtags=hashtags,
            chapters=chapters,
            category="Education",
            language="en",
            seo_keywords=words + [niche],
        )
