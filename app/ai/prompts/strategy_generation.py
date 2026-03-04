"""Strategy generation prompt templates for Gemini."""
from __future__ import annotations

from typing import Any


def video_strategy_prompt(
    niche_name: str,
    keywords: list[str],
    trend_data: dict[str, Any] | None = None,
    competition_data: dict[str, Any] | None = None,
    count: int = 15,
) -> str:
    """Build a prompt that asks Gemini Flash to generate video strategy ideas.

    Parameters
    ----------
    niche_name : str
        The niche to generate ideas for.
    keywords : list[str]
        Keyword cluster associated with the niche.
    trend_data : dict | None
        Topic velocity / trend signals.
    competition_data : dict | None
        Competition metrics.
    count : int
        Number of ideas to generate (10–20).
    """
    trend_block = ""
    if trend_data:
        trend_block = (
            f"Trend signals — Growth Rate: {trend_data.get('growth_rate', 0):.2f}x, "
            f"Acceleration: {trend_data.get('acceleration', 0):+.2f}, "
            f"Velocity Score: {trend_data.get('velocity_score', 0):.0f}/100"
        )

    comp_block = ""
    if competition_data:
        comp_block = (
            f"Competition — Avg Views (top 20): {competition_data.get('avg_views_top20', 0):,.0f}, "
            f"Avg Subscribers: {competition_data.get('avg_subscriber_count', 0):,.0f}, "
            f"Saturation: {competition_data.get('content_saturation', 0):.0f}%, "
            f"Competition Score: {competition_data.get('competition_score', 50):.0f}/100"
        )

    return f"""\
You are a YouTube content strategist specializing in faceless channels.

Generate {count} video ideas for the niche "{niche_name}".

KEYWORDS: {', '.join(keywords[:15])}
{trend_block}
{comp_block}

For each idea return JSON in this structure:
{{
  "video_ideas": [
    {{
      "title": "<CTR-optimized title with curiosity gap>",
      "concept": "<1-2 sentence video concept>",
      "content_angle": "<unique angle or hook>",
      "audience_hook": "<what grabs attention in first 5 seconds>",
      "target_keywords": ["<kw1>", "<kw2>"],
      "estimated_difficulty": "easy|medium|hard",
      "virality_potential": "low|medium|high"
    }}
  ]
}}

Guidelines:
- Titles should use proven CTR patterns (numbers, curiosity gaps, power words).
- Each idea should have a distinct angle — avoid repetition.
- Optimise for faceless production (voiceover, stock footage, screen recording).
- Consider current trends and competition when suggesting angles.
- Return exactly {count} ideas."""


def viral_opportunity_prompt(
    niche_name: str,
    anomalies: list[dict[str, Any]],
) -> str:
    """Prompt Gemini to interpret viral anomaly data and suggest new topics."""
    anomaly_block = ""
    for a in anomalies[:10]:
        anomaly_block += (
            f"- {a.get('channel_name', '?')} ({a.get('channel_subscribers', 0):,} subs): "
            f"\"{a.get('video_title', '')}\" — "
            f"{a.get('video_views', 0):,} views, "
            f"{a.get('views_to_sub_ratio', 0):.0f}× ratio, "
            f"{a.get('video_age_days', 0)} days old\n"
        )

    return f"""\
You are a YouTube viral content analyst.

The following videos from the niche "{niche_name}" show anomalous performance —
small channels (under 50K subscribers) achieving outsized view counts.

VIRAL ANOMALIES:
{anomaly_block}

Analyze the patterns and return JSON:
{{
  "common_themes": ["<theme1>", "<theme2>", "<theme3>"],
  "success_factors": ["<factor1>", "<factor2>"],
  "suggested_video_topics": [
    {{
      "title": "<suggested video title>",
      "reasoning": "<why this is likely to perform well>"
    }}
  ],
  "timing_insight": "<when/how to publish for maximum impact>"
}}

Identify what these viral videos have in common and suggest 5-8 new video
topics likely to replicate this success."""
