"""Tests for strategy generators."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.video_strategy.engine import VideoStrategyEngine
from app.thumbnail_strategy.engine import ThumbnailStrategyGenerator
from app.title_generation.engine import TitleGenerationEngine
from app.description_generation.engine import DescriptionGenerationEngine
from app.monetization_engine.engine import MonetizationEngine
from app.video_strategy.blueprint import BlueprintAssembler
from app.core.models import NicheScore, VideoIdea, FacelessViability, FacelessFormat
from app.config.settings import reset_settings, load_settings


def setup_module() -> None:
    reset_settings()
    load_settings()


# ── Video Strategy ─────────────────────────────────────────────────────────────

def test_channel_concept_generation() -> None:
    engine = VideoStrategyEngine()
    niche = NicheScore(
        niche="ai tools",
        demand_score=80,
        competition_score=40,
        trend_momentum=75,
        overall_score=72,
        rank=1,
        keywords=["ai tools", "chatgpt", "ai automation"],
    )
    concept = engine.generate_channel_concept(niche)
    assert len(concept.channel_name_ideas) > 0
    assert concept.estimated_rpm > 0
    assert concept.time_to_monetization_months > 0


def test_video_ideas_generation() -> None:
    engine = VideoStrategyEngine()
    niche = NicheScore(
        niche="personal finance",
        demand_score=85,
        overall_score=78,
        rank=1,
        keywords=["budgeting", "investing", "saving money"],
    )
    ideas = engine.generate_video_ideas(niche, count=10)
    assert len(ideas) == 10
    assert all(idea.title for idea in ideas)


# ── Thumbnail Strategy ─────────────────────────────────────────────────────────

def test_thumbnail_generation() -> None:
    gen = ThumbnailStrategyGenerator()
    video = VideoIdea(
        title="The Shocking Truth About AI",
        topic="artificial intelligence",
        angle="Hidden secrets / lesser-known facts",
    )
    thumbnail = gen.generate(video, "ai")
    assert thumbnail.emotion_trigger
    assert thumbnail.color_palette
    assert thumbnail.layout_concept


def test_thumbnail_batch() -> None:
    gen = ThumbnailStrategyGenerator()
    videos = [
        VideoIdea(title="Test 1", topic="test", angle="tutorial"),
        VideoIdea(title="Test 2", topic="test", angle="secrets"),
    ]
    results = gen.generate_batch(videos, "test")
    assert len(results) == 2


# ── Title Generation ───────────────────────────────────────────────────────────

def test_title_generation() -> None:
    gen = TitleGenerationEngine()
    video = VideoIdea(
        title="AI Tools Guide",
        topic="ai tools",
        target_keywords=["ai", "tools", "automation"],
    )
    titles = gen.generate_titles(video)
    assert "curiosity_gap_headline" in titles
    assert "keyword_optimized_title" in titles
    assert len(titles["alternative_titles"]) > 0


# ── Description Generation ─────────────────────────────────────────────────────

def test_description_generation() -> None:
    gen = DescriptionGenerationEngine()
    video = VideoIdea(
        title="Python Tutorial",
        topic="python",
        target_keywords=["python", "programming", "tutorial"],
    )
    desc = gen.generate(video, "programming")
    assert desc.intro_paragraph
    assert len(desc.keyword_block) > 0
    assert len(desc.chapters) > 0


# ── Monetization ───────────────────────────────────────────────────────────────

def test_monetization_strategy() -> None:
    engine = MonetizationEngine()
    niche = NicheScore(
        niche="technology",
        overall_score=75,
        rank=1,
        keywords=["tech", "gadgets"],
    )
    strategy = engine.generate_strategy(niche)
    assert len(strategy.affiliate_products) > 0
    assert len(strategy.digital_products) > 0
    assert strategy.expansion_strategy


# ── Blueprint Assembler ────────────────────────────────────────────────────────

def test_blueprint_assembly() -> None:
    assembler = BlueprintAssembler()
    video = VideoIdea(
        title="AI Tools Guide",
        topic="ai tools",
        angle="tutorial",
        target_keywords=["ai", "tools"],
    )
    niche = NicheScore(
        niche="ai tools",
        overall_score=75,
        rank=1,
        keywords=["ai", "tools"],
    )
    blueprint = assembler.assemble_blueprint(video, niche)
    assert blueprint.curiosity_gap_headline
    assert blueprint.thumbnail.emotion_trigger
    assert blueprint.script_structure.hook
    assert blueprint.low_cost_production.stock_footage_libraries
    assert blueprint.seo_description.intro_paragraph
    assert blueprint.monetization.affiliate_products


# ══════════════════════════════════════════════════════════════════════════════
#  AI-first + Fallback tests
# ══════════════════════════════════════════════════════════════════════════════


def _mock_ai_available(generate_json_return):
    """Create a mock client that returns the given value from generate_json."""
    client = MagicMock()
    client.available = True
    client.generate_json.return_value = generate_json_return
    return client


def _mock_ai_unavailable():
    """Create a mock client that is not available."""
    client = MagicMock()
    client.available = False
    return client


# ── Title AI-first tests ───────────────────────────────────────────────────

def test_title_generation_uses_ai_when_available() -> None:
    gen = TitleGenerationEngine()
    video = VideoIdea(
        title="AI Tools Guide",
        topic="ai tools",
        target_keywords=["ai", "tools"],
    )
    mock_client = _mock_ai_available({
        "curiosity_gap_headline": "AI Secret Nobody Tells You",
        "keyword_optimized_title": "AI Tools Complete Guide 2026",
        "alternative_titles": ["Why AI Will Change Everything"],
    })
    with patch("app.ai.client.get_ai_client", return_value=mock_client):
        titles = gen.generate_titles(video)
    assert titles.get("_ai_generated") is True
    assert titles["curiosity_gap_headline"] == "AI Secret Nobody Tells You"


def test_title_generation_fallback_on_ai_failure() -> None:
    gen = TitleGenerationEngine()
    video = VideoIdea(
        title="AI Tools Guide",
        topic="ai tools",
        target_keywords=["ai", "tools"],
    )
    with patch("app.ai.client.get_ai_client", return_value=_mock_ai_unavailable()):
        titles = gen.generate_titles(video)
    assert "_ai_generated" not in titles
    assert titles["curiosity_gap_headline"]  # still has a title from templates


# ── Thumbnail AI-first tests ──────────────────────────────────────────────

def test_thumbnail_uses_ai_when_available() -> None:
    gen = ThumbnailStrategyGenerator()
    video = VideoIdea(title="Shocking Truth", topic="ai", angle="secrets")
    mock_client = _mock_ai_available({
        "emotion_trigger": "shock",
        "contrast_strategy": "Bold red on black",
        "visual_focal_point": "Dramatic reveal",
        "text_overlay": "SHOCKING",
        "color_palette": ["#ff0000", "#000000"],
        "layout_concept": "Full bleed dramatic layout",
    })
    with patch("app.ai.client.get_ai_client", return_value=mock_client):
        concept = gen.generate(video, "technology")
    assert concept.emotion_trigger == "shock"
    assert concept.layout_concept == "Full bleed dramatic layout"


def test_thumbnail_fallback_on_ai_failure() -> None:
    gen = ThumbnailStrategyGenerator()
    video = VideoIdea(title="Shocking Truth", topic="ai", angle="secrets")
    with patch("app.ai.client.get_ai_client", return_value=_mock_ai_unavailable()):
        concept = gen.generate(video, "technology")
    assert concept.emotion_trigger  # still has an emotion from keyword detection
    assert concept.color_palette


# ── Description AI-first tests ────────────────────────────────────────────

def test_description_uses_ai_when_available() -> None:
    gen = DescriptionGenerationEngine()
    video = VideoIdea(
        title="Python Tutorial",
        topic="python",
        target_keywords=["python", "coding"],
    )
    mock_client = _mock_ai_available({
        "intro_paragraph": "AI-generated intro about Python",
        "keyword_block": ["python", "coding", "tutorial"],
        "chapters": ["0:00 Introduction", "2:00 Setup"],
        "cta_structure": "Subscribe for more!",
        "affiliate_positioning": "Resources used in this tutorial",
    })
    with patch("app.ai.client.get_ai_client", return_value=mock_client):
        desc = gen.generate(video, "programming")
    assert desc.intro_paragraph == "AI-generated intro about Python"


def test_description_fallback_on_ai_failure() -> None:
    gen = DescriptionGenerationEngine()
    video = VideoIdea(
        title="Python Tutorial",
        topic="python",
        target_keywords=["python", "coding"],
    )
    with patch("app.ai.client.get_ai_client", return_value=_mock_ai_unavailable()):
        desc = gen.generate(video, "programming")
    assert "dive deep" in desc.intro_paragraph  # fallback template text


# ── Blueprint script structure AI-first tests ─────────────────────────────

def test_blueprint_script_uses_ai_when_available() -> None:
    assembler = BlueprintAssembler()
    video = VideoIdea(title="Test", topic="ai", angle="tutorial", target_keywords=["ai"])
    niche = NicheScore(niche="ai", overall_score=75, rank=1, keywords=["ai"])

    mock_client = MagicMock()
    mock_client.available = True
    mock_client.generate_json.return_value = {
        "hook": "AI-generated hook",
        "retention_pattern_interrupt": "Pattern interrupt",
        "story_progression": "Journey arc",
        "mid_video_curiosity_loop": "Tease",
        "final_payoff": "Payoff",
        "cta_placement": "Subscribe",
    }
    # Patch at client level for script, let other engines use fallback
    with patch("app.ai.client.get_ai_client", return_value=mock_client):
        script = assembler._generate_script_structure(video, "ai")
    assert script.hook == "AI-generated hook"


def test_blueprint_script_fallback_on_ai_failure() -> None:
    assembler = BlueprintAssembler()
    video = VideoIdea(title="Test", topic="ai", angle="tutorial", target_keywords=["ai"])

    with patch("app.ai.client.get_ai_client", return_value=_mock_ai_unavailable()):
        script = assembler._generate_script_structure(video, "ai")
    assert "bold, surprising statement" in script.hook  # fallback template


# ── Monetization AI-first tests ───────────────────────────────────────────

def test_monetization_uses_ai_when_available() -> None:
    engine = MonetizationEngine()
    niche = NicheScore(
        niche="technology",
        overall_score=75,
        rank=1,
        keywords=["tech"],
    )
    mock_client = _mock_ai_available({
        "digital_products": ["AI Course", "Tech Template Pack"],
        "lead_magnets": ["Free AI Starter Guide"],
        "expansion_strategy": "AI-powered Phase 1-4 plan",
    })
    with patch("app.ai.client.get_ai_client", return_value=mock_client):
        strategy = engine.generate_strategy(niche)
    assert "AI Course" in strategy.digital_products
    assert "AI-powered Phase 1-4 plan" in strategy.expansion_strategy


def test_monetization_fallback_on_ai_failure() -> None:
    engine = MonetizationEngine()
    niche = NicheScore(
        niche="technology",
        overall_score=75,
        rank=1,
        keywords=["tech"],
    )
    with patch("app.ai.client.get_ai_client", return_value=_mock_ai_unavailable()):
        strategy = engine.generate_strategy(niche)
    assert len(strategy.digital_products) > 0  # fallback templates
    assert "Phase 1" in strategy.expansion_strategy  # fallback phased plan
