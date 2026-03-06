"""Faceless Content Viability Analyzer."""
from __future__ import annotations

from app.core.logging import get_logger
from app.core.models import FacelessFormat, FacelessViability

logger = get_logger(__name__)


# ── Faceless Format Suitability Patterns ───────────────────────────────────────

STOCK_FOOTAGE_NICHES: list[str] = [
    "travel", "nature", "wildlife", "city", "lifestyle", "luxury",
    "motivation", "fitness", "food", "cooking", "architecture",
    "history", "documentary", "ocean", "space", "weather",
]

BROLL_VOICEOVER_NICHES: list[str] = [
    "documentary", "history", "true crime", "mystery", "biography",
    "science", "geography", "culture", "war", "politics", "news",
    "analysis", "commentary", "essay", "story", "explained",
]

ANIMATED_EXPLAINER_NICHES: list[str] = [
    "science", "math", "physics", "biology", "chemistry", "education",
    "philosophy", "psychology", "economics", "finance", "investing",
    "how things work", "engineering", "medicine", "anatomy",
]

SCREEN_RECORDING_NICHES: list[str] = [
    "programming", "coding", "software", "tutorial", "photoshop",
    "excel", "web design", "app", "gaming", "tech review",
    "crypto", "trading", "ai tool", "saas", "no code",
    "automation", "productivity tool", "browser",
]

SLIDESHOW_NICHES: list[str] = [
    "facts", "list", "top 10", "top 5", "comparison", "ranking",
    "quiz", "trivia", "data", "statistics", "infographic",
    "tier list", "worst", "best", "rated",
]

DATA_VIZ_NICHES: list[str] = [
    "statistics", "data", "chart", "graph", "comparison",
    "ranking", "population", "economy", "growth", "decline",
    "timeline", "map", "visualization", "analytics", "trends",
]


class FacelessViabilityEngine:
    """Determine if niche content can be produced without appearing on camera."""

    def analyze_niche(self, niche_name: str, keywords: list[str]) -> FacelessViability:
        """Analyze faceless viability for a niche."""
        text = (niche_name + " " + " ".join(keywords)).lower()

        stock_score = self._match_score(text, STOCK_FOOTAGE_NICHES)
        broll_score = self._match_score(text, BROLL_VOICEOVER_NICHES)
        animated_score = self._match_score(text, ANIMATED_EXPLAINER_NICHES)
        screen_score = self._match_score(text, SCREEN_RECORDING_NICHES)
        slideshow_score = self._match_score(text, SLIDESHOW_NICHES)
        data_viz_score = self._match_score(text, DATA_VIZ_NICHES)

        # Find best formats
        format_scores = {
            FacelessFormat.STOCK_FOOTAGE: stock_score,
            FacelessFormat.BROLL_VOICEOVER: broll_score,
            FacelessFormat.ANIMATED_EXPLAINER: animated_score,
            FacelessFormat.SCREEN_RECORDING: screen_score,
            FacelessFormat.SLIDESHOW: slideshow_score,
            FacelessFormat.DATA_VISUALIZATION: data_viz_score,
        }

        best_formats = sorted(
            format_scores.keys(),
            key=lambda f: format_scores[f],
            reverse=True,
        )[:3]

        # Overall faceless viability
        top_scores = sorted(format_scores.values(), reverse=True)
        # Weighted: best format 50%, second 30%, third 20%
        if len(top_scores) >= 3:
            overall = top_scores[0] * 0.50 + top_scores[1] * 0.30 + top_scores[2] * 0.20
        elif len(top_scores) >= 2:
            overall = top_scores[0] * 0.60 + top_scores[1] * 0.40
        else:
            overall = top_scores[0] if top_scores else 0.0

        # Apply baseline bonus — most YouTube content CAN be faceless
        overall = max(overall, 30.0)

        # Penalty for topics that strongly require on-camera presence
        if self._requires_camera(text):
            overall *= 0.5

        result = FacelessViability(
            niche=niche_name,
            stock_footage_score=round(stock_score, 1),
            broll_voiceover_score=round(broll_score, 1),
            animated_explainer_score=round(animated_score, 1),
            screen_recording_score=round(screen_score, 1),
            slideshow_score=round(slideshow_score, 1),
            data_visualization_score=round(data_viz_score, 1),
            best_formats=best_formats,
            faceless_viability_score=round(max(0, min(100, overall)), 1),
        )

        logger.info(
            "faceless_analyzed",
            niche=niche_name,
            score=result.faceless_viability_score,
            formats=[f.value for f in best_formats],
        )

        return result

    def _match_score(self, text: str, patterns: list[str]) -> float:
        """Score how well text matches a list of niche patterns."""
        matches = sum(1 for p in patterns if p in text)
        # Hitting 3+ patterns = strong match
        return min(100.0, matches * 30.0)

    def _requires_camera(self, text: str) -> bool:
        """Detect topics that strongly benefit from on-camera presence."""
        camera_required = [
            "vlog", "day in my life", "get ready with me", "routine",
            "try on", "haul", "unboxing", "makeup tutorial",
            "hair tutorial", "skincare", "asmr eating",
            "mukbang", "prank", "street interview",
        ]
        return any(topic in text for topic in camera_required)

    def analyze_batch(
        self, niches: dict[str, list[str]]
    ) -> dict[str, FacelessViability]:
        """Analyze faceless viability for multiple niches."""
        results: dict[str, FacelessViability] = {}
        for niche_name, keywords in niches.items():
            results[niche_name] = self.analyze_niche(niche_name, keywords)
        return results
