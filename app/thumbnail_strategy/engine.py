"""Thumbnail Strategy Generator."""
from __future__ import annotations

from typing import Any

from app.core.logging import get_logger
from app.core.models import ThumbnailConcept, VideoIdea

logger = get_logger(__name__)


# ── Emotion → Visual Mapping ──────────────────────────────────────────────────

EMOTION_VISUALS: dict[str, dict[str, Any]] = {
    "curiosity": {
        "focal_point": "Mysterious object or partially revealed information",
        "contrast": "Dark background with bright highlight on the mystery element",
        "colors": ["#1a1a2e", "#e94560", "#ffffff"],
        "text_style": "Bold question or ellipsis (... )",
    },
    "shock": {
        "focal_point": "Dramatic facial expression or impactful number",
        "contrast": "High contrast red/yellow with dark elements",
        "colors": ["#ff0000", "#ffd700", "#000000"],
        "text_style": "ALL CAPS with exclamation marks",
    },
    "urgency": {
        "focal_point": "Countdown timer or 'breaking' badge",
        "contrast": "Red/orange gradient with white text",
        "colors": ["#ff4500", "#ff8c00", "#ffffff"],
        "text_style": "Time-sensitive language with bold font",
    },
    "inspiration": {
        "focal_point": "Upward trajectory, success imagery, or transformation",
        "contrast": "Warm golden tones against clean background",
        "colors": ["#ffd700", "#228b22", "#ffffff"],
        "text_style": "Clean, aspirational text with subtle glow",
    },
    "fear": {
        "focal_point": "Warning symbol or danger indicator",
        "contrast": "Dark tones with red warning accents",
        "colors": ["#8b0000", "#2d2d2d", "#ff6347"],
        "text_style": "Warning/danger text with border emphasis",
    },
    "humor": {
        "focal_point": "Exaggerated or absurd visual element",
        "contrast": "Bright, saturated pop colors",
        "colors": ["#ff69b4", "#00ff7f", "#ffff00"],
        "text_style": "Playful font with comic-style emphasis",
    },
}


class ThumbnailStrategyGenerator:
    """Generate optimized thumbnail concepts for video ideas."""

    def generate(self, video: VideoIdea, niche: str) -> ThumbnailConcept:
        """Generate a thumbnail concept for a video idea."""
        emotion = self._detect_primary_emotion(video.title, video.angle)
        visuals = EMOTION_VISUALS.get(emotion, EMOTION_VISUALS["curiosity"])

        # Text overlay
        text_overlay = self._generate_text_overlay(video.title)

        # Layout concept
        layout = self._generate_layout(emotion, niche)

        concept = ThumbnailConcept(
            emotion_trigger=emotion,
            contrast_strategy=visuals["contrast"],
            visual_focal_point=visuals["focal_point"],
            text_overlay=text_overlay,
            color_palette=visuals["colors"],
            layout_concept=layout,
        )

        return concept

    def _detect_primary_emotion(self, title: str, angle: str) -> str:
        """Detect the primary emotion that should drive the thumbnail."""
        text = (title + " " + angle).lower()

        emotion_keywords = {
            "shock": ["shocking", "exposed", "truth", "never", "insane", "unbelievable"],
            "curiosity": ["secret", "hidden", "why", "how", "mystery", "nobody"],
            "urgency": ["breaking", "urgent", "now", "before", "stop", "warning"],
            "inspiration": ["success", "master", "transform", "achieve", "growth"],
            "fear": ["mistake", "danger", "avoid", "worst", "risk", "scam"],
            "humor": ["funny", "hilarious", "tried", "challenge", "weird"],
        }

        scores: dict[str, int] = {}
        for emotion, keywords in emotion_keywords.items():
            scores[emotion] = sum(1 for kw in keywords if kw in text)

        if not any(scores.values()):
            return "curiosity"

        return max(scores, key=lambda k: scores[k])

    def _generate_text_overlay(self, title: str) -> str:
        """Generate thumbnail text overlay — shorter and punchier than the title."""
        words = title.split()
        if len(words) <= 4:
            return title.upper()

        # Extract the most impactful 2-4 words
        power_words = {"secret", "truth", "hidden", "never", "insane", "shocking",
                       "top", "best", "worst", "free", "money", "hack", "master"}

        important = [w for w in words if w.lower().strip(",.!?:") in power_words]
        if len(important) >= 2:
            return " ".join(important[:3]).upper()

        # Use first 3-4 impactful words
        return " ".join(words[:4]).upper() + "..."

    def _generate_layout(self, emotion: str, niche: str) -> str:
        """Describe the thumbnail layout concept."""
        layouts = {
            "curiosity": (
                "Split design: Left 60% shows the intriguing visual element "
                "with partial reveal. Right 40% has bold text overlay with "
                "question mark or arrow pointing to the mystery."
            ),
            "shock": (
                "Full-bleed dramatic image with bold red/yellow text overlay. "
                "Top-right corner badge with '!!!' or 'EXPOSED'. "
                "Face/reaction element in bottom-left corner."
            ),
            "urgency": (
                "Red-tinted overlay on main image. Timer/countdown element "
                "in corner. 'BREAKING' or 'URGENT' banner at top. "
                "White text with red outline for maximum readability."
            ),
            "inspiration": (
                "Clean, bright layout with before/after split or upward "
                "arrow/trajectory. Warm color gradient background. "
                "Aspirational text in modern, clean font."
            ),
            "fear": (
                "Dark, moody background with warning elements. Red accent "
                "lines or borders. 'WARNING' or 'DON'T' text prominent. "
                "Crossed-out or danger symbol."
            ),
            "humor": (
                "Bright, saturated colors with exaggerated visual element. "
                "Comic-style text bubbles or arrows. Playful font choice. "
                "Unexpected juxtaposition of elements."
            ),
        }
        return layouts.get(emotion, layouts["curiosity"])

    def generate_batch(
        self, videos: list[VideoIdea], niche: str
    ) -> list[ThumbnailConcept]:
        """Generate thumbnails for multiple videos."""
        return [self.generate(v, niche) for v in videos]
