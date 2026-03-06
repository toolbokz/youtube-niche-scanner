"""Description generation prompt templates for Gemini."""
from __future__ import annotations

from typing import Any


def description_generation_prompt(
    niche: str,
    topic: str,
    title: str,
    keywords: list[str],
    angle: str = "",
    trend_momentum: float = 0,
    competition_score: float = 0,
) -> str:
    """Build a prompt asking Gemini Flash to generate a YouTube description.

    Parameters
    ----------
    niche : str
        The niche the video belongs to.
    topic : str
        The specific video topic.
    title : str
        The video title (for context).
    keywords : list[str]
        Target SEO keywords.
    angle : str
        Content angle.
    trend_momentum : float
        Trend momentum score (0-100).
    competition_score : float
        Competition score (0-100).
    """
    context_block = ""
    if trend_momentum:
        context_block += f"Trend Momentum: {trend_momentum:.0f}/100\n"
    if competition_score:
        context_block += f"Competition Score: {competition_score:.0f}/100\n"

    return f"""\
You are a YouTube SEO expert who writes high-converting video descriptions.

Write a complete YouTube description for this video:

NICHE: {niche}
TOPIC: {topic}
TITLE: {title}
ANGLE: {angle or "general"}
TARGET KEYWORDS: {', '.join(keywords[:10])}
{context_block}

Return JSON with exactly this structure:
{{
  "intro_paragraph": "<SEO-optimized opening paragraph, 150-200 chars visible in search. Must hook the reader and contain the primary keyword naturally.>",
  "keyword_block": ["<keyword1>", "<keyword2>", "...up to 15 relevant tags/keywords"],
  "chapters": [
    "0:00 <chapter title>",
    "0:30 <chapter title>",
    "<more chapters with realistic timestamps>"
  ],
  "cta_structure": "<call-to-action block with subscribe, like, comment prompts tailored to {niche} audience>",
  "affiliate_positioning": "<resource/affiliate section with 3-4 specific product categories relevant to {niche}>"
}}

Guidelines:
- The intro paragraph is the MOST important — it appears in YouTube search results.
  Front-load the primary keyword naturally. Create urgency or curiosity.
- Chapters should reflect realistic video structure for a "{angle or 'general'}" style video.
  Use 6-10 chapters with plausible timestamps.
- The CTA should feel natural to the {niche} community, not generic.
- The affiliate section should reference specific TYPES of products/tools
  relevant to {niche} (not placeholder text).
- Include 12-15 keywords mixing head terms and long-tail phrases.

Return ONLY valid JSON."""
