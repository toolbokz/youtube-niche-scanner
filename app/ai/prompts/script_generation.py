"""Script structure generation prompt templates for Gemini."""
from __future__ import annotations

from typing import Any


def script_structure_prompt(
    niche: str,
    topic: str,
    angle: str = "",
    title: str = "",
    virality_score: float = 0,
    ctr_potential: float = 0,
) -> str:
    """Build a prompt asking Gemini Flash to generate a video script structure.

    Parameters
    ----------
    niche : str
        The niche the video belongs to.
    topic : str
        The specific video topic.
    angle : str
        Content angle (e.g. "tutorial", "myth-busting").
    title : str
        The video title.
    virality_score : float
        Virality prediction score (0-100).
    ctr_potential : float
        CTR potential score (0-100).
    """
    context_block = ""
    if virality_score:
        context_block += f"Virality Score: {virality_score:.0f}/100\n"
    if ctr_potential:
        context_block += f"CTR Potential: {ctr_potential:.0f}/100\n"

    return f"""\
You are a YouTube scriptwriter who specialises in high-retention video scripts.

Create a video script structure for:

NICHE: {niche}
TOPIC: {topic}
ANGLE: {angle or "general"}
TITLE: {title or topic}
{context_block}

Return JSON with exactly this structure:
{{
  "hook": "<specific opening hook for this topic — the first 15 seconds that grab attention. Include an example opening line.>",
  "retention_pattern_interrupt": "<specific pattern interrupt strategy for this content type. When to change visuals, introduce new elements, or shift pacing.>",
  "story_progression": "<narrative arc specific to this topic and angle. How the content builds from opening to climax.>",
  "mid_video_curiosity_loop": "<specific mid-video tease that prevents drop-off. Reference the actual topic/insight being covered.>",
  "final_payoff": "<specific conclusion that delivers on the hook's promise. What key takeaways to emphasise.>",
  "cta_placement": "<CTA strategy specific to {niche} audience — when and how to ask for engagement.>"
}}

Guidelines:
- The hook MUST be specific to "{topic}" — not a generic opening pattern.
- Include an actual example opening line in the hook.
- The story progression should match the "{angle}" content angle.
  A tutorial needs a different arc than a myth-busting or case study video.
- Pattern interrupts should be timed to typical audience retention curves.
- The mid-video curiosity loop should reference a specific insight from the topic.
- CTAs should feel natural to the {niche} community.
- All sections should be 2-4 sentences of actionable guidance.

Return ONLY valid JSON."""
