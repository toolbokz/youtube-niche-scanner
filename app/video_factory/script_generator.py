"""Video Factory — Step 2: Script Generation.

Generates a full YouTube video script structured for maximum retention.
"""
from __future__ import annotations

from typing import Any

from app.core.logging import get_logger
from app.video_factory.models import VideoConcept, VideoScript, ScriptSection
from app.video_factory.prompts import script_generation_prompt

logger = get_logger(__name__)

# Approximate words-per-minute for narration timing
_WPM = 150


class ScriptGenerator:
    """Generate complete video scripts from a concept."""

    async def generate(self, niche: str, concept: VideoConcept) -> VideoScript:
        """Generate a full script for the given concept.

        Parameters
        ----------
        niche : str
            The niche being targeted.
        concept : VideoConcept
            Video concept from Step 1.

        Returns
        -------
        VideoScript
            Complete narration script with timed sections.
        """
        logger.info("script_generation_start", niche=niche, title=concept.title)

        try:
            from app.ai.client import get_ai_client

            client = get_ai_client()
            prompt = script_generation_prompt(niche, concept.model_dump())
            result = client.generate_json(prompt, use_pro=True, temperature=0.7, max_tokens=8192)

            if result and isinstance(result, dict):
                sections = [
                    ScriptSection(**s)
                    for s in result.get("sections", [])
                    if isinstance(s, dict)
                ]
                if sections:
                    script = VideoScript(
                        title=result.get("title", concept.title),
                        sections=sections,
                        total_word_count=result.get("total_word_count", self._count_words(sections)),
                        estimated_duration_seconds=result.get(
                            "estimated_duration_seconds",
                            sum(s.duration_seconds for s in sections),
                        ),
                        target_audience=result.get("target_audience", concept.target_audience),
                        tone=result.get("tone", "engaging"),
                    )
                    logger.info(
                        "script_generation_done",
                        niche=niche,
                        sections=len(sections),
                        words=script.total_word_count,
                    )
                    return script

        except Exception as exc:
            logger.warning("script_generation_ai_failed", niche=niche, error=str(exc))

        # Fallback
        return self._fallback_script(niche, concept)

    @staticmethod
    def _count_words(sections: list[ScriptSection]) -> int:
        return sum(len(s.content.split()) for s in sections)

    def _fallback_script(self, niche: str, concept: VideoConcept) -> VideoScript:
        """Generate a structured fallback script."""
        sections = [
            ScriptSection(
                section_type="hook",
                section_title="Opening Hook",
                content=(
                    f"What if I told you that everything you think you know about "
                    f"{niche} is completely wrong? In the next few minutes, I'm going "
                    f"to show you exactly why — and what you should be doing instead."
                ),
                duration_seconds=10,
                visual_notes="Eye-catching intro animation with bold text overlay",
                transition_note="Quick cut to intro",
            ),
            ScriptSection(
                section_type="intro",
                section_title="Introduction",
                content=(
                    f"Welcome back to the channel. Today we're diving deep into {niche}. "
                    f"I've spent weeks researching this topic, and what I found shocked me. "
                    f"By the end of this video, you'll have a completely new perspective on "
                    f"{niche} — and actionable steps you can take right now. "
                    f"Let's get into it."
                ),
                duration_seconds=25,
                visual_notes="Channel branding, topic title reveal",
                transition_note="Smooth transition to first point",
            ),
            ScriptSection(
                section_type="main_1",
                section_title="The Surprising Truth",
                content=(
                    f"Let's start with what most people get wrong about {niche}. "
                    f"The conventional wisdom tells us one thing, but the data tells "
                    f"a completely different story. Studies show that the majority of "
                    f"people approach {niche} in a way that's actually counterproductive. "
                    f"Here's what's really happening behind the scenes, and why it matters "
                    f"so much for anyone looking to succeed in this space."
                ),
                duration_seconds=90,
                visual_notes="Data visualizations, infographics, supporting B-roll",
                transition_note="But it gets even more interesting...",
            ),
            ScriptSection(
                section_type="main_2",
                section_title="The Hidden Strategy",
                content=(
                    f"Now here's where things get really interesting. The top performers "
                    f"in {niche} all share one thing in common — and it's not what you'd "
                    f"expect. They've discovered a strategy that most people completely "
                    f"overlook. Let me break it down step by step so you can apply this "
                    f"yourself starting today. First, you need to understand the fundamentals. "
                    f"Then, you apply this specific framework that changes everything."
                ),
                duration_seconds=120,
                visual_notes="Step-by-step breakdown graphics, examples",
                transition_note="And the results speak for themselves...",
            ),
            ScriptSection(
                section_type="main_3",
                section_title="Real-World Examples",
                content=(
                    f"Don't just take my word for it. Let's look at some real examples "
                    f"of people who've applied these {niche} strategies and seen incredible "
                    f"results. The first example shows how a complete beginner went from "
                    f"zero to impressive results in just a few months. The second example "
                    f"demonstrates how even experienced people in {niche} found new ways "
                    f"to improve by using these exact techniques."
                ),
                duration_seconds=90,
                visual_notes="Case study graphics, before/after comparisons",
                transition_note="So what does this all mean for you?",
            ),
            ScriptSection(
                section_type="main_4",
                section_title="Your Action Plan",
                content=(
                    f"Now let me give you a clear action plan that you can follow "
                    f"starting right now. Step one: assess your current position in "
                    f"{niche}. Step two: identify which of the strategies we discussed "
                    f"applies most to your situation. Step three: commit to implementing "
                    f"at least one change this week. The key is consistency — small actions "
                    f"compound into massive results over time."
                ),
                duration_seconds=75,
                visual_notes="Numbered action steps, checklist graphics",
                transition_note="Let me wrap this up with the most important takeaway...",
            ),
            ScriptSection(
                section_type="conclusion",
                section_title="Key Takeaway",
                content=(
                    f"If there's one thing I want you to remember from this video, it's "
                    f"this: success in {niche} isn't about working harder — it's about "
                    f"working smarter with the right strategies. The people who get the "
                    f"best results are the ones who take the time to understand these "
                    f"principles and apply them consistently."
                ),
                duration_seconds=30,
                visual_notes="Summary graphic with key points",
                transition_note="Transition to CTA",
            ),
            ScriptSection(
                section_type="cta",
                section_title="Call to Action",
                content=(
                    f"If you found this valuable, smash that like button and subscribe "
                    f"for more insights on {niche}. Drop a comment below telling me which "
                    f"strategy you're going to try first — I read every single comment. "
                    f"And if you want to dive even deeper, check out the video on screen "
                    f"right now. I'll see you in the next one."
                ),
                duration_seconds=20,
                visual_notes="Subscribe animation, end screen with related video",
                transition_note="",
            ),
        ]

        total_words = self._count_words(sections)
        return VideoScript(
            title=concept.title,
            sections=sections,
            total_word_count=total_words,
            estimated_duration_seconds=sum(s.duration_seconds for s in sections),
            target_audience=concept.target_audience,
            tone="engaging",
        )
