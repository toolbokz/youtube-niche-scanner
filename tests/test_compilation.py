"""Tests for the Compilation Video Intelligence engine."""
from __future__ import annotations

import math
from unittest.mock import AsyncMock, patch

import pytest

from app.config.settings import reset_settings, load_settings
from app.compilation_engine.schemas import (
    CompilationSegment,
    CompilationSourceVideo,
    CompilationStrategy,
    CompilationStructureItem,
    EditingGuidance,
    EnergyLevel,
    FinalVideoConcept,
    SegmentType,
)
from app.compilation_engine.engine import (
    CompilationAnalyzer,
    _CompilationStrategyBuilder,
    _SegmentDetector,
    _VideoSourceFinder,
    _estimate_age_days,
    _format_ts,
)
from app.core.models import SearchResult


def setup_module() -> None:
    reset_settings()
    load_settings()


# ── Helpers ────────────────────────────────────────────────────────────────────


def _fake_search_result(
    video_id: str = "vid1",
    title: str = "Test Compilation Video",
    channel_name: str = "TestChannel",
    channel_subs: int = 5_000,
    views: int = 200_000,
    duration: int = 300,
    published: str = "3 days ago",
) -> SearchResult:
    return SearchResult(
        video_id=video_id,
        title=title,
        channel_name=channel_name,
        channel_subscribers=channel_subs,
        view_count=views,
        duration_seconds=duration,
        published_date=published,
    )


def _make_source_video(
    video_id: str = "src1",
    title: str = "Funny Cats Ultimate",
    views: int = 500_000,
    duration: int = 600,
    engagement: float = 75.0,
) -> CompilationSourceVideo:
    return CompilationSourceVideo(
        video_id=video_id,
        title=title,
        channel_name="SomeChannel",
        view_count=views,
        duration_seconds=duration,
        published_date="5 days ago",
        url=f"https://www.youtube.com/watch?v={video_id}",
        engagement_score=engagement,
        relevance_score=engagement * 0.8,
    )


# ═══════════════════════════════════════════════════════════════════════
#  Schema tests
# ═══════════════════════════════════════════════════════════════════════


class TestSchemas:
    """Verify Pydantic models instantiate and serialise correctly."""

    def test_compilation_source_video_defaults(self) -> None:
        v = CompilationSourceVideo()
        assert v.video_id == ""
        assert v.engagement_score == 0.0

    def test_compilation_segment_defaults(self) -> None:
        s = CompilationSegment()
        assert s.energy_level == EnergyLevel.MEDIUM
        assert s.timestamp_start == "0:00"

    def test_compilation_structure_item_defaults(self) -> None:
        item = CompilationStructureItem()
        assert item.position == 0
        assert item.segment_type == SegmentType.REVEAL
        assert item.segment is None

    def test_editing_guidance_defaults(self) -> None:
        e = EditingGuidance()
        assert e.transition_style == "smooth crossfade"
        assert isinstance(e.text_overlays, list)

    def test_final_video_concept_defaults(self) -> None:
        c = FinalVideoConcept()
        assert c.estimated_duration_minutes == 10.0
        assert c.tags == []

    def test_compilation_strategy_defaults(self) -> None:
        s = CompilationStrategy()
        assert s.niche == ""
        assert s.compilation_score == 0.0

    def test_round_trip_serialisation(self) -> None:
        """model → dict → model should be lossless."""
        seg = CompilationSegment(
            source_video_id="v1",
            source_video_title="Test",
            timestamp_start="1:00",
            timestamp_end="1:30",
            duration_seconds=30,
            energy_level=EnergyLevel.HIGH,
        )
        data = seg.model_dump(mode="json")
        restored = CompilationSegment(**data)
        assert restored.energy_level == EnergyLevel.HIGH
        assert restored.timestamp_start == "1:00"


# ═══════════════════════════════════════════════════════════════════════
#  Utility helpers
# ═══════════════════════════════════════════════════════════════════════


class TestUtilities:
    def test_estimate_age_days_recent(self) -> None:
        assert _estimate_age_days("5 hours ago") == 0

    def test_estimate_age_days_days(self) -> None:
        assert _estimate_age_days("3 days ago") == 3

    def test_estimate_age_days_weeks(self) -> None:
        assert _estimate_age_days("2 weeks ago") == 14

    def test_estimate_age_days_months(self) -> None:
        assert _estimate_age_days("1 month ago") == 30

    def test_estimate_age_days_years(self) -> None:
        assert _estimate_age_days("1 year ago") == 365

    def test_estimate_age_days_yesterday(self) -> None:
        assert _estimate_age_days("yesterday") == 1

    def test_estimate_age_days_empty(self) -> None:
        assert _estimate_age_days("") is None

    def test_estimate_age_days_garbage(self) -> None:
        assert _estimate_age_days("no date here") is None

    def test_format_ts_zero(self) -> None:
        assert _format_ts(0) == "0:00"

    def test_format_ts_seconds(self) -> None:
        assert _format_ts(65) == "1:05"

    def test_format_ts_minutes(self) -> None:
        assert _format_ts(300) == "5:00"


# ═══════════════════════════════════════════════════════════════════════
#  VideoSourceFinder
# ═══════════════════════════════════════════════════════════════════════


class TestVideoSourceFinder:
    def _make_finder(self, results: list[SearchResult] | None = None) -> _VideoSourceFinder:
        mock_yt = AsyncMock()
        mock_yt.search = AsyncMock(return_value=results or [])
        return _VideoSourceFinder(mock_yt)

    @pytest.mark.asyncio
    async def test_find_sources_empty(self) -> None:
        finder = self._make_finder([])
        sources = await finder.find_sources("test", [])
        assert sources == []

    @pytest.mark.asyncio
    async def test_find_sources_deduplicates(self) -> None:
        r = _fake_search_result(video_id="v1", duration=300)
        finder = self._make_finder([r, r, r])
        sources = await finder.find_sources("test", ["kw1"])
        video_ids = [s.video_id for s in sources]
        assert video_ids.count("v1") == 1

    @pytest.mark.asyncio
    async def test_find_sources_filters_short_videos(self) -> None:
        short = _fake_search_result(video_id="short", duration=30)
        long = _fake_search_result(video_id="long", duration=300)
        finder = self._make_finder([short, long])
        sources = await finder.find_sources("test", [])
        assert len(sources) == 1
        assert sources[0].video_id == "long"

    @pytest.mark.asyncio
    async def test_find_sources_scores(self) -> None:
        r = _fake_search_result(video_id="v1", views=1_000_000, channel_subs=1_000, duration=600)
        finder = self._make_finder([r])
        sources = await finder.find_sources("niche", [])
        assert len(sources) == 1
        assert sources[0].engagement_score > 0
        assert sources[0].url.endswith("v1")

    def test_score_video_engagement(self) -> None:
        r = _fake_search_result(views=2_000_000, channel_subs=500, duration=600, published="1 day ago")
        scored = _VideoSourceFinder._score_video(r)
        assert scored.engagement_score > 50

    def test_score_video_length_bonus(self) -> None:
        """Videos 3-20 min should score higher than very short ones."""
        short_r = _fake_search_result(views=100_000, channel_subs=10_000, duration=90)
        long_r = _fake_search_result(views=100_000, channel_subs=10_000, duration=600)
        short_score = _VideoSourceFinder._score_video(short_r)
        long_score = _VideoSourceFinder._score_video(long_r)
        assert long_score.engagement_score >= short_score.engagement_score


# ═══════════════════════════════════════════════════════════════════════
#  SegmentDetector
# ═══════════════════════════════════════════════════════════════════════


class TestSegmentDetector:
    def test_detect_segments_empty(self) -> None:
        segs = _SegmentDetector.detect_segments([])
        assert segs == []

    def test_detect_segments_produces_clips(self) -> None:
        videos = [_make_source_video(video_id=f"v{i}") for i in range(3)]
        segs = _SegmentDetector.detect_segments(videos)
        assert len(segs) > 0
        for seg in segs:
            assert seg.source_video_id in [f"v{i}" for i in range(3)]
            assert seg.duration_seconds > 0

    def test_detect_segments_max_per_source(self) -> None:
        videos = [_make_source_video(video_id="v1", duration=600)]
        segs = _SegmentDetector.detect_segments(videos)
        assert len(segs) <= 2  # _SEGMENTS_PER_SOURCE = 2

    def test_infer_energy_high_keyword(self) -> None:
        energy = _SegmentDetector._infer_energy("INSANE Cat Moments", 0, 2)
        assert energy == EnergyLevel.HIGH

    def test_infer_energy_last_segment_climax(self) -> None:
        energy = _SegmentDetector._infer_energy("Ordinary Video", 1, 2)
        assert energy == EnergyLevel.CLIMAX

    def test_infer_theme_extracts_words(self) -> None:
        theme = _SegmentDetector._infer_theme("Best Cat Fails 2024")
        assert "Best" in theme or "Cat" in theme


# ═══════════════════════════════════════════════════════════════════════
#  CompilationStrategyBuilder
# ═══════════════════════════════════════════════════════════════════════


class TestCompilationStrategyBuilder:
    def _make_segments(self, count: int = 10) -> list[CompilationSegment]:
        energies = [EnergyLevel.LOW, EnergyLevel.MEDIUM, EnergyLevel.HIGH, EnergyLevel.CLIMAX]
        return [
            CompilationSegment(
                source_video_id=f"v{i}",
                source_video_title=f"Video {i}",
                duration_seconds=30,
                energy_level=energies[i % len(energies)],
            )
            for i in range(count)
        ]

    def test_build_structure_empty(self) -> None:
        structure = _CompilationStrategyBuilder.build_structure([])
        assert structure == []

    def test_build_structure_has_arc(self) -> None:
        segs = self._make_segments(10)
        structure = _CompilationStrategyBuilder.build_structure(segs)
        assert len(structure) > 0
        # First item should be an intro hook
        assert structure[0].segment_type == SegmentType.INTRO_HOOK
        # Should have sequential positions
        positions = [s.position for s in structure]
        assert positions == sorted(positions)
        assert positions[0] == 1

    def test_build_structure_includes_leftover(self) -> None:
        """More segments than arc slots → leftover added as reveals."""
        segs = self._make_segments(15)
        structure = _CompilationStrategyBuilder.build_structure(segs)
        types = [s.segment_type for s in structure]
        assert SegmentType.REVEAL in types

    def test_editing_guidance_generation(self) -> None:
        structure = [
            CompilationStructureItem(position=1, segment=CompilationSegment(duration_seconds=30)),
            CompilationStructureItem(position=2, segment=CompilationSegment(duration_seconds=45)),
        ]
        guidance = _CompilationStrategyBuilder.generate_editing_guidance("tech", structure)
        assert isinstance(guidance, EditingGuidance)
        assert len(guidance.text_overlays) > 0
        assert "tech" in guidance.background_music_style.lower()

    def test_video_concept_generation(self) -> None:
        sources = [_make_source_video(video_id=f"v{i}", views=100_000 * (i + 1)) for i in range(5)]
        structure = [
            CompilationStructureItem(position=i + 1, duration_seconds=30, segment=CompilationSegment())
            for i in range(5)
        ]
        concept = _CompilationStrategyBuilder.generate_video_concept("funny cats", structure, sources)
        assert isinstance(concept, FinalVideoConcept)
        assert "funny cats" in concept.title.lower() or "5" in concept.title
        assert concept.estimated_duration_minutes > 0
        assert len(concept.tags) > 0


# ═══════════════════════════════════════════════════════════════════════
#  CompilationAnalyzer (integration)
# ═══════════════════════════════════════════════════════════════════════


class TestCompilationAnalyzer:
    def _make_analyzer(self, results: list[SearchResult] | None = None) -> CompilationAnalyzer:
        mock_yt = AsyncMock()
        mock_yt.search = AsyncMock(return_value=results or [])
        return CompilationAnalyzer(mock_yt)

    @pytest.mark.asyncio
    async def test_analyze_empty(self) -> None:
        analyzer = self._make_analyzer([])
        strategy = await analyzer.analyze("empty niche", [], use_ai=False)
        assert isinstance(strategy, CompilationStrategy)
        assert strategy.compilation_score == 0.0
        assert strategy.source_videos == []

    @pytest.mark.asyncio
    async def test_analyze_with_results(self) -> None:
        results = [
            _fake_search_result(video_id=f"v{i}", duration=600, views=100_000 * (i + 1))
            for i in range(5)
        ]
        analyzer = self._make_analyzer(results)
        strategy = await analyzer.analyze("tech", ["reviews", "gadgets"], use_ai=False)

        assert strategy.niche == "tech"
        assert len(strategy.source_videos) > 0
        assert len(strategy.recommended_segments) > 0
        assert len(strategy.video_structure) > 0
        assert strategy.compilation_score > 0
        assert isinstance(strategy.editing_guidance, EditingGuidance)
        assert isinstance(strategy.final_video_concept, FinalVideoConcept)

    @pytest.mark.asyncio
    async def test_analyze_score_range(self) -> None:
        results = [
            _fake_search_result(video_id=f"v{i}", duration=300, views=50_000)
            for i in range(10)
        ]
        analyzer = self._make_analyzer(results)
        strategy = await analyzer.analyze("generic", [], use_ai=False)
        assert 0 <= strategy.compilation_score <= 100

    @pytest.mark.asyncio
    async def test_analyze_structure_positions(self) -> None:
        results = [
            _fake_search_result(video_id=f"v{i}", duration=600, views=200_000)
            for i in range(8)
        ]
        analyzer = self._make_analyzer(results)
        strategy = await analyzer.analyze("gaming", ["esports"], use_ai=False)

        positions = [s.position for s in strategy.video_structure]
        assert positions == sorted(positions)
        assert positions[0] == 1

    def test_compute_score_empty(self) -> None:
        score = CompilationAnalyzer._compute_score([], [], [])
        assert score == 0.0

    def test_compute_score_with_diversity(self) -> None:
        sources = [
            _make_source_video(video_id=f"v{i}", engagement=80)
            for i in range(5)
        ]
        # Different channels
        for i, s in enumerate(sources):
            s.channel_name = f"Channel{i}"
        segments = [CompilationSegment() for _ in range(10)]
        structure = [
            CompilationStructureItem(position=i, segment=CompilationSegment())
            for i in range(7)
        ]
        score = CompilationAnalyzer._compute_score(sources, segments, structure)
        assert 0 < score <= 100


# ═══════════════════════════════════════════════════════════════════════
#  AI prompt template tests
# ═══════════════════════════════════════════════════════════════════════


class TestPromptTemplates:
    def test_compilation_strategy_prompt(self) -> None:
        from app.ai.prompts.compilation_analysis import compilation_strategy_prompt

        prompt = compilation_strategy_prompt("tech", "[{}]", "[{}]", "[{}]")
        assert "tech" in prompt
        assert "refined_structure" in prompt
        assert "editing_guidance" in prompt
        assert "JSON" in prompt

    def test_compilation_quick_insight_prompt(self) -> None:
        from app.ai.prompts.compilation_analysis import compilation_quick_insight_prompt

        prompt = compilation_quick_insight_prompt("fitness", 10)
        assert "fitness" in prompt
        assert "10" in prompt
        assert "viability_score" in prompt
