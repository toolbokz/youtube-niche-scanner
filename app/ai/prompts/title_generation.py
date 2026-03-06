"""Title generation prompt templates for Gemini."""
from __future__ import annotations

from typing import Any


def title_generation_prompt(
    niche: str,
    topic: str,
    keywords: list[str],
    angle: str = "",
    trend_momentum: float = 0,
    competition_score: float = 0,
    ctr_potential: float = 0,
    virality_score: float = 0,
) -> str:
    """Build a prompt that asks Gemini Flash to generate CTR-optimized titles.

    Parameters
    ----------
    niche : str
        The niche the video belongs to.
    topic : str
        The specific video topic.
    keywords : list[str]
        Target SEO keywords.
    angle : str
        Content angle (e.g. "tutorial", "myth-busting").
    trend_momentum : float
        Trend momentum score (0-100).
    competition_score : float
        Competition score (0-100, higher = less competitive).
    ctr_potential : float
        CTR potential score (0-100).
    virality_score : float
        Virality prediction score (0-100).
    """
    context_block = ""
    if trend_momentum:
        context_block += f"Trend Momentum: {trend_momentum:.0f}/100\n"
    if competition_score:
        context_block += f"Competition Score: {competition_score:.0f}/100 (higher = less competitive)\n"
    if ctr_potential:
        context_block += f"CTR Potential: {ctr_potential:.0f}/100\n"
    if virality_score:
        context_block += f"Virality Score: {virality_score:.0f}/100\n"

    return f"""\
You are a YouTube title optimization expert who specialises in high-CTR titles.

Generate video titles for a video in the "{niche}" niche.

TOPIC: {topic}
ANGLE: {angle or "general"}
TARGET KEYWORDS: {', '.join(keywords[:10])}
{context_block}

Return JSON with exactly this structure:
{{
  "curiosity_gap_headline": "<title using curiosity gap pattern>",
  "keyword_optimized_title": "<SEO-optimized title with primary keyword near the start>",
  "alternative_titles": [
    "<alternative title 1>",
    "<alternative title 2>",
    "<alternative title 3>",
    "<alternative title 4>",
    "<alternative title 5>"
  ],
  "title_formulas": [
    "Curiosity Gap: <the curiosity title>",
    "SEO Optimized: <the keyword title>",
    "Alternative: <alt 1>",
    "Alternative: <alt 2>",
    "Alternative: <alt 3>"
  ]
}}

Guidelines:
- The curiosity gap headline should create an information gap that compels clicks.
- The keyword-optimized title should front-load the primary keyword for SEO.
- Alternative titles should each use a DIFFERENT proven CTR pattern:
  numbers/lists, how-to, comparison, controversy, personal story, urgency.
- Titles must be 40-70 characters for optimal YouTube display.
- Use power words sparingly — max 1-2 per title.
- Tailor vocabulary and tone to the "{niche}" audience.
- Do NOT use generic clickbait that could apply to any niche.
- Include the current year only if the topic is time-sensitive.

Return ONLY valid JSON."""
