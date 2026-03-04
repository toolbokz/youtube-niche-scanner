"""CTR Prediction Engine - estimates click-through rate potential."""
from __future__ import annotations

import re
from typing import Any

from app.core.logging import get_logger
from app.core.models import CTRMetrics

logger = get_logger(__name__)


# ── Power Words ────────────────────────────────────────────────────────────────

POWER_WORDS: list[str] = [
    "secret", "hidden", "shocking", "revealed", "ultimate", "insane",
    "proven", "dangerous", "banned", "illegal", "free", "instant",
    "guaranteed", "exclusive", "urgent", "breaking", "warning",
    "massive", "unbelievable", "truth", "exposed", "life-changing",
    "mind-blowing", "hack", "cheat", "trick", "mistake", "never",
    "always", "worst", "best", "fastest", "easiest", "cheapest",
]

CURIOSITY_TRIGGERS: list[str] = [
    r"you won'?t believe",
    r"no one (talks|knows) about",
    r"(?:they|he|she) didn'?t expect",
    r"what happened (next|when)",
    r"the real reason",
    r"before it'?s too late",
    r"stop doing this",
    r"i was wrong about",
    r"the truth about",
    r"here'?s why",
    r"this is why",
    r"don'?t (make this mistake|do this)",
]

PATTERN_INTERRUPTS: list[str] = [
    r"^\d+\s",  # Starts with number
    r"\b(vs|versus)\b",  # Comparison
    r"\b(day \d+|hour \d+)\b",  # Time stamps
    r"\(\w+\)",  # Parenthetical
    r"[!?]{2,}",  # Multiple punctuation
    r"\.{3}",  # Ellipsis
    r"[A-Z]{3,}",  # ALL CAPS words
]


class CTRPredictionEngine:
    """Predict click-through rate potential from title and niche analysis."""

    def analyze_niche(self, niche_name: str, keywords: list[str]) -> CTRMetrics:
        """Analyze CTR potential for a niche."""
        # Sample title templates for the niche
        sample_titles = self._generate_sample_titles(niche_name, keywords)
        text = " ".join([niche_name] + keywords + sample_titles).lower()

        title_curiosity = self._score_curiosity(text)
        title_length = self._score_title_length(niche_name)
        power_words = self._score_power_words(text)
        numbers_lists = self._score_numbers_lists(text)
        pattern_interrupt = self._score_pattern_interrupts(text)
        visual_concept = self._score_visual_concept(niche_name, keywords)

        # Composite CTR score
        ctr_score = (
            title_curiosity * 0.25
            + title_length * 0.10
            + power_words * 0.20
            + numbers_lists * 0.15
            + pattern_interrupt * 0.15
            + visual_concept * 0.15
        )

        metrics = CTRMetrics(
            niche=niche_name,
            title_curiosity=round(title_curiosity, 1),
            title_length_score=round(title_length, 1),
            power_words_score=round(power_words, 1),
            numbers_lists_score=round(numbers_lists, 1),
            pattern_interrupt_score=round(pattern_interrupt, 1),
            visual_concept_score=round(visual_concept, 1),
            ctr_potential=round(max(0, min(100, ctr_score)), 1),
        )

        logger.info("ctr_analyzed", niche=niche_name, score=metrics.ctr_potential)
        return metrics

    def _generate_sample_titles(self, niche: str, keywords: list[str]) -> list[str]:
        """Generate sample title variations for CTR analysis."""
        templates = [
            f"The Secret {niche} Nobody Tells You About",
            f"Top 10 {niche} That Will Blow Your Mind",
            f"Why {niche} Is Not What You Think",
            f"I Tried {niche} For 30 Days - Here's What Happened",
            f"The REAL Truth About {niche}",
            f"{niche}: What They Don't Want You To Know",
            f"Stop Making These {niche} Mistakes",
            f"How to Master {niche} in 2024",
        ]
        return templates

    def _score_curiosity(self, text: str) -> float:
        """Score curiosity trigger potential."""
        matches = 0
        for pattern in CURIOSITY_TRIGGERS:
            if re.search(pattern, text, re.IGNORECASE):
                matches += 1
        ratio = matches / max(1, len(CURIOSITY_TRIGGERS))
        return min(100.0, ratio * 500.0)

    def _score_title_length(self, title: str) -> float:
        """Score title length optimization (50-60 chars optimal)."""
        length = len(title)
        if 40 <= length <= 70:
            return 90.0
        elif 30 <= length <= 80:
            return 70.0
        elif length < 20:
            return 40.0
        else:
            return 50.0

    def _score_power_words(self, text: str) -> float:
        """Score presence of power words."""
        matches = sum(1 for word in POWER_WORDS if word in text.lower())
        return min(100.0, matches * 12.0)

    def _score_numbers_lists(self, text: str) -> float:
        """Score presence of numbers and list-style content."""
        number_matches = len(re.findall(r"\b\d+\b", text))
        list_patterns = [r"\btop \d+\b", r"\b\d+ (best|worst|ways|tips|things)\b"]
        list_matches = sum(1 for p in list_patterns if re.search(p, text, re.IGNORECASE))

        score = min(60.0, number_matches * 8.0) + min(40.0, list_matches * 20.0)
        return min(100.0, score)

    def _score_pattern_interrupts(self, text: str) -> float:
        """Score pattern interrupt elements."""
        matches = 0
        for pattern in PATTERN_INTERRUPTS:
            if re.search(pattern, text):
                matches += 1
        ratio = matches / max(1, len(PATTERN_INTERRUPTS))
        return min(100.0, ratio * 400.0)

    def _score_visual_concept(self, niche: str, keywords: list[str]) -> float:
        """Score potential for strong thumbnail visual concepts."""
        visual_keywords = [
            "before after", "transformation", "comparison", "reaction",
            "results", "money", "car", "house", "food", "body",
            "face", "nature", "space", "animal", "technology",
        ]
        text = (niche + " " + " ".join(keywords)).lower()
        matches = sum(1 for vk in visual_keywords if vk in text)
        return min(100.0, matches * 20.0)

    def analyze_batch(self, niches: dict[str, list[str]]) -> dict[str, CTRMetrics]:
        """Analyze CTR for multiple niches."""
        results: dict[str, CTRMetrics] = {}
        for niche_name, keywords in niches.items():
            results[niche_name] = self.analyze_niche(niche_name, keywords)
        return results
