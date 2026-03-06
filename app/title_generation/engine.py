"""Title Generation Engine - curiosity-driven, CTR-optimized titles."""
from __future__ import annotations

import random
from typing import Any

from app.core.logging import get_logger
from app.core.models import VideoIdea

logger = get_logger(__name__)


# ── Title Formula Templates (fallback) ─────────────────────────────────────────

CURIOSITY_GAP_FORMULAS: list[str] = [
    "The {topic} Secret That {audience} Don't Want You to Know",
    "Why {topic} Is NOT What You Think",
    "I Discovered the Truth About {topic} (It Changes Everything)",
    "{topic}: What Nobody Is Telling You",
    "The Hidden Side of {topic} That Will Shock You",
    "They Lied About {topic} — Here's the Proof",
    "What Really Happens When You Try {topic}",
    "The {topic} Trick That Changed My Life",
]

KEYWORD_OPTIMIZED_FORMULAS: list[str] = [
    "{topic}: Complete Guide for Beginners ({year})",
    "{topic} Explained — Everything You Need to Know",
    "How to {topic} Step by Step ({year} Tutorial)",
    "{topic} Tips: {n} Things I Wish I Knew Earlier",
    "Best {topic} Strategies That Actually Work in {year}",
    "{topic} for Beginners: Start Here",
    "{topic} Masterclass — From Zero to Expert",
]

ALTERNATIVE_FORMULAS: list[str] = [
    "I Tried {topic} for 30 Days — Here's What Happened",
    "{n} {topic} Mistakes That Are Costing You",
    "{topic} vs {topic}: Which One Actually Wins?",
    "Stop Doing {topic} Wrong (Do This Instead)",
    "The {n} Rules of {topic} Nobody Teaches You",
    "{topic} in {year}: Everything Has Changed",
    "How I Mastered {topic} (And You Can Too)",
    "Why 99% of People Fail at {topic}",
    "The REAL Reason {topic} Doesn't Work For You",
    "{topic}: Ranked From Worst to Best",
]


class TitleGenerationEngine:
    """Generate CTR-optimized video titles using AI with template fallback."""

    def __init__(self) -> None:
        self.year = "2026"

    def generate_titles(self, video: VideoIdea) -> dict[str, Any]:
        """Generate all title variations for a video idea.

        Tries AI generation first; falls back to template formulas on failure.
        """
        ai_result = self._try_ai_titles(video)
        if ai_result:
            return ai_result

        return self._fallback_titles(video)

    # ── AI-first path ──────────────────────────────────────────────────────

    def _try_ai_titles(self, video: VideoIdea) -> dict[str, Any] | None:
        """Attempt AI-powered title generation."""
        try:
            from app.ai.client import get_ai_client
            from app.ai.prompts.title_generation import title_generation_prompt

            client = get_ai_client()
            if not client.available:
                return None

            prompt = title_generation_prompt(
                niche=video.topic,
                topic=video.topic,
                keywords=video.target_keywords or [],
                angle=video.angle or "",
                trend_momentum=getattr(video, "trend_momentum", 0.0),
                competition_score=getattr(video, "competition_score", 0.0),
                ctr_potential=getattr(video, "ctr_potential", 0.0),
                virality_score=getattr(video, "virality_score", 0.0),
            )
            result = client.generate_json(prompt, use_pro=False)

            if result and isinstance(result, dict):
                curiosity = result.get("curiosity_gap_headline", "")
                keyword_opt = result.get("keyword_optimized_title", "")
                alternatives = result.get("alternative_titles", [])
                formulas = result.get("title_formulas", [])

                if curiosity and keyword_opt:
                    titles = {
                        "curiosity_gap_headline": curiosity,
                        "keyword_optimized_title": keyword_opt,
                        "alternative_titles": alternatives[:5],
                        "title_formulas": formulas if formulas else [
                            f"Curiosity Gap: {curiosity}",
                            f"SEO Optimized: {keyword_opt}",
                        ] + [f"Alternative: {t}" for t in alternatives[:3]],
                        "_ai_generated": True,
                    }
                    logger.info("ai_title_generation_success", topic=video.topic)
                    return titles

        except Exception as exc:
            logger.warning("ai_title_generation_failed", error=str(exc))

        return None

    # ── Template fallback ──────────────────────────────────────────────────

    def _fallback_titles(self, video: VideoIdea) -> dict[str, Any]:
        """Generate titles using static template formulas (fallback)."""
        topic = video.topic.title()

        curiosity_title = self._generate_curiosity_title(topic)
        keyword_title = self._generate_keyword_title(topic, video.target_keywords)
        alternatives = self._generate_alternatives(topic)

        return {
            "curiosity_gap_headline": curiosity_title,
            "keyword_optimized_title": keyword_title,
            "alternative_titles": alternatives,
            "title_formulas": [
                f"Curiosity Gap: {curiosity_title}",
                f"SEO Optimized: {keyword_title}",
            ] + [f"Alternative: {t}" for t in alternatives],
        }

    def _generate_curiosity_title(self, topic: str) -> str:
        """Generate a curiosity-gap headline."""
        template = random.choice(CURIOSITY_GAP_FORMULAS)
        return template.format(
            topic=topic,
            audience="experts",
            year=self.year,
            n=random.choice([5, 7, 10, 15]),
        )

    def _generate_keyword_title(self, topic: str, keywords: list[str]) -> str:
        """Generate a keyword-optimized title."""
        template = random.choice(KEYWORD_OPTIMIZED_FORMULAS)
        return template.format(
            topic=topic,
            year=self.year,
            n=random.choice([5, 7, 10]),
        )

    def _generate_alternatives(self, topic: str, count: int = 5) -> list[str]:
        """Generate alternative high-CTR titles."""
        templates = random.sample(
            ALTERNATIVE_FORMULAS, min(count, len(ALTERNATIVE_FORMULAS))
        )
        titles: list[str] = []
        for template in templates:
            title = template.format(
                topic=topic,
                year=self.year,
                n=random.choice([3, 5, 7, 10]),
            )
            titles.append(title)
        return titles

    def generate_batch(
        self, videos: list[VideoIdea]
    ) -> list[dict[str, Any]]:
        """Generate titles for multiple video ideas."""
        return [self.generate_titles(v) for v in videos]
