"""Trend interpretation prompt templates for Gemini."""
from __future__ import annotations

from typing import Any


def trend_forecast_prompt(
    velocities: dict[str, dict[str, Any]],
    niches: list[dict[str, Any]] | None = None,
) -> str:
    """Prompt Gemini Pro to forecast which topics will explode on YouTube.

    Parameters
    ----------
    velocities : dict[str, dict]
        Mapping of niche name → TopicVelocityResult dicts.
    niches : list[dict] | None
        Optional NicheScore data for richer context.
    """
    vel_block = ""
    for niche_name, vel in velocities.items():
        trend_label = (
            "Accelerating" if vel.get("acceleration", 0) > 0.2
            else "Decelerating" if vel.get("acceleration", 0) < -0.2
            else "Steady"
        )
        vel_block += (
            f"- **{niche_name}**: Growth {vel.get('growth_rate', 0):.2f}×, "
            f"Acceleration {vel.get('acceleration', 0):+.2f}, "
            f"Velocity {vel.get('velocity_score', 0):.0f}/100, "
            f"Trend: {trend_label}\n"
        )

    niche_context = ""
    if niches:
        for n in niches[:10]:
            niche_context += (
                f"- {n['niche']}: Score {n.get('overall_score', 0):.0f}, "
                f"Demand {n.get('demand_score', 0):.0f}, "
                f"Trend {n.get('trend_momentum', 0):.0f}\n"
            )

    return f"""\
You are a YouTube trend forecaster and data analyst.

Given the following topic velocity data (measuring how fast content upload
volume is growing for each topic) and niche scores, determine which topics
are likely to explode in popularity on YouTube within the next 3 months.

TOPIC VELOCITY DATA:
{vel_block}

{"NICHE SCORES:" + chr(10) + niche_context if niche_context else ""}

Return JSON:
{{
  "trend_forecast": [
    {{
      "topic": "<niche/topic name>",
      "explosion_likelihood": "very_high|high|moderate|low",
      "predicted_peak_timeframe": "<e.g. 4-6 weeks>",
      "reasoning": "<why this topic will grow>",
      "early_mover_advantage": "<how to capitalise before saturation>"
    }}
  ],
  "emerging_subtopics": [
    {{
      "subtopic": "<emerging sub-niche>",
      "parent_niche": "<niche it branches from>",
      "signal": "<what data supports this>"
    }}
  ],
  "overall_market_direction": "<1-2 sentence summary of where YouTube content is heading>"
}}

Base your forecast ONLY on the data provided. Be specific and actionable."""
