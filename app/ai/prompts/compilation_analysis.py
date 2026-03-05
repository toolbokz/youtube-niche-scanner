"""AI prompt templates for compilation video analysis."""
from __future__ import annotations


def compilation_strategy_prompt(
    niche_name: str,
    source_videos_json: str,
    segments_json: str,
    structure_json: str,
) -> str:
    """Build a prompt that asks Gemini to refine a compilation strategy.

    The AI receives the heuristic-generated strategy and enhances it with
    creative recommendations, better pacing, and audience-tuned advice.
    """
    return f"""You are a YouTube compilation video strategist and editing expert.

## Context
A user wants to create a high-performing compilation video in the **{niche_name}** niche.
The system has already identified source videos, extracted candidate segments, and
proposed an initial video structure.  Your job is to **refine and enhance** the strategy.

## Source Videos (JSON)
```json
{source_videos_json}
```

## Candidate Segments (JSON)
```json
{segments_json}
```

## Proposed Video Structure (JSON)
```json
{structure_json}
```

## Your Task
Return a JSON object with the following keys:
- "refined_structure": An array of objects, each with:
    - "position": int (1-based order in the timeline)
    - "segment_type": one of "intro_hook", "reveal", "surprise", "educational", "dramatic", "payoff", "outro_cta", "transition"
    - "source_video_title": string (which source video this clip comes from)
    - "timestamp_start": string (e.g. "1:30")
    - "timestamp_end": string (e.g. "2:15")
    - "energy_level": one of "low", "medium", "high", "climax"
    - "notes": string (why this ordering works)
- "editing_guidance": An object with:
    - "transition_style": string
    - "text_overlays": array of strings
    - "sound_effects": array of strings
    - "background_music_style": string
    - "pacing_notes": string
    - "color_grading_tips": string
    - "audio_mixing_tips": string
- "final_video_concept": An object with:
    - "title": string (optimized for CTR)
    - "description": string (SEO-optimised YouTube description, 200+ words)
    - "tags": array of strings (10-15 tags)
    - "target_audience": string
    - "emotional_hook": string (what keeps viewers watching)
    - "watch_time_strategy": string
    - "estimated_duration_minutes": number
    - "thumbnail_idea": string
- "pacing_analysis": string (paragraph explaining the overall pacing arc)
- "audience_retention_tips": array of strings (5-8 tips to maximize watch time)
- "monetization_angles": array of strings (3-5 ways to monetise this compilation)

IMPORTANT: Return ONLY valid JSON. No markdown, no explanation outside the JSON.
"""


def compilation_quick_insight_prompt(niche_name: str, video_count: int) -> str:
    """Short prompt for a quick compilation viability check."""
    return f"""You are a YouTube compilation video expert.

For the **{niche_name}** niche, with {video_count} potential source videos found,
provide a brief JSON assessment:

{{
    "viability_score": <0-100 integer>,
    "viability_reason": "<one sentence>",
    "best_compilation_formats": ["<format 1>", "<format 2>", "<format 3>"],
    "estimated_views_potential": "<e.g. 50K-200K>",
    "key_risk": "<one sentence>"
}}

Return ONLY valid JSON.
"""
