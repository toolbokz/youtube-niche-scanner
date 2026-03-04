"""Tests for strategy generators."""
from __future__ import annotations

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
