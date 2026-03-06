# Creative Generation Logic Audit — Growth Strategist

**Date:** 2026-03-06
**Scope:** Hard-coded creative content generation that should be replaced with AI generation
**Status:** ✅ Implementation complete — all 12 refactor targets shipped

---

## Table of Contents

1. [Overview of Creative Generation Logic](#section-1--overview-of-creative-generation-logic)
2. [Locations of Hard-Coded Templates](#section-2--locations-of-hard-coded-templates)
3. [AI Replacement Opportunities](#section-3--ai-replacement-opportunities)
4. [Proposed AI Integration Points](#section-4--proposed-ai-integration-points)
5. [Risk Assessment](#section-5--risk-assessment)
6. [Refactor Priority List](#section-6--refactor-priority-list)
7. [Implementation Summary](#section-7--implementation-summary)

---

## Implementation Status

> All 12 audit targets have been implemented with the AI-first + fallback pattern.
> Original hard-coded templates are preserved as fallbacks.
> Full test suite: **315 tests passing** (291 original + 24 new AI-path tests).

| # | Target | Status | Files Modified |
|---|--------|--------|----------------|
| H1 | Title Generation | ✅ Done | `app/title_generation/engine.py`, `app/ai/prompts/title_generation.py` |
| H2 | Description Generation | ✅ Done | `app/description_generation/engine.py`, `app/ai/prompts/description_generation.py` |
| H3 | Thumbnail Strategy | ✅ Done | `app/thumbnail_strategy/engine.py`, `app/ai/prompts/thumbnail_generation.py` |
| H4 | Video Strategy Titles & Ideas | ✅ Done | `app/video_strategy/engine.py`, `app/ai/prompts/video_strategy_generation.py` |
| M1 | Script Structure | ✅ Done | `app/video_strategy/blueprint.py`, `app/ai/prompts/script_generation.py` |
| M2 | Channel Names | ✅ Done | `app/video_strategy/engine.py` (via `channel_concept_prompt`) |
| M3 | Audience Persona | ✅ Done | `app/video_strategy/engine.py` (via `channel_concept_prompt`) |
| M4 | Positioning Statement | ✅ Done | `app/video_strategy/engine.py` (via `channel_concept_prompt`) |
| L1 | Monetization Products | ✅ Done | `app/monetization_engine/engine.py` (inline prompt) |
| L2 | Monetization Lead Magnets | ✅ Done | `app/monetization_engine/engine.py` (inline prompt) |
| L3 | Monetization Expansion | ✅ Done | `app/monetization_engine/engine.py` (inline prompt) |
| L4 | Report Narrative | — Skipped | Data-driven rendering — no AI needed |

---

## SECTION 1 — Overview of Creative Generation Logic

The codebase contains **6 modules with significant hard-coded creative content generation** that produces user-visible outputs (titles, descriptions, thumbnails, scripts, strategies, metadata). These modules use static string templates with simple `{variable}` interpolation and `random.choice()` selection to generate content that directly reaches end users.

An AI service layer already exists (`app/ai/service.py`) with 7 public functions and Gemini Flash + Pro integration, but it is **only used during the optional AI enhancement step (Step 8b) of the pipeline and in the Video Factory**. The core content generation engines (title, description, thumbnail strategy, video strategy, blueprint assembler) operate entirely with hard-coded templates and produce identical structural patterns regardless of niche characteristics.

### Summary of Findings

| Category | Modules Affected | Template Instances | User Impact |
|----------|------------------|--------------------|-------------|
| Title Generation | 2 files | 30 title formula templates | Direct — YouTube video titles |
| Description Generation | 1 file | 5 template methods | Direct — YouTube descriptions |
| Thumbnail Strategy | 1 file | 6 emotion layouts + text overlays | Direct — thumbnail design briefs |
| Video Strategy | 2 files | 15 angle templates + 15 title templates | Direct — video ideas and titles |
| Script Structure | 1 file | 6 hard-coded script sections | Direct — video production scripts |
| Monetization Copy | 1 file | 5 product templates + 4 lead magnets | Direct — monetization strategy text |
| Video Factory Metadata | 1 file | Fallback description + tags | Direct — YouTube publishing metadata |

### Modules Already Using AI (No Changes Needed)

| Module | AI Usage |
|--------|----------|
| `app/video_factory/metadata_generator.py` | Calls `client.generate_json()` for metadata (with fallback) |
| `app/video_factory/thumbnail_generator.py` | Calls `client.generate_json()` for thumbnail concepts (with fallback) |
| `app/ai/service.py` | Full AI service layer — 13 functions via Gemini (7 original + 6 new creative) |
| `app/ai/prompts/` | 10 prompt templates for Gemini (5 original + 5 new creative) |

---

## SECTION 2 — Locations of Hard-Coded Templates

### 2.1 — Title Generation Engine

| File | Lines | Template Type | Example Template |
|------|-------|---------------|-----------------|
| `app/title_generation/engine.py` | 17–25 | Curiosity Gap Formulas (8) | `"The {topic} Secret That {audience} Don't Want You to Know"` |
| `app/title_generation/engine.py` | 27–34 | Keyword-Optimized Formulas (7) | `"{topic}: Complete Guide for Beginners ({year})"` |
| `app/title_generation/engine.py` | 36–47 | Alternative Formulas (10) | `"Why 99% of People Fail at {topic}"` |

**Category: B — Creative Content Generation**

These 25 title formulas are randomly selected via `random.choice()` and produce generic clickbait-style titles with no awareness of niche-specific language, competition patterns, trending formats, or audience preferences. The `{audience}` field is hardcoded to `"experts"` (line 82). The `{n}` parameter uses arbitrary numbers `[5, 7, 10, 15]` without data-driven reasoning.

### 2.2 — Description Generation Engine

| File | Lines | Template Type | Example Template |
|------|-------|---------------|-----------------|
| `app/description_generation/engine.py` | 43–51 | SEO Intro Paragraph | `"In this video, we dive deep into {topic} and uncover everything you need to know about {niche}..."` |
| `app/description_generation/engine.py` | 53–61 | Keyword Block Builder | Static modifiers: `["guide", "tutorial", "tips", "explained", "2026", "best"]` |
| `app/description_generation/engine.py` | 63–73 | Chapter Suggestions (9) | `"0:00 Introduction to {topic}"`, `"2:00 Key Concepts Explained"` |
| `app/description_generation/engine.py` | 75–84 | CTA Structure | `"🔔 Subscribe for more {niche} content and hit the notification bell!"` |
| `app/description_generation/engine.py` | 86–93 | Affiliate Section | `"📚 Resources & Tools Mentioned:\n• [Tool/Product 1] — [Affiliate Link]"` |

**Category: B — Creative Content Generation**

Every description follows an identical structure regardless of niche. The intro paragraph uses the same generic phrasing for all topics. Chapter timestamps are fixed (`0:00`, `0:30`, `2:00`, `4:30`, etc.) and chapter titles are completely generic (`"Key Concepts Explained"`, `"Practical Examples"`). The CTA copy is identical for every video. The affiliate section contains unfilled placeholder text (`[Tool/Product 1]`, `[Affiliate Link]`).

### 2.3 — Thumbnail Strategy Engine

| File | Lines | Template Type | Example Template |
|------|-------|---------------|-----------------|
| `app/thumbnail_strategy/engine.py` | 14–60 | Emotion→Visual Mapping (6 emotions) | `"Mysterious object or partially revealed information"` (curiosity focal point) |
| `app/thumbnail_strategy/engine.py` | 95–110 | Text Overlay Generation | Extracts power words or truncates title to first 4 words + `"..."` |
| `app/thumbnail_strategy/engine.py` | 112–152 | Layout Concept Descriptions (6) | `"Split design: Left 60% shows the intriguing visual element..."` (curiosity layout) |

**Category: B — Creative Content Generation**

The emotion detection uses a simple keyword-counting heuristic (6 lists of ~6 keywords each). Layout concepts are static paragraph descriptions that never vary within an emotion category — every "curiosity" video gets the identical layout description. Text overlay generation is purely mechanical (power-word extraction or title truncation) with no awareness of what text drives CTR in a specific niche. Color palettes are hardcoded per emotion with no niche adaptation.

### 2.4 — Video Strategy Engine

| File | Lines | Template Type | Example Template |
|------|-------|---------------|-----------------|
| `app/video_strategy/engine.py` | 47–62 | Angle Templates (15) | `"Beginner's guide / introduction"`, `"Top 10 / ranking list"` |
| `app/video_strategy/engine.py` | 228–252 | Title Creation Templates (15) | `"Top 10 {keyword} That Will Change Everything"`, `"{keyword}: Hidden Secrets Exposed"` |
| `app/video_strategy/engine.py` | 143–149 | Channel Name Ideas (5) | `"{Core} Explained"`, `"The {Core} Lab"`, `"Simply {Core}"` |
| `app/video_strategy/engine.py` | 151–162 | Audience Persona | Hardcoded age `"18-45"`, generic pain points and preferences |
| `app/video_strategy/engine.py` | 164–173 | Positioning Statement | `"The go-to channel for {niche} insights..."` |

**Category: B — Creative Content Generation**

The `_create_title()` method (lines 228–252) is a key instance — it contains 15 keyword→template mappings that produce the video titles displayed to users. Every "top 10" angle always generates `"Top 10 {keyword} That Will Change Everything"`. Every "challenge" angle always generates `"I Tried {keyword} for 30 Days - Results"`. Channel names follow 5 fixed patterns regardless of niche personality. The audience persona returns a hardcoded `"18-45"` age range and 3 generic pain points for all niches.

### 2.5 — Blueprint Assembler (Script Structure)

| File | Lines | Template Type | Example Template |
|------|-------|---------------|-----------------|
| `app/video_strategy/blueprint.py` | 87–106 | Script Hook | `"Open with a bold, surprising statement or question about {topic}..."` |
| `app/video_strategy/blueprint.py` | 107–113 | Retention Pattern Interrupt | `"At the 30-second mark, shift visual style..."` |
| `app/video_strategy/blueprint.py` | 114–121 | Story Progression | `"Structure as a journey: Problem → Investigation → Discovery → Solution..."` |
| `app/video_strategy/blueprint.py` | 122–127 | Mid-Video Curiosity Loop | `"But the REAL secret about {topic} is coming up..."` |
| `app/video_strategy/blueprint.py` | 128–132 | Final Payoff | `"Deliver the promised insight with maximum impact..."` |
| `app/video_strategy/blueprint.py` | 133–141 | CTA Placement | `"Soft CTA at 30% mark: 'If you're finding this helpful, consider subscribing.'"` |
| `app/video_strategy/blueprint.py` | 143–168 | Production Plan | Static lists of stock footage sources, motion graphics ideas |
| `app/video_strategy/blueprint.py` | 170–217 | Low-Cost Production Plan | Static lists of tools (ElevenLabs, OBS, Canva, etc.) |

**Category: B (script structure) / A (production tool lists)**

The script structure sections (hook, retention interrupt, story progression, mid-video loop, final payoff, CTA) are all generic paragraph templates with `{topic}` interpolation. Every video across every niche receives the identical narrative structure advice — a finance video gets the same hook template as a cooking video. The CTA phrasing is always `"If you're finding this helpful, consider subscribing"`.

Production tool lists (lines 143–217) are **Category A** — these are factual reference data (tool names, URLs) and should remain static.

### 2.6 — Monetization Engine

| File | Lines | Template Type | Example Template |
|------|-------|---------------|-----------------|
| `app/monetization_engine/engine.py` | 97–103 | Digital Product Suggestions (5) | `"Comprehensive {niche} eBook/Guide"`, `"{niche} Online Course"` |
| `app/monetization_engine/engine.py` | 105–111 | Lead Magnet Suggestions (4) | `"Free {niche} Starter Guide (PDF)"`, `"Top 10 {niche} Resources List"` |
| `app/monetization_engine/engine.py` | 113–124 | Expansion Strategy | `"Phase 1 (Months 1-3): Build authority in {niche}..."` (4 phases, same for all) |

**Category: B — Creative Content Generation**

Digital product names and lead magnet titles use fixed patterns. The expansion strategy is a 4-phase roadmap that is identical for every niche — a gaming niche gets the same phasing advice as a finance niche, despite vastly different monetization timelines and approaches.

### 2.7 — Video Factory Metadata (Fallback)

| File | Lines | Template Type | Example Template |
|------|-------|---------------|-----------------|
| `app/video_factory/metadata_generator.py` | 109–116 | Fallback Description | `"In this video, we explore {niche} and reveal insights that can change your perspective..."` |
| `app/video_factory/metadata_generator.py` | 117–120 | Fallback CTA Block | `"🔔 Subscribe for more {niche} content!"` |
| `app/video_factory/metadata_generator.py` | 122–134 | Fallback Tags | Static modifiers: `"{niche} explained"`, `"tips and tricks"`, `"how to"` |

**Category: B — Creative Content Generation (but already has AI primary path)**

This module already uses AI as the primary generation method (lines 72–99) with proper fallback. The hardcoded templates only activate when `_generate_ai_metadata()` fails. This is the **correct pattern** that other modules should adopt.

---

## SECTION 3 — AI Replacement Opportunities

### 3.1 — Title Generation (HIGH IMPACT)

**Why AI would improve it:** Titles are the single highest-impact user-visible output — they directly determine CTR (click-through rate) on YouTube. The current 25 static formulas produce repetitive, generic clickbait patterns. AI generation using Gemini Flash can produce titles that are:

- **Niche-aware** — financial content titles differ from gaming content titles in vocabulary and tone
- **Trend-responsive** — incorporating trending terms and current events from `trend_momentum` data
- **Competition-differentiated** — avoiding title patterns already saturated by competitors (using `competition_score`)
- **Format-appropriate** — faceless channels need different title styles than personality-driven channels

The AI service already generates video strategy ideas with CTR-optimized titles via `generate_video_strategy()` in `app/ai/service.py`, but the `TitleGenerationEngine` completely ignores this capability.

### 3.2 — Description Generation (HIGH IMPACT)

**Why AI would improve it:** YouTube descriptions affect search ranking (SEO) and viewer conversion. The current engine produces identical descriptions for every video — same intro phrasing, same generic chapters, same CTA. AI can generate:

- **Niche-specific SEO intros** that naturally incorporate target keywords
- **Contextual chapters** based on actual video structure (the pipeline already has `ScriptStructure` data)
- **Targeted CTAs** that match the niche's audience behavior (from `AudiencePersona`)
- **Specific affiliate/resource mentions** instead of placeholder `[Affiliate Link]` text

### 3.3 — Thumbnail Strategy (MEDIUM-HIGH IMPACT)

**Why AI would improve it:** The AI service already has `analyze_thumbnail_patterns()` which generates niche-specific color strategies, text overlay recommendations, and emotion styles. But the `ThumbnailStrategyGenerator` in `app/thumbnail_strategy/engine.py` ignores this — it uses a hardcoded 6-emotion mapping that produces the same layout for every video in a category. AI can generate:

- **Data-informed text overlays** using actual thumbnail pattern analysis from the pipeline
- **Niche-specific visual concepts** instead of generic emotion-to-layout mapping
- **Competitor-differentiated designs** based on `ThumbnailPatternResult` style groups

### 3.4 — Video Strategy / Blueprint Script Structure (MEDIUM IMPACT)

**Why AI would improve it:** The script structure in `blueprint.py` is a single fixed narrative template applied to all videos. A cooking tutorial needs a different hook and pacing than a finance exposé. AI can generate:

- **Topic-specific hooks** that match the content angle (educational vs. shock vs. storytelling)
- **Niche-appropriate CTAs** (e.g., "Sign up for my newsletter" for business vs. "Join the Discord" for gaming)
- **Angle-specific narrative arcs** (a "myth-busting" video needs a different structure than a "tutorial")
- **Channel name ideas** that reflect niche personality and audience expectations

### 3.5 — Monetization Copy (LOW-MEDIUM IMPACT)

**Why AI would improve it:** Digital product suggestions and lead magnet names use the same template for all niches. AI can generate niche-calibrated product ideas based on the audience's willingness to pay (informed by `RPM_ESTIMATES`) and the competitive landscape.

---

## SECTION 4 — Proposed AI Integration Points

### 4.1 — Title Generation Engine

**Current flow:**
```
TitleGenerationEngine.generate_titles(video)
  → random.choice(CURIOSITY_GAP_FORMULAS)
  → string.format(topic=..., year=...)
  → return dict of titles
```

**Proposed flow:**
```
TitleGenerationEngine.generate_titles(video, niche_score, trend_data)
  → try: ai_service.generate_titles(
        niche=niche_score.niche,
        topic=video.topic,
        keywords=video.target_keywords,
        trend_momentum=niche_score.trend_momentum,
        competition_score=niche_score.competition_score,
        ctr_potential=niche_score.ctr_potential,
    )
  → except: fallback to existing CURIOSITY_GAP_FORMULAS / KEYWORD_OPTIMIZED_FORMULAS
```

**New AI service function needed:** `generate_titles()` in `app/ai/service.py`
**New prompt template needed:** `app/ai/prompts/title_generation.py`

### 4.2 — Description Generation Engine

**Current flow:**
```
DescriptionGenerationEngine.generate(video, niche)
  → _generate_intro() → hardcoded paragraph
  → _suggest_chapters() → 9 fixed timestamps
  → _build_cta() → static emoji CTA
  → _build_affiliate_section() → placeholder links
```

**Proposed flow:**
```
DescriptionGenerationEngine.generate(video, niche, niche_score, script_structure)
  → try: ai_service.generate_description(
        niche=niche,
        topic=video.topic,
        keywords=video.target_keywords,
        script_structure=script_structure,  # for contextual chapters
        audience=audience_persona,
        monetization=monetization_strategy,  # for contextual affiliate text
    )
  → except: fallback to existing _generate_intro() / _build_cta()
```

**New AI service function needed:** `generate_description()` in `app/ai/service.py`
**New prompt template needed:** `app/ai/prompts/description_generation.py`

### 4.3 — Thumbnail Strategy Engine

**Current flow:**
```
ThumbnailStrategyGenerator.generate(video, niche)
  → _detect_primary_emotion() → keyword counting
  → EMOTION_VISUALS[emotion] → static dict
  → _generate_text_overlay() → power word extraction
  → _generate_layout() → static paragraph per emotion
```

**Proposed flow:**
```
ThumbnailStrategyGenerator.generate(video, niche, niche_score, thumbnail_patterns)
  → try: ai_service.generate_thumbnail_concepts(
        niche=niche,
        title=video.title,
        angle=video.angle,
        thumbnail_patterns=thumbnail_patterns,  # from ThumbnailAnalysisEngine
        competition_data=competition_analysis,
        ctr_potential=niche_score.ctr_potential,
    )
  → except: fallback to existing EMOTION_VISUALS mapping
```

**Existing AI service function:** `analyze_thumbnail_patterns()` in `app/ai/service.py` already exists but is not called by `ThumbnailStrategyGenerator`. A new `generate_thumbnail_concepts()` function should generate per-video concepts.
**New prompt template needed:** `app/ai/prompts/thumbnail_generation.py`

### 4.4 — Video Strategy Engine (Titles + Channel Concepts)

**Current flow:**
```
VideoStrategyEngine._create_title(niche, keyword, angle)
  → 15 hardcoded {key: template} mappings
  → string matching on angle

VideoStrategyEngine._generate_channel_names(niche)
  → 5 fixed "{Core} Explained" style patterns

VideoStrategyEngine._build_audience_persona(niche, keywords)
  → hardcoded age_range="18-45", generic pain points
```

**Proposed flow:**
```
VideoStrategyEngine._create_title(niche, keyword, angle, niche_score)
  → try: ai_service.generate_video_titles(
        niche=niche,
        keyword=keyword,
        angle=angle,
        trend_momentum=niche_score.trend_momentum,
        virality_score=niche_score.virality_score,
    )
  → except: fallback to existing template dict

VideoStrategyEngine._generate_channel_names(niche, niche_score)
  → try: AI-generated channel names
  → except: fallback to existing "{Core} Explained" patterns

VideoStrategyEngine._build_audience_persona(niche, keywords, niche_score)
  → try: AI-generated persona with niche-specific demographics
  → except: fallback to "18-45" generic persona
```

**Existing AI service function:** `generate_video_strategy()` already generates titles with concepts and audience hooks — this output can be adapted.

### 4.5 — Blueprint Assembler (Script Structure)

**Current flow:**
```
BlueprintAssembler._generate_script_structure(video, niche)
  → 6 hardcoded paragraph templates with {topic} interpolation
```

**Proposed flow:**
```
BlueprintAssembler._generate_script_structure(video, niche, niche_score)
  → try: ai_service.generate_script_structure(
        niche=niche,
        topic=video.topic,
        angle=video.angle,
        target_keywords=video.target_keywords,
        virality_score=niche_score.virality_score,
        faceless_viability=faceless_score,
    )
  → except: fallback to existing hardcoded ScriptStructure
```

**New AI service function needed:** `generate_script_structure()` in `app/ai/service.py`
**New prompt template needed:** `app/ai/prompts/script_generation.py`

### 4.6 — Monetization Engine (Copy Generation)

**Current flow:**
```
MonetizationEngine._suggest_digital_products(niche_text)
  → 5 fixed "{niche} eBook/Guide" patterns

MonetizationEngine._suggest_expansion(niche)
  → 4-phase roadmap, identical for all niches
```

**Proposed flow:**
```
MonetizationEngine._suggest_digital_products(niche_text, niche_score)
  → try: ai_service.generate_monetization_copy(
        niche=niche_text,
        rpm_estimate=estimated_rpm,
        competition_score=niche_score.competition_score,
        audience_persona=audience,
    )
  → except: fallback to existing templates
```

**New AI service function needed:** `generate_monetization_copy()` in `app/ai/service.py`

### Summary: Required New AI Functions and Prompts

| New Function | Target Model | Est. Latency | Priority |
|-------------|-------------|-------------|----------|
| `generate_titles()` | Flash | ~1s | HIGH |
| `generate_description()` | Flash | ~1.5s | HIGH |
| `generate_thumbnail_concepts()` | Flash | ~1s | HIGH |
| `generate_script_structure()` | Flash | ~1.5s | MEDIUM |
| `generate_monetization_copy()` | Flash | ~1s | LOW |

| New Prompt File | Purpose |
|----------------|---------|
| `app/ai/prompts/title_generation.py` | CTR-optimized title generation with niche context |
| `app/ai/prompts/description_generation.py` | SEO YouTube description with chapters and CTAs |
| `app/ai/prompts/thumbnail_generation.py` | Per-video thumbnail visual concepts |
| `app/ai/prompts/script_generation.py` | Niche-specific narrative structure |
| `app/ai/prompts/monetization_copy.py` | Digital product and expansion strategy copy |

---

## SECTION 5 — Risk Assessment

### 5.1 — Pipeline Performance Impact

| Concern | Assessment | Mitigation |
|---------|-----------|------------|
| **Added latency from AI calls** | Each Gemini Flash call adds ~1–2s. The blueprint assembly loop generates titles + descriptions + thumbnails + scripts per video. For 10 videos × 5 niches = 50 AI calls. | Use `asyncio.gather()` to parallelize AI calls within each niche. Batch multiple videos into a single prompt where possible. The pipeline already supports bounded concurrency via `Semaphore`. |
| **Pipeline already runs 11 steps** | The blueprint assembly happens at Steps 9–10, which already use `run_in_executor()`. Adding AI calls here extends total pipeline time. | AI generation calls should replace the synchronous template logic — net latency increase is ~2–5s per niche (Flash calls in parallel), not 50× serial. |
| **Cost** | Gemini Flash pricing is low (~$0.075 per 1M input tokens). For a full analysis run: ~50 calls × ~500 tokens = $0.002 per pipeline run. | Negligible cost. Use Flash for all creative generation (Pro only for deep analysis). |

### 5.2 — API Latency Impact

| Concern | Assessment | Mitigation |
|---------|-----------|------------|
| **Single-video API endpoints** | If `POST /api/strategy/{niche}` calls AI for each video idea synchronously, response time increases from ~50ms to ~2s. | Cache AI-generated content in `ai_insights` table (24h TTL, already implemented). Second request hits cache. |
| **Report generation** | `POST /api/analyze` already takes 30–90 seconds for a full pipeline run. Adding AI creative generation extends this. | AI creative calls can run in parallel with the existing AI enhancement step (Step 8b). Net wall-clock impact: ~3–5s additional. |

### 5.3 — System Stability Impact

| Concern | Assessment | Mitigation |
|---------|-----------|------------|
| **Vertex AI outage** | If Google Vertex is down, all creative generation fails. | **Mandatory fallback pattern.** Every AI call must have a `try/except` that falls back to the existing hardcoded templates. The `metadata_generator.py` already implements this pattern correctly. |
| **Quota exhaustion** | High pipeline usage could hit Vertex API rate limits. | The system already has retry with exponential backoff on AI calls (3 retries). Add rate-limit detection to fallback triggers. |
| **Malformed AI responses** | Gemini may return incomplete or malformed JSON. | The `client.py` already strips markdown fences and handles malformed responses. Each creative generation function should validate the response structure before using it. |
| **Test stability** | 291 tests currently pass. AI-dependent tests would become flaky. | All tests should mock AI calls. New tests should verify both AI path and fallback path. Keep existing template tests as fallback-path tests. |

### 5.4 — Content Quality Risk

| Concern | Assessment | Mitigation |
|---------|-----------|------------|
| **AI hallucination** | Titles or descriptions could include fabricated claims, inappropriate language, or factual errors. | Prompt engineering with strict constraints. Post-generation validation (e.g., title length limits, keyword presence checks). |
| **Loss of consistency** | Current templates produce predictable, consistent output. AI may produce varied quality. | Structured JSON output format (already proven in existing AI prompts). Temperature control (0.5–0.7 for creative, lower for descriptions). |
| **Regression in baseline quality** | If AI generates worse titles than templates, user experience degrades. | A/B capability: store both AI-generated and template-generated versions. Allow users to select preference. |

---

## SECTION 6 — Refactor Priority List

### HIGH — User-Visible Outputs (Directly Impacts YouTube Performance)

| Priority | Module | File | Change | Effort |
|----------|--------|------|--------|--------|
| **H1** | Title Generation | `app/title_generation/engine.py` | Replace `random.choice(FORMULAS)` with `ai_service.generate_titles()`, keep templates as fallback | Medium |
| **H2** | Description Generation | `app/description_generation/engine.py` | Replace all 5 `_generate_*` / `_build_*` methods with single `ai_service.generate_description()` call, keep methods as fallback | Medium |
| **H3** | Thumbnail Strategy | `app/thumbnail_strategy/engine.py` | Replace `EMOTION_VISUALS` mapping with `ai_service.generate_thumbnail_concepts()`, keep emotion mapping as fallback | Medium |
| **H4** | Video Strategy Titles | `app/video_strategy/engine.py` `_create_title()` | Replace 15-template dict with AI title generation, keep dict as fallback | Low–Medium |

### MEDIUM — Strategy Generation

| Priority | Module | File | Change | Effort |
|----------|--------|------|--------|--------|
| **M1** | Script Structure | `app/video_strategy/blueprint.py` `_generate_script_structure()` | Replace 6 hardcoded sections with AI-generated structure per angle | Medium |
| **M2** | Channel Names | `app/video_strategy/engine.py` `_generate_channel_names()` | Replace 5 fixed patterns with AI-generated names factoring niche personality | Low |
| **M3** | Audience Persona | `app/video_strategy/engine.py` `_build_audience_persona()` | Replace hardcoded `"18-45"` and generic pain points with AI persona | Low |
| **M4** | Positioning Statement | `app/video_strategy/engine.py` `_generate_positioning()` | Replace generic statement with AI-generated positioning | Low |

### LOW — Internal Reports / Supplementary Copy

| Priority | Module | File | Change | Effort |
|----------|--------|------|--------|--------|
| **L1** | Monetization Products | `app/monetization_engine/engine.py` `_suggest_digital_products()` | Replace 5 fixed product name patterns with AI-generated suggestions | Low |
| **L2** | Monetization Lead Magnets | `app/monetization_engine/engine.py` `_suggest_lead_magnets()` | Replace 4 fixed lead magnet titles with AI-generated suggestions | Low |
| **L3** | Monetization Expansion | `app/monetization_engine/engine.py` `_suggest_expansion()` | Replace 4-phase fixed roadmap with AI-generated niche-specific plan | Low |
| **L4** | Report Narrative | `app/report_generation/engine.py` | Mostly data-driven rendering (Category A) — no AI needed except optional executive summary | Very Low |

### DO NOT MODIFY (Deterministic Engines — Category A)

| Module | Reason |
|--------|--------|
| `app/ranking_engine/` | Weighted composite scoring formula — deterministic |
| `app/ctr_prediction/` | Power-word and number-pattern scoring — deterministic¹ |
| `app/virality_prediction/` | Statistical virality scoring — deterministic |
| `app/competition_analysis/` | YouTube search data analysis — deterministic |
| `app/faceless_viability/` | Keyword-pattern format detection — deterministic |
| `app/topic_velocity/` | Time-series growth rate calculation — deterministic |
| `app/niche_clustering/` | TF-IDF + Agglomerative clustering — deterministic |
| `app/trend_discovery/` | Google Trends data fetch + scoring — deterministic |
| `app/compilation_engine/` | Segment detection + energy arc structure — deterministic² |
| `app/video_factory/timeline_engine.py` | FFmpeg command generation — deterministic |
| `app/video_factory/video_assembler.py` | FFmpeg concat encoding — deterministic |

¹ `ctr_prediction/engine.py` lines 103–113 contain title templates used for CTR *scoring benchmark*, not as user-visible output. These must remain deterministic.

² `compilation_engine/engine.py` `_ARC_TEMPLATE` (lines 219–230) is an energy-arc ordering pattern (hook→build→surprise→payoff), not creative content. This must remain deterministic.

---

## Recommended Implementation Order

```
Phase 1 (HIGH items) ✅ COMPLETE
├── ✅ Create app/ai/prompts/title_generation.py
├── ✅ Create app/ai/prompts/description_generation.py
├── ✅ Create app/ai/prompts/thumbnail_generation.py
├── ✅ Add generate_titles() to app/ai/service.py
├── ✅ Add generate_description() to app/ai/service.py
├── ✅ Add generate_thumbnail_concepts() to app/ai/service.py
├── ✅ Refactor TitleGenerationEngine with AI + fallback
├── ✅ Refactor DescriptionGenerationEngine with AI + fallback
├── ✅ Refactor ThumbnailStrategyGenerator with AI + fallback
├── ✅ Refactor VideoStrategyEngine with AI + fallback (titles, ideas, channel concept)
└── ✅ Add tests for both AI and fallback paths

Phase 2 (MEDIUM items) ✅ COMPLETE
├── ✅ Create app/ai/prompts/script_generation.py
├── ✅ Create app/ai/prompts/video_strategy_generation.py (channel_concept_prompt)
├── ✅ Add generate_script_structure() to app/ai/service.py
├── ✅ Add generate_channel_concept_ai() to app/ai/service.py
├── ✅ Add generate_video_ideas_ai() to app/ai/service.py
├── ✅ Refactor BlueprintAssembler._generate_script_structure()
├── ✅ Refactor _generate_channel_names(), _build_audience_persona(), _generate_positioning()
└── ✅ Add tests

Phase 3 (LOW items) ✅ COMPLETE
├── ✅ Refactor MonetizationEngine with inline AI prompt + fallback
└── ✅ Add tests
```

### Reference Pattern: Correct Fallback Implementation

`app/video_factory/metadata_generator.py` already implements the correct AI-with-fallback pattern that all refactored modules should follow:

```python
async def _generate_ai_metadata(self, niche, concept, script) -> VideoMetadata:
    try:
        client = get_ai_client()
        prompt = "..."
        result = client.generate_json(prompt, use_pro=True, temperature=0.5)
        if result and isinstance(result, dict):
            return VideoMetadata(...)  # AI-generated
    except Exception as exc:
        logger.warning("metadata_ai_failed", error=str(exc))

    # Fallback metadata
    return self._fallback_metadata(niche, concept, script)
```

### Context Data to Pass to AI

Every AI generation call should include the following pipeline context (where available):

| Context Field | Source | Purpose |
|---------------|--------|---------|
| `niche` | `NicheScore.niche` | Primary topic context |
| `keywords` | `NicheScore.keywords` | SEO targeting |
| `trend_momentum` | `NicheScore.trend_momentum` | Trend-responsive content |
| `competition_score` | `NicheScore.competition_score` | Differentiation strategy |
| `virality_score` | `NicheScore.virality_score` | Viral format selection |
| `ctr_potential` | `NicheScore.ctr_potential` | Title optimization signals |
| `demand_score` | `NicheScore.demand_score` | Content demand calibration |
| `faceless_viability` | `FacelessViability` | Production format constraints |
| `topic_velocity_score` | `NicheScore.topic_velocity_score` | Trending topic emphasis |
| `viral_opportunity_score` | `NicheScore.viral_opportunity_score` | Anomaly-informed content angles |

---

## SECTION 7 — Implementation Summary

### New Prompt Templates Created

| File | Functions | Purpose |
|------|-----------|----------|
| `app/ai/prompts/title_generation.py` | `title_generation_prompt()` | CTR-optimized titles with curiosity gap, SEO, and alternative variants |
| `app/ai/prompts/description_generation.py` | `description_generation_prompt()` | SEO descriptions with intro, chapters, CTAs, and affiliate positioning |
| `app/ai/prompts/thumbnail_generation.py` | `thumbnail_concept_prompt()` | Visual thumbnail concepts with emotion, contrast, color, and layout |
| `app/ai/prompts/video_strategy_generation.py` | `video_ideas_prompt()`, `channel_concept_prompt()` | Video ideas with titles/angles, channel names/positioning/audience |
| `app/ai/prompts/script_generation.py` | `script_structure_prompt()` | Script beat sheets with hooks, retention loops, and CTA placement |

### New Service Functions Added to `app/ai/service.py`

| Function | Model | Caching | Purpose |
|----------|-------|---------|---------|
| `generate_titles()` | Flash | ✅ 24h | Async title generation for API/pipeline use |
| `generate_description()` | Flash | ✅ 24h | Async description generation |
| `generate_thumbnail_concepts()` | Flash | ✅ 24h | Async thumbnail concept generation |
| `generate_video_ideas_ai()` | Flash | ✅ 24h | Async video idea generation |
| `generate_channel_concept_ai()` | Flash | ✅ 24h | Async channel concept generation |
| `generate_script_structure()` | Flash | ✅ 24h | Async script structure generation |

### Engine Refactor Pattern

All 6 refactored engines follow the same pattern established by `metadata_generator.py`:

```python
def generate(self, video, niche):
    # AI-first path
    ai_result = self._try_ai_generation(video, niche)
    if ai_result:
        return ai_result
    # Template fallback
    return self._fallback_generation(video, niche)

def _try_ai_generation(self, video, niche):
    try:
        from app.ai.client import get_ai_client
        from app.ai.prompts.<module> import <prompt_function>

        client = get_ai_client()
        if not client.available:
            return None

        prompt = <prompt_function>(niche=..., topic=..., ...)
        result = client.generate_json(prompt, use_pro=False)

        if result and isinstance(result, dict) and <validate_keys>:
            return <build_result>(result)
    except Exception as exc:
        logger.warning("ai_generation_failed", error=str(exc))
    return None
```

Key design decisions:
- **Sync `client.generate_json()`** in engines (not async service) to avoid sync/async boundary issues
- **Lazy imports** inside `_try_ai_*` methods — AI client is only imported when called
- **Graceful degradation** — `client.available` check + try/except ensures templates activate when AI is unavailable
- **All original templates preserved** as fallback methods — zero regression risk

### Test Coverage Added

| Test File | New Tests | Coverage |
|-----------|-----------|----------|
| `tests/test_ai.py` | 6 prompt template tests | Validates all 5 new prompt templates produce correct output keys |
| `tests/test_ai.py` | 8 service function tests | Mocked async tests for all 6 new service functions + edge cases |
| `tests/test_strategy.py` | 10 AI-first + fallback tests | Verifies AI path returns AI content, fallback path returns templates |

**Total test suite: 315 passing (291 original + 24 new)**

---

*Audit completed 2026-03-06. Implementation completed 2026-03-06.*
