"""Title Generation Engine - curiosity-driven, CTR-optimized titles."""
from __future__ import annotations

import random
from typing import Any

from app.core.logging import get_logger
from app.core.models import VideoIdea

logger = get_logger(__name__)


# ── Title Formula Templates ────────────────────────────────────────────────────

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
    """Generate CTR-optimized video titles using proven formulas."""

    def __init__(self) -> None:
        self.year = "2026"

    def generate_titles(self, video: VideoIdea) -> dict[str, Any]:
        """Generate all title variations for a video idea."""
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
