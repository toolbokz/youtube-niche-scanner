"""Video Factory — AI prompts for all pipeline steps."""
from __future__ import annotations


def concept_generation_prompt(niche: str) -> str:
    """Prompt for generating a video concept from a niche."""
    return f"""You are a YouTube content strategist specializing in faceless, viral video creation.

Given the YouTube niche: "{niche}"

Generate a complete video concept that maximizes viewer engagement.

Return a JSON object with these exact keys:
{{
    "title": "An attention-grabbing YouTube title (under 70 characters)",
    "concept": "A detailed 2-3 sentence description of the video concept",
    "target_audience": "Who this video is for (be specific about demographics and interests)",
    "engagement_hook": "The hook that will stop viewers from scrolling (first 3 seconds)",
    "emotional_trigger": "The primary emotion this video targets (curiosity, fear, excitement, etc.)",
    "video_structure": ["section1", "section2", ...],
    "estimated_duration_minutes": 8
}}

Requirements:
- Title must use proven click-worthy patterns (numbers, curiosity gaps, power words)
- Concept must have a clear narrative arc
- Hook must be impossible to ignore
- Structure should maintain retention throughout

Return ONLY valid JSON. No markdown fences, no commentary."""


def script_generation_prompt(niche: str, concept: dict) -> str:
    """Prompt for generating a full video script."""
    return f"""You are an expert YouTube scriptwriter who creates scripts that maximize retention and engagement.

Niche: "{niche}"
Video Title: "{concept.get('title', '')}"
Video Concept: "{concept.get('concept', '')}"
Target Audience: "{concept.get('target_audience', '')}"
Engagement Hook: "{concept.get('engagement_hook', '')}"

Write a complete YouTube video script (5-10 minutes of narration, ~1000-1500 words).

Return a JSON object with:
{{
    "title": "The video title",
    "sections": [
        {{
            "section_type": "hook",
            "section_title": "Opening Hook",
            "content": "Full narration text for this section...",
            "duration_seconds": 10,
            "visual_notes": "What visuals should accompany this narration",
            "transition_note": "How to transition to next section"
        }},
        {{
            "section_type": "intro",
            "section_title": "Introduction",
            "content": "...",
            "duration_seconds": 30,
            "visual_notes": "...",
            "transition_note": "..."
        }},
        // ... more main sections (main_1, main_2, main_3, etc.)
        {{
            "section_type": "conclusion",
            "section_title": "Conclusion",
            "content": "...",
            "duration_seconds": 30,
            "visual_notes": "...",
            "transition_note": "..."
        }},
        {{
            "section_type": "cta",
            "section_title": "Call to Action",
            "content": "...",
            "duration_seconds": 15,
            "visual_notes": "...",
            "transition_note": ""
        }}
    ],
    "total_word_count": 1200,
    "estimated_duration_seconds": 480,
    "target_audience": "...",
    "tone": "engaging"
}}

Script writing rules:
1. HOOK (first 5-10 seconds): Start with a shocking statement, question, or teaser
2. INTRO: Briefly set context, promise value, use curiosity gap
3. MAIN SECTIONS: Each should contain a mini-hook, key information, and a bridge to the next
4. Use pattern interrupts every 60-90 seconds to maintain retention
5. Include curiosity loops ("But wait, there's something even more surprising...")
6. CONCLUSION: Deliver on the hook's promise, provide a memorable takeaway
7. CTA: Ask to subscribe, like, and comment with a specific question

The narration should sound natural and conversational, not robotic.

Return ONLY valid JSON."""


def clip_selection_prompt(niche: str, script_sections: list[dict]) -> str:
    """Prompt for selecting visual clips for each script section."""
    import json
    sections_text = json.dumps(script_sections, indent=2)
    return f"""You are a video editor selecting visual content for a YouTube video.

Niche: "{niche}"

Script sections:
{sections_text}

For each script section, suggest visual clips/footage that should accompany the narration.

Return a JSON array:
[
    {{
        "section_index": 0,
        "section_title": "Opening Hook",
        "source_type": "stock",
        "search_query": "specific search term for finding this footage",
        "description": "Describe exactly what visual should be shown",
        "duration_seconds": 10,
        "relevance_score": 0.95
    }},
    ...
]

Guidelines:
- Each section needs at least one clip suggestion
- Prefer dynamic, visually engaging footage
- source_type can be: "stock" (stock footage), "youtube" (reference clips), "text_overlay" (text on screen)
- search_query should be specific enough to find relevant footage
- Include visual variety — don't repeat the same type of footage

Return ONLY valid JSON."""


def thumbnail_concept_prompt(niche: str, title: str, concept: str) -> str:
    """Prompt for generating a thumbnail concept."""
    return f"""You are a YouTube thumbnail design expert with a deep understanding of click psychology.

Video Title: "{title}"
Niche: "{niche}"
Concept: "{concept}"

Generate a YouTube thumbnail concept that maximizes click-through rate.

Return a JSON object:
{{
    "visual_concept": "Detailed description of the main visual element",
    "text_overlay": "Bold text on the thumbnail (max 4-5 words)",
    "color_scheme": ["#hex1", "#hex2", "#hex3"],
    "layout_structure": "Describe the layout: where text goes, where image goes, etc.",
    "emotion_trigger": "The emotion this thumbnail should evoke",
    "contrast_strategy": "How to make this thumbnail stand out in a feed"
}}

Thumbnail best practices:
- Use high contrast colors
- Maximum 4-5 words of text
- One clear focal point
- Emotional triggers (shock, curiosity, excitement)
- Bold, readable fonts
- The thumbnail should tell a story even without the title

Return ONLY valid JSON."""


def metadata_generation_prompt(
    niche: str,
    title: str,
    script_sections: list[dict],
    concept: dict,
) -> str:
    """Prompt for generating YouTube publishing metadata."""
    import json
    sections_summary = json.dumps(
        [{"title": s.get("section_title", ""), "duration": s.get("duration_seconds", 0)}
         for s in script_sections],
        indent=2,
    )
    return f"""You are a YouTube SEO expert who specializes in maximizing search visibility and engagement.

Video Title: "{title}"
Niche: "{niche}"
Target Audience: "{concept.get('target_audience', '')}"

Script sections (for chapter timestamps):
{sections_summary}

Generate complete YouTube publishing metadata.

Return a JSON object:
{{
    "title": "SEO-optimized title (may refine the original)",
    "description": "Full YouTube description (500-1000 chars) with:\\n- Hook paragraph\\n- Video summary\\n- Timestamps/chapters\\n- Keywords naturally integrated\\n- Call-to-action\\n- Relevant links placeholder",
    "tags": ["tag1", "tag2", ...],
    "hashtags": ["#hashtag1", "#hashtag2", "#hashtag3"],
    "chapters": [
        {{"time": "0:00", "title": "Introduction"}},
        {{"time": "0:30", "title": "Section 1 Name"}},
        ...
    ],
    "category": "Education",
    "language": "en",
    "seo_keywords": ["keyword1", "keyword2", ...]
}}

SEO rules:
- Title: under 70 characters, front-load keywords
- Description: first 150 chars are critical (shown in search)
- Tags: 15-30 relevant tags, mix of broad and specific
- Hashtags: 3-5 relevant hashtags
- Chapters: accurate timestamps based on script sections
- Include viewer hook in first line of description

Return ONLY valid JSON."""
