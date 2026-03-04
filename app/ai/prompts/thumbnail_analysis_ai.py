"""Thumbnail analysis AI prompt templates for Gemini."""
from __future__ import annotations

from typing import Any


def thumbnail_strategy_prompt(
    niche_name: str,
    pattern_data: dict[str, Any],
) -> str:
    """Prompt Gemini Flash to interpret thumbnail patterns and recommend styles.

    Parameters
    ----------
    niche_name : str
        Niche being analysed.
    pattern_data : dict
        Serialised ThumbnailPatternResult — signals, style_groups, insight.
    """
    style_block = ""
    for sg in pattern_data.get("style_groups", []):
        colors = ", ".join(sg.get("dominant_colors", [])[:3]) or "varied"
        style_block += (
            f"- **{sg.get('style_label', '?')}** ({sg.get('count', 0)} thumbnails): "
            f"Avg views {sg.get('avg_views', 0):,.0f}, "
            f"Colors: {colors}, "
            f"Text {sg.get('text_prevalence', 0):.0%}, "
            f"Faces {sg.get('face_prevalence', 0):.0%}, "
            f"Contrast {sg.get('avg_contrast', 0):.1f}\n"
        )

    insight = pattern_data.get("insight", "")
    recs = pattern_data.get("recommendations", [])
    existing_recs = "\n".join(f"- {r}" for r in recs) if recs else "None yet."

    return f"""\
You are a YouTube thumbnail designer and visual marketing expert.

Analyze the following thumbnail pattern statistics for the niche "{niche_name}"
and suggest the most effective visual style.

THUMBNAIL STYLE GROUPS:
{style_block}

CURRENT INSIGHT: {insight}
EXISTING RECOMMENDATIONS:
{existing_recs}

Total thumbnails analyzed: {pattern_data.get('total_analyzed', 0)}

Return JSON:
{{
  "color_strategy": {{
    "primary_colors": ["<color1>", "<color2>"],
    "accent_color": "<attention-grabbing accent>",
    "background_approach": "<solid / gradient / image-based>",
    "reasoning": "<why these colors work for this niche>"
  }},
  "text_overlay": {{
    "recommended": true/false,
    "max_words": <number>,
    "font_style": "<bold sans-serif / script / outline>",
    "placement": "<top / center / bottom-third>",
    "tips": ["<tip1>", "<tip2>"]
  }},
  "emotion_style": {{
    "primary_emotion": "<curiosity / shock / excitement / trust>",
    "face_usage": "<recommended / optional / avoid>",
    "expression_guidance": "<e.g. exaggerated surprise>",
    "emotional_trigger": "<what makes viewers click>"
  }},
  "layout_concepts": [
    {{
      "name": "<layout name>",
      "description": "<brief description of layout approach>",
      "best_for": "<type of video this suits>"
    }}
  ],
  "overall_recommendation": "<1 paragraph summary of optimal thumbnail strategy>"
}}

Be specific to this niche — do not give generic thumbnail advice."""
