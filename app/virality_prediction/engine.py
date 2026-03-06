"""Virality Prediction Engine - heuristic-based viral potential scoring."""
from __future__ import annotations

import re

from app.core.logging import get_logger
from app.core.models import ViralityMetrics

logger = get_logger(__name__)


# ── Pattern Dictionaries ───────────────────────────────────────────────────────

CURIOSITY_PATTERNS: list[str] = [
    r"\bhow\b", r"\bwhy\b", r"\bwhat\b", r"\bsecret\b", r"\bhidden\b",
    r"\buntold\b", r"\btruth\b", r"\breveal\b", r"\bdiscover\b",
    r"\bunexpected\b", r"\bunbelievable\b", r"\bmystery\b", r"\bno one knows\b",
    r"\byou won't believe\b", r"\bfinally\b", r"\bexposed\b",
]

EMOTION_TRIGGERS: list[str] = [
    r"\bamazing\b", r"\bshocking\b", r"\bheartbreaking\b", r"\binspiring\b",
    r"\bterrifying\b", r"\bhilarious\b", r"\binsane\b", r"\bmind-?blowing\b",
    r"\bincredible\b", r"\bunreal\b", r"\bepic\b", r"\bbrutal\b",
    r"\bemotional\b", r"\bheartwarming\b", r"\bdevastating\b",
]

SHOCK_PATTERNS: list[str] = [
    r"\bshocking\b", r"\bexposed\b", r"\bscandal\b", r"\bcontrovers\b",
    r"\bdangerous\b", r"\bwent wrong\b", r"\bcaught\b", r"\bfailed\b",
    r"\bdisaster\b", r"\bscam\b", r"\bfraud\b", r"\bbanned\b",
]

NOVELTY_PATTERNS: list[str] = [
    r"\bnew\b", r"\b20(2[4-9]|3[0-9])\b", r"\bfirst\b", r"\bnever\b",
    r"\blatest\b", r"\bbreaking\b", r"\bjust released\b",
    r"\bupdate\b", r"\brecently\b", r"\bemerging\b",
]

INFO_ASYMMETRY_PATTERNS: list[str] = [
    r"\bno one tells\b", r"\bthey don't want\b", r"\bhidden\b",
    r"\binsider\b", r"\bsecret\b", r"\bunderrated\b",
    r"\boverlooked\b", r"\bunknown\b", r"\brare\b",
]

RELATABLE_TOPICS: list[str] = [
    "money", "health", "relationship", "career", "success", "failure",
    "anxiety", "productivity", "sleep", "diet", "fitness", "happiness",
    "technology", "ai", "social media", "education", "travel",
    "cooking", "home", "parenting", "dating", "finance", "investing",
]


class ViralityPredictionEngine:
    """Predict viral potential using heuristic content analysis signals."""

    def analyze_niche(self, niche_name: str, keywords: list[str]) -> ViralityMetrics:
        """Analyze virality potential for a niche."""
        # Combine niche name and keywords for analysis
        text = " ".join([niche_name] + keywords).lower()

        curiosity = self._score_patterns(text, CURIOSITY_PATTERNS)
        emotional = self._score_patterns(text, EMOTION_TRIGGERS)
        shock = self._score_patterns(text, SHOCK_PATTERNS)
        info_asym = self._score_patterns(text, INFO_ASYMMETRY_PATTERNS)
        novelty = self._score_patterns(text, NOVELTY_PATTERNS)
        relatability = self._score_relatability(text)

        # Calculate composite virality probability
        virality = (
            curiosity * 0.25
            + emotional * 0.20
            + shock * 0.10
            + info_asym * 0.15
            + novelty * 0.15
            + relatability * 0.15
        )

        # Apply content type bonus
        virality = self._apply_content_bonus(text, virality)

        metrics = ViralityMetrics(
            niche=niche_name,
            curiosity_gap=round(curiosity, 1),
            emotional_trigger=round(emotional, 1),
            shock_factor=round(shock, 1),
            information_asymmetry=round(info_asym, 1),
            novelty_score=round(novelty, 1),
            relatability=round(relatability, 1),
            virality_probability=round(max(0, min(100, virality)), 1),
        )

        logger.info(
            "virality_analyzed",
            niche=niche_name,
            score=metrics.virality_probability,
        )

        return metrics

    def _score_patterns(self, text: str, patterns: list[str]) -> float:
        """Score text against a list of regex patterns (0-100)."""
        matches = 0
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                matches += 1

        # Calibrated: 50% pattern match = 100 (was 30% which caused saturation)
        ratio = matches / max(1, len(patterns))
        return min(100.0, ratio * 200.0)

    def _score_relatability(self, text: str) -> float:
        """Score how relatable the topic is to broad audiences."""
        matches = sum(1 for topic in RELATABLE_TOPICS if topic in text)
        return min(100.0, matches * 25.0)

    def _apply_content_bonus(self, text: str, base_score: float) -> float:
        """Apply bonus for content types known to go viral."""
        bonus = 0.0

        # List/ranking content
        if re.search(r"\btop\s+\d+\b|\b\d+\s+(best|worst|things)\b", text):
            bonus += 10.0

        # Comparison content
        if re.search(r"\bvs\.?\b|\bversus\b|\bcompare\b", text):
            bonus += 8.0

        # Tutorial/how-to content
        if re.search(r"\bhow to\b|\btutorial\b|\bguide\b|\bstep by step\b", text):
            bonus += 5.0

        # Challenge/experiment content
        if re.search(r"\bchallenge\b|\bexperiment\b|\btried\b|\btesting\b", text):
            bonus += 12.0

        # Story/documentary style
        if re.search(r"\bstory\b|\brise and fall\b|\bhistory\b|\bdocumentary\b", text):
            bonus += 7.0

        return base_score + bonus

    def analyze_batch(
        self, niches: dict[str, list[str]]
    ) -> dict[str, ViralityMetrics]:
        """Analyze virality for multiple niches."""
        results: dict[str, ViralityMetrics] = {}
        for niche_name, keywords in niches.items():
            results[niche_name] = self.analyze_niche(niche_name, keywords)
        return results
