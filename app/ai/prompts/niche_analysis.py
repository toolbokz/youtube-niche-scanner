"""Niche analysis prompt templates for Gemini."""
from __future__ import annotations

from typing import Any


def niche_analysis_prompt(niches: list[dict[str, Any]]) -> str:
    """Build a prompt that asks Gemini Pro to provide deep niche insights.

    Parameters
    ----------
    niches : list[dict]
        Serialised NicheScore dicts (niche, overall_score, demand_score,
        competition_score, trend_momentum, virality_score, ctr_potential,
        viral_opportunity_score, topic_velocity_score, keywords).
    """
    niche_block = ""
    for n in niches:
        niche_block += (
            f"- **{n['niche']}** (Score {n.get('overall_score', 0):.0f}): "
            f"Demand {n.get('demand_score', 0):.0f}, "
            f"Competition {n.get('competition_score', 0):.0f}, "
            f"Trend {n.get('trend_momentum', 0):.0f}, "
            f"Virality {n.get('virality_score', 0):.0f}, "
            f"CTR {n.get('ctr_potential', 0):.0f}, "
            f"Viral Opp {n.get('viral_opportunity_score', 0):.0f}, "
            f"Velocity {n.get('topic_velocity_score', 0):.0f}, "
            f"Keywords: {', '.join(n.get('keywords', [])[:8])}\n"
        )

    return f"""\
You are a YouTube growth strategist and data analyst.

Analyze the following dataset of YouTube niches, including their demand score,
competition score, trend momentum, virality signals, CTR potential,
viral opportunity indicators, and content velocity.

NICHE DATA:
{niche_block}

Provide a comprehensive analysis in JSON with the following structure:
{{
  "growth_potential": [
    {{
      "niche": "<name>",
      "rating": "high|medium|low",
      "reasoning": "<2-3 sentences explaining long-term growth potential>"
    }}
  ],
  "content_strategy_insights": [
    {{
      "niche": "<name>",
      "recommended_angle": "<brief content angle recommendation>",
      "differentiation_tip": "<how to stand out from competition>",
      "ideal_posting_frequency": "<e.g. 3x/week>"
    }}
  ],
  "audience_behavior_insights": [
    {{
      "niche": "<name>",
      "primary_audience": "<audience segment>",
      "engagement_pattern": "<how this audience typically engages>",
      "retention_hook": "<what keeps viewers watching in this niche>"
    }}
  ],
  "overall_recommendation": "<1 paragraph summary of best opportunities>"
}}

Focus on which niches have the strongest long-term growth potential and explain why.
Base your analysis ONLY on the data provided — do not fabricate statistics."""


def quick_niche_insight_prompt(niche_data: dict[str, Any]) -> str:
    """Short prompt for on-demand niche insight in the Discovery Map UI."""
    return f"""\
You are a YouTube growth strategist.

Given this niche profile, provide a brief strategic insight.

NICHE: {niche_data.get('niche', niche_data.get('label', 'Unknown'))}
Score: {niche_data.get('overall_score', niche_data.get('score', 0)):.0f}/100
Demand: {niche_data.get('demand_score', niche_data.get('demand', 0)):.0f}
Competition: {niche_data.get('competition_score', niche_data.get('competition', 0)):.0f}
Trend Momentum: {niche_data.get('trend_momentum', niche_data.get('trend', 0)):.0f}
Virality: {niche_data.get('virality_score', niche_data.get('virality', 0)):.0f}
Keywords: {', '.join(niche_data.get('keywords', [])[:10])}

Return JSON:
{{
  "quick_insight": "<2-3 sentence strategic assessment>",
  "recommended_video_topics": ["<topic1>", "<topic2>", "<topic3>", "<topic4>", "<topic5>"],
  "growth_opportunities": ["<opportunity1>", "<opportunity2>", "<opportunity3>"],
  "risk_factors": ["<risk1>", "<risk2>"]
}}"""
