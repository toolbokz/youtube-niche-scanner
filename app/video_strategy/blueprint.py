"""Video Blueprint Assembler - combines all generators into complete blueprints."""
from __future__ import annotations

from typing import Any

from app.core.logging import get_logger
from app.core.models import (
    LowCostProduction,
    MonetizationStrategy,
    NicheScore,
    ProductionPlan,
    ScriptStructure,
    SEODescription,
    ThumbnailConcept,
    VideoBlueprint,
    VideoIdea,
)
from app.description_generation.engine import DescriptionGenerationEngine
from app.monetization_engine.engine import MonetizationEngine
from app.thumbnail_strategy.engine import ThumbnailStrategyGenerator
from app.title_generation.engine import TitleGenerationEngine

logger = get_logger(__name__)


class BlueprintAssembler:
    """Assemble complete video blueprints by orchestrating all generators."""

    def __init__(self) -> None:
        self.title_gen = TitleGenerationEngine()
        self.thumbnail_gen = ThumbnailStrategyGenerator()
        self.description_gen = DescriptionGenerationEngine()
        self.monetization_gen = MonetizationEngine()

    def assemble_blueprint(
        self, video: VideoIdea, niche: NicheScore
    ) -> VideoBlueprint:
        """Assemble a complete video blueprint."""
        niche_name = niche.niche

        # Title generation
        titles = self.title_gen.generate_titles(video)

        # Thumbnail
        thumbnail = self.thumbnail_gen.generate(video, niche_name)

        # Script structure
        script = self._generate_script_structure(video, niche_name)

        # Production plan
        production = self._generate_production_plan(video, niche_name)

        # Low-cost production method
        low_cost = self._generate_low_cost_plan(niche_name)

        # SEO description
        description = self.description_gen.generate(video, niche_name)

        # Monetization
        monetization = self.monetization_gen.generate_strategy(niche)

        blueprint = VideoBlueprint(
            video_idea=video,
            title_formulas=titles.get("title_formulas", []),
            curiosity_gap_headline=titles.get("curiosity_gap_headline", ""),
            keyword_optimized_title=titles.get("keyword_optimized_title", ""),
            alternative_titles=titles.get("alternative_titles", []),
            thumbnail=thumbnail,
            script_structure=script,
            production_plan=production,
            low_cost_production=low_cost,
            seo_description=description,
            monetization=monetization,
        )

        logger.debug("blueprint_assembled", title=video.title)
        return blueprint

    def assemble_batch(
        self, videos: list[VideoIdea], niche: NicheScore
    ) -> list[VideoBlueprint]:
        """Assemble blueprints for multiple videos."""
        blueprints = [self.assemble_blueprint(v, niche) for v in videos]
        logger.info(
            "blueprints_assembled",
            niche=niche.niche,
            count=len(blueprints),
        )
        return blueprints

    def _generate_script_structure(
        self, video: VideoIdea, niche: str
    ) -> ScriptStructure:
        """Generate a video script structure."""
        topic = video.topic

        return ScriptStructure(
            hook=(
                f"Open with a bold, surprising statement or question about {topic}. "
                f"Example: 'What if everything you know about {topic} is wrong?' "
                f"or 'In the next 10 minutes, I'm going to show you something "
                f"about {topic} that will completely change your perspective.' "
                f"Duration: 5-15 seconds. Must create immediate curiosity."
            ),
            retention_pattern_interrupt=(
                f"At the 30-second mark, shift visual style — cut to a graphic, "
                f"change the music, or introduce an unexpected fact. "
                f"Every 2-3 minutes, introduce a new visual element, "
                f"change pacing, or tease upcoming content. "
                f"Use on-screen text callouts for key points."
            ),
            story_progression=(
                f"Structure as a journey: Problem → Investigation → Discovery → "
                f"Solution. Start with the 'why this matters' angle. "
                f"Build knowledge progressively — each section should unlock "
                f"understanding needed for the next. "
                f"Use real-world examples and data to support each point."
            ),
            mid_video_curiosity_loop=(
                f"At the midpoint, tease the most valuable insight: "
                f"'But the REAL secret about {topic} is coming up — "
                f"and it's something most people completely miss.' "
                f"This prevents mid-video drop-off."
            ),
            final_payoff=(
                f"Deliver the promised insight with maximum impact. "
                f"Summarize the top 3 takeaways. "
                f"End with an actionable next step the viewer can take today."
            ),
            cta_placement=(
                f"Soft CTA at 30% mark: 'If you're finding this helpful, "
                f"consider subscribing.' "
                f"End CTA: 'Subscribe and hit the bell for more "
                f"{niche} content every week.' "
                f"Link to related video in end screen."
            ),
        )

    def _generate_production_plan(
        self, video: VideoIdea, niche: str
    ) -> ProductionPlan:
        """Generate a visual production plan."""
        return ProductionPlan(
            stock_footage_sources=[
                "Pexels (free)", "Pixabay (free)", "Videvo (free/premium)",
                "Artgrid (premium)", "Storyblocks (premium subscription)",
            ],
            motion_graphics_ideas=[
                "Animated data charts for statistics",
                "Lower-third text overlays for key points",
                "Transition animations between sections",
                "Animated icons/illustrations for concepts",
            ],
            animation_suggestions=[
                "Kinetic typography for quotes",
                "Animated infographics",
                "Simple character animation for explanations",
                "Map/timeline animations for historical content",
            ],
            on_screen_text_strategies=[
                "Key statistics in large bold font",
                "Bullet point summaries after each section",
                "Highlighted keywords during narration",
                "Chapter title cards between sections",
            ],
            editing_rhythm=(
                f"Fast cuts (2-5 seconds) during high-energy sections. "
                f"Longer shots (5-10 seconds) for complex explanations. "
                f"Jump cuts in voiceover sections. "
                f"B-roll transitions every 10-15 seconds to maintain visual interest. "
                f"Music shifts to match emotional beats."
            ),
        )

    def _generate_low_cost_plan(self, niche: str) -> LowCostProduction:
        """Generate a low-cost production method."""
        return LowCostProduction(
            stock_footage_libraries=[
                "Pexels.com — Free HD/4K stock footage",
                "Pixabay.com — Free stock footage, no attribution required",
                "Videvo.net — Free and premium stock footage",
                "Coverr.co — Free stock footage for creators",
                "Mixkit.co — Free HD stock footage",
            ],
            creative_commons_sources=[
                "Wikimedia Commons — Educational/historical footage",
                "Internet Archive — Public domain video collection",
                "NASA Media Library — Space/science footage (public domain)",
                "Library of Congress — Historical footage",
            ],
            public_domain_sources=[
                "Archive.org — Millions of free media files",
                "Public Domain Review — Curated public domain content",
                "Prelinger Archives — Historical films",
            ],
            ai_voiceover_tools=[
                "ElevenLabs — High-quality AI voice cloning",
                "Play.ht — Neural text-to-speech",
                "Murf.ai — AI voice generator",
                "Fliki — AI video creation with voiceover",
                "Google Cloud TTS — Cost-effective at scale",
            ],
            screen_recording_tools=[
                "OBS Studio — Free, open source screen recording",
                "ShareX — Free screenshot and screen recording",
                "Loom — Quick screen recordings with webcam",
            ],
            animation_tools=[
                "Canva — Free animated graphics and presentations",
                "DaVinci Resolve — Free professional video editing",
                "Blender — Free 3D animation (advanced)",
                "Animaker — Simple animated video creation",
                "Kdenlive — Free open-source video editor",
            ],
            estimated_cost_per_video=(
                "$0-10 (fully free tools) or $20-50 (premium stock + AI voice)"
            ),
        )
