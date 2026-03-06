"""Video Strategy Engine - generates channel concepts and video ideas."""
from __future__ import annotations

import random

from app.core.logging import get_logger
from app.core.models import (
    AudiencePersona,
    ChannelConcept,
    FacelessFormat,
    FacelessViability,
    NicheScore,
    VideoIdea,
)

logger = get_logger(__name__)


# ── RPM Estimates by Category ──────────────────────────────────────────────────

RPM_ESTIMATES: dict[str, tuple[float, float]] = {
    "finance": (12.0, 30.0),
    "investing": (15.0, 35.0),
    "insurance": (20.0, 50.0),
    "real estate": (10.0, 25.0),
    "technology": (5.0, 15.0),
    "software": (8.0, 20.0),
    "ai": (6.0, 18.0),
    "health": (8.0, 20.0),
    "fitness": (4.0, 12.0),
    "education": (3.0, 10.0),
    "gaming": (2.0, 6.0),
    "entertainment": (2.0, 8.0),
    "travel": (3.0, 10.0),
    "cooking": (3.0, 8.0),
    "science": (4.0, 12.0),
    "history": (3.0, 10.0),
    "psychology": (5.0, 15.0),
    "business": (10.0, 25.0),
    "marketing": (8.0, 20.0),
    "crypto": (8.0, 25.0),
    "productivity": (5.0, 15.0),
}

# ── Video Angle Templates ─────────────────────────────────────────────────────

ANGLE_TEMPLATES: list[str] = [
    "Beginner's guide / introduction",
    "Deep dive / comprehensive analysis",
    "Comparison / X vs Y",
    "Top 10 / ranking list",
    "Common mistakes to avoid",
    "Hidden secrets / lesser-known facts",
    "Future predictions / trends",
    "Case study / real-world example",
    "Step-by-step tutorial",
    "Myth-busting / debunking",
    "History / origin story",
    "Expert tips / advanced strategies",
    "Challenge / experiment",
    "News / update breakdown",
    "Review / honest opinion",
]


class VideoStrategyEngine:
    """Generate complete video strategies for top niches."""

    def generate_channel_concept(
        self, niche: NicheScore, faceless: FacelessViability | None = None
    ) -> ChannelConcept:
        """Generate a full channel concept for a niche."""
        niche_name = niche.niche
        keywords = niche.keywords

        # Channel name ideas
        channel_names = self._generate_channel_names(niche_name)

        # Audience persona
        audience = self._build_audience_persona(niche_name, keywords)

        # Content positioning
        positioning = self._generate_positioning(niche_name, faceless)

        # Posting cadence based on production complexity
        cadence = self._suggest_cadence(niche_name, faceless)

        # RPM estimate
        rpm_low, rpm_high = self._estimate_rpm(niche_name, keywords)

        # Time to monetization
        months = self._estimate_monetization_time(niche)

        concept = ChannelConcept(
            niche=niche_name,
            channel_name_ideas=channel_names,
            positioning=positioning,
            audience=audience,
            posting_cadence=cadence,
            estimated_rpm=round((rpm_low + rpm_high) / 2, 2),
            time_to_monetization_months=months,
        )

        logger.info("channel_concept_generated", niche=niche_name)
        return concept

    def generate_video_ideas(
        self, niche: NicheScore, count: int = 10
    ) -> list[VideoIdea]:
        """Generate video ideas for a niche."""
        ideas: list[VideoIdea] = []
        niche_name = niche.niche
        keywords = niche.keywords[:10]

        # Use angle templates
        angles = random.sample(ANGLE_TEMPLATES, min(count, len(ANGLE_TEMPLATES)))

        for i, angle in enumerate(angles):
            keyword = keywords[i % len(keywords)] if keywords else niche_name
            title = self._create_title(niche_name, keyword, angle)

            ideas.append(VideoIdea(
                title=title,
                topic=keyword,
                angle=angle,
                target_keywords=keywords[:5],
                estimated_views=self._estimate_views(niche),
                difficulty=self._estimate_difficulty(angle),
            ))

        # Fill remaining slots with keyword-driven ideas
        while len(ideas) < count and keywords:
            kw = keywords[len(ideas) % len(keywords)]
            angle = random.choice(ANGLE_TEMPLATES)
            title = self._create_title(niche_name, kw, angle)
            ideas.append(VideoIdea(
                title=title,
                topic=kw,
                angle=angle,
                target_keywords=keywords[:5],
                estimated_views=self._estimate_views(niche),
                difficulty=self._estimate_difficulty(angle),
            ))

        logger.info("video_ideas_generated", niche=niche_name, count=len(ideas))
        return ideas[:count]

    def _generate_channel_names(self, niche: str) -> list[str]:
        """Generate channel name suggestions."""
        words = niche.split()
        core = words[0].capitalize() if words else "Channel"
        return [
            f"{core} Explained",
            f"The {core} Lab",
            f"{core} Daily",
            f"{core} Insider",
            f"Simply {core}",
        ]

    def _build_audience_persona(self, niche: str, keywords: list[str]) -> AudiencePersona:
        """Build an audience persona for the niche."""
        return AudiencePersona(
            age_range="18-45",
            interests=[niche] + keywords[:5],
            pain_points=[
                f"Lack of clear information about {niche}",
                f"Overwhelmed by options in {niche}",
                f"Want to learn {niche} quickly",
            ],
            content_preferences=[
                "Visual explanations",
                "Data-driven content",
                "Concise and actionable tips",
                "Real-world examples",
            ],
        )

    def _generate_positioning(
        self, niche: str, faceless: FacelessViability | None
    ) -> str:
        """Generate content positioning statement."""
        format_str = ""
        if faceless and faceless.best_formats:
            fmt = faceless.best_formats[0].value.replace("_", " ")
            format_str = f" using {fmt} format"

        return (
            f"The go-to channel for {niche} insights{format_str}. "
            f"Delivering clear, data-driven content that cuts through the noise "
            f"and provides actionable value."
        )

    def _suggest_cadence(
        self, niche: str, faceless: FacelessViability | None
    ) -> str:
        """Suggest posting frequency."""
        if faceless and faceless.best_formats:
            fmt = faceless.best_formats[0]
            if fmt in (FacelessFormat.SLIDESHOW, FacelessFormat.DATA_VISUALIZATION):
                return "3-5 videos per week (low production effort)"
            elif fmt == FacelessFormat.SCREEN_RECORDING:
                return "2-4 videos per week (moderate production effort)"
            elif fmt == FacelessFormat.ANIMATED_EXPLAINER:
                return "1-2 videos per week (higher production effort)"

        return "2-3 videos per week"

    def _estimate_rpm(self, niche: str, keywords: list[str]) -> tuple[float, float]:
        """Estimate RPM range based on niche category."""
        text = (niche + " " + " ".join(keywords)).lower()
        for category, (low, high) in RPM_ESTIMATES.items():
            if category in text:
                return (low, high)
        return (3.0, 10.0)  # Default

    def _estimate_monetization_time(self, niche: NicheScore) -> int:
        """Estimate months to YouTube Partner Program eligibility."""
        # Lower competition + higher trend = faster growth
        growth_factor = (100 - niche.competition_score) * 0.5 + niche.trend_momentum * 0.5
        if growth_factor > 70:
            return 3
        elif growth_factor > 50:
            return 6
        elif growth_factor > 30:
            return 9
        return 12

    def _create_title(self, niche: str, keyword: str, angle: str) -> str:
        """Create a video title based on niche, keyword, and angle."""
        templates = {
            "beginner": f"{keyword.title()}: Complete Beginner's Guide",
            "deep dive": f"The Truth About {keyword.title()} Nobody Tells You",
            "comparison": f"{keyword.title()} - What's Actually Worth It?",
            "top 10": f"Top 10 {keyword.title()} That Will Change Everything",
            "mistakes": f"Stop Making These {keyword.title()} Mistakes",
            "hidden": f"{keyword.title()}: Hidden Secrets Exposed",
            "future": f"The Future of {keyword.title()} Will Shock You",
            "case study": f"How {keyword.title()} Actually Works (Real Data)",
            "step-by-step": f"Master {keyword.title()} in Just 30 Minutes",
            "myth": f"{keyword.title()} Myths Most People Still Believe",
            "history": f"The Untold Story of {keyword.title()}",
            "expert": f"Expert {keyword.title()} Strategies Nobody Shares",
            "challenge": f"I Tried {keyword.title()} for 30 Days - Results",
            "news": f"{keyword.title()} Just Changed Forever",
            "review": f"Honest {keyword.title()} Review After 1 Year",
        }

        angle_lower = angle.lower()
        for key, template in templates.items():
            if key in angle_lower:
                return template

        return f"{keyword.title()}: Everything You Need to Know"

    def _estimate_views(self, niche: NicheScore) -> str:
        """Estimate view range based on niche metrics."""
        base = niche.demand_score * 100
        if niche.overall_score > 70:
            return f"{int(base * 10):,}-{int(base * 50):,}"
        elif niche.overall_score > 50:
            return f"{int(base * 5):,}-{int(base * 20):,}"
        return f"{int(base * 2):,}-{int(base * 10):,}"

    @staticmethod
    def _estimate_difficulty(angle: str) -> str:
        """Estimate production difficulty of a video angle."""
        easy = ["top 10", "ranking", "list", "facts", "comparison"]
        hard = ["deep dive", "case study", "tutorial", "step-by-step"]
        if any(e in angle.lower() for e in easy):
            return "easy"
        if any(h in angle.lower() for h in hard):
            return "hard"
        return "medium"
