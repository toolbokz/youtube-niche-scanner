"""Thumbnail concept generation prompt templates for Gemini."""
from __future__ import annotations

from typing import Any


def thumbnail_concept_prompt(
    niche: str,
    title: str,
    angle: str = "",
    ctr_potential: float = 0,
    competition_score: float = 0,
    virality_score: float = 0,
) -> str:
    """Build a prompt asking Gemini Flash to generate a thumbnail concept.

    Parameters
    ----------
    niche : str
        The niche the video belongs to.
    title : str
        The video title.
    angle : str
        Content angle.
    ctr_potential : float
        CTR potential score (0-100).
    competition_score : float
        Competition score (0-100).
    virality_score : float
        Virality prediction score (0-100).
    """
    context_block = ""
    if ctr_potential:
        context_block += f"CTR Potential: {ctr_potential:.0f}/100\n"
    if competition_score:
        context_block += f"Competition Score: {competition_score:.0f}/100\n"
    if virality_score:
        context_block += f"Virality Score: {virality_score:.0f}/100\n"

    return f"""\
You are a YouTube thumbnail design strategist who understands visual psychology.

Design a thumbnail concept for this video:

NICHE: {niche}
TITLE: {title}
ANGLE: {angle or "general"}
{context_block}

Return JSON with exactly this structure:
{{
  "emotion_trigger": "<primary emotion: curiosity | shock | urgency | inspiration | fear | humor>",
  "contrast_strategy": "<description of contrast approach for readability>",
  "visual_focal_point": "<what the viewer's eye should be drawn to first>",
  "text_overlay": "<2-4 word punchy text overlay for the thumbnail, ALL CAPS>",
  "color_palette": ["<hex color 1>", "<hex color 2>", "<hex color 3>"],
  "layout_concept": "<detailed description of the thumbnail layout, composition, and visual hierarchy>"
}}

Guidelines:
- The emotion trigger should match the content angle and niche expectations.
- Text overlay must be SHORT (2-4 words max) — readable at small mobile sizes.
- Color palette should create high contrast. Use niche-appropriate tones:
  finance = blue/green/gold, tech = blue/purple, health = green/white, etc.
- Layout concept should describe specific visual composition, not generic advice.
- The focal point should exploit the curiosity or emotional hook of the title.
- Consider mobile-first: 70%+ of YouTube is mobile, thumbnails are tiny.

Return ONLY valid JSON."""
