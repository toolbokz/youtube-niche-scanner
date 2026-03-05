"""Video Factory — Step 1: Video Concept Generation.

Uses AI to generate a compelling video concept from a selected niche.
"""
from __future__ import annotations

import json
from typing import Any

from app.core.logging import get_logger
from app.video_factory.models import VideoConcept
from app.video_factory.prompts import concept_generation_prompt

logger = get_logger(__name__)


class ConceptEngine:
    """Generate video concepts from a niche using AI."""

    async def generate(self, niche: str) -> VideoConcept:
        """Generate a video concept for the given niche.

        Parameters
        ----------
        niche : str
            The YouTube niche to generate a concept for.

        Returns
        -------
        VideoConcept
            The generated video concept with title, hook, structure, etc.
        """
        logger.info("concept_generation_start", niche=niche)

        try:
            from app.ai.client import get_ai_client

            client = get_ai_client()
            prompt = concept_generation_prompt(niche)
            result = client.generate_json(prompt, use_pro=True, temperature=0.7)

            if result and isinstance(result, dict):
                concept = VideoConcept(
                    title=result.get("title", f"The Truth About {niche}"),
                    concept=result.get("concept", ""),
                    target_audience=result.get("target_audience", ""),
                    engagement_hook=result.get("engagement_hook", ""),
                    emotional_trigger=result.get("emotional_trigger", "curiosity"),
                    video_structure=result.get("video_structure", []),
                    estimated_duration_minutes=result.get("estimated_duration_minutes", 8),
                    niche=niche,
                )
                logger.info("concept_generation_done", niche=niche, title=concept.title)
                return concept

        except Exception as exc:
            logger.warning("concept_generation_ai_failed", niche=niche, error=str(exc))

        # Fallback: generate a sensible default concept
        return self._fallback_concept(niche)

    def _fallback_concept(self, niche: str) -> VideoConcept:
        """Generate a fallback concept when AI is unavailable."""
        title = f"What Nobody Tells You About {niche.title()}"
        return VideoConcept(
            title=title,
            concept=(
                f"An in-depth exploration of {niche} that reveals surprising insights "
                f"and practical strategies most people overlook."
            ),
            target_audience=f"People interested in {niche} looking for actionable insights",
            engagement_hook=f"Did you know that 90% of people get {niche} completely wrong?",
            emotional_trigger="curiosity",
            video_structure=[
                "Hook — shocking statistic",
                "Introduction — promise of insider knowledge",
                "Section 1 — common misconceptions",
                "Section 2 — the hidden truth",
                "Section 3 — actionable strategies",
                "Section 4 — real examples",
                "Conclusion — key takeaway",
                "Call to Action",
            ],
            estimated_duration_minutes=8,
            niche=niche,
        )
