"""Video strategy generation prompt templates for Gemini."""
from __future__ import annotations

from typing import Any


def video_ideas_prompt(
    niche: str,
    keywords: list[str],
    trend_momentum: float = 0,
    competition_score: float = 0,
    virality_score: float = 0,
    demand_score: float = 0,
    count: int = 10,
) -> str:
    """Build a prompt asking Gemini Flash to generate video ideas with titles.

    Parameters
    ----------
    niche : str
        The niche to generate ideas for.
    keywords : list[str]
        Keyword cluster.
    trend_momentum : float
        Trend momentum score (0-100).
    competition_score : float
        Competition score (0-100).
    virality_score : float
        Virality prediction score (0-100).
    demand_score : float
        Demand score (0-100).
    count : int
        Number of ideas to generate.
    """
    context_block = ""
    if trend_momentum:
        context_block += f"Trend Momentum: {trend_momentum:.0f}/100\n"
    if competition_score:
        context_block += f"Competition Score: {competition_score:.0f}/100 (higher = less saturated)\n"
    if virality_score:
        context_block += f"Virality Score: {virality_score:.0f}/100\n"
    if demand_score:
        context_block += f"Demand Score: {demand_score:.0f}/100\n"

    return f"""\
You are a YouTube content strategist specialising in faceless channels.

Generate exactly {count} video ideas for the niche "{niche}".

KEYWORDS: {', '.join(keywords[:15])}
{context_block}

For each idea return JSON in this structure:
{{
  "video_ideas": [
    {{
      "title": "<CTR-optimized title, 40-70 chars>",
      "topic": "<specific topic/keyword this video targets>",
      "angle": "<content angle: tutorial | deep dive | comparison | top 10 | mistakes | secrets | predictions | case study | step-by-step | myth-busting | history | expert tips | challenge | news | review>",
      "target_keywords": ["<kw1>", "<kw2>", "<kw3>"],
      "estimated_difficulty": "easy|medium|hard",
      "virality_potential": "low|medium|high"
    }}
  ]
}}

Guidelines:
- Each idea must have a DISTINCT angle — no repeats.
- Titles should use proven CTR patterns specific to the {niche} niche.
- Optimise for faceless production (voiceover, stock footage, screen recording).
- Consider the competition and trend data when choosing topics.
- Keywords should be realistic search terms viewers would use.
- Return exactly {count} ideas.

Return ONLY valid JSON."""


def channel_concept_prompt(
    niche: str,
    keywords: list[str],
    trend_momentum: float = 0,
    competition_score: float = 0,
    demand_score: float = 0,
) -> str:
    """Build a prompt asking Gemini Flash to generate a channel concept.

    Parameters
    ----------
    niche : str
        The niche for the channel.
    keywords : list[str]
        Associated keywords.
    trend_momentum : float
        Trend momentum (0-100).
    competition_score : float
        Competition score (0-100).
    demand_score : float
        Demand score (0-100).
    """
    context_block = ""
    if trend_momentum:
        context_block += f"Trend Momentum: {trend_momentum:.0f}/100\n"
    if competition_score:
        context_block += f"Competition Score: {competition_score:.0f}/100\n"
    if demand_score:
        context_block += f"Demand Score: {demand_score:.0f}/100\n"

    return f"""\
You are a YouTube channel strategist and brand expert.

Create a channel concept for the "{niche}" niche.

KEYWORDS: {', '.join(keywords[:10])}
{context_block}

Return JSON with exactly this structure:
{{
  "channel_names": [
    "<memorable channel name 1>",
    "<memorable channel name 2>",
    "<memorable channel name 3>",
    "<memorable channel name 4>",
    "<memorable channel name 5>"
  ],
  "positioning": "<1-2 sentence content positioning statement that differentiates from competitors>",
  "audience_persona": {{
    "age_range": "<specific age range>",
    "interests": ["<interest1>", "<interest2>", "<interest3>", "<interest4>", "<interest5>"],
    "pain_points": [
      "<specific pain point 1>",
      "<specific pain point 2>",
      "<specific pain point 3>"
    ],
    "content_preferences": [
      "<preference 1>",
      "<preference 2>",
      "<preference 3>",
      "<preference 4>"
    ]
  }}
}}

Guidelines:
- Channel names should be catchy, memorable, and available (avoid generic words).
- The positioning statement should clearly communicate the channel's unique value.
- The audience persona should be specific to {niche}, not generic.
- Pain points should reflect real problems the {niche} audience faces.
- Content preferences should be based on what performs well in this niche.

Return ONLY valid JSON."""
