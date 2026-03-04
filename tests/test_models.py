"""Tests for core models."""
from __future__ import annotations

from app.core.models import (
    AutocompleteResult,
    CompetitionMetrics,
    CTRMetrics,
    FacelessFormat,
    FacelessViability,
    KeywordCluster,
    NicheScore,
    RedditSignal,
    SearchResult,
    TrendData,
    TrendDirection,
    VideoBlueprint,
    VideoIdea,
    ViralityMetrics,
    NicheReport,
)


def test_autocomplete_result() -> None:
    result = AutocompleteResult(query="test", suggestions=["test 1", "test 2"])
    assert result.query == "test"
    assert len(result.suggestions) == 2
    assert result.source == "youtube"


def test_search_result() -> None:
    result = SearchResult(title="Test Video", channel_name="TestChannel", view_count=1000)
    assert result.title == "Test Video"
    assert result.view_count == 1000
    assert result.video_id == ""


def test_trend_data() -> None:
    trend = TrendData(
        keyword="python",
        interest_over_time=[10, 20, 30, 40, 50],
        direction=TrendDirection.RISING,
        momentum_score=75.0,
    )
    assert trend.direction == TrendDirection.RISING
    assert trend.momentum_score == 75.0


def test_reddit_signal() -> None:
    signal = RedditSignal(
        keyword="test",
        post_count_7d=50,
        spike_detected=True,
    )
    assert signal.spike_detected is True
    assert signal.post_count_7d == 50


def test_keyword_cluster() -> None:
    cluster = KeywordCluster(
        cluster_id=1,
        name="python programming",
        keywords=["python tutorial", "learn python", "python basics"],
        seed_keyword="python",
        size=3,
    )
    assert cluster.size == 3
    assert cluster.seed_keyword == "python"


def test_competition_metrics() -> None:
    metrics = CompetitionMetrics(
        niche="test",
        avg_views_top20=50000,
        competition_score=65.0,
    )
    assert metrics.competition_score == 65.0


def test_virality_metrics() -> None:
    metrics = ViralityMetrics(
        niche="test",
        curiosity_gap=80.0,
        virality_probability=72.5,
    )
    assert metrics.virality_probability == 72.5


def test_ctr_metrics() -> None:
    metrics = CTRMetrics(
        niche="test",
        title_curiosity=90.0,
        ctr_potential=78.0,
    )
    assert metrics.ctr_potential == 78.0


def test_faceless_viability() -> None:
    viability = FacelessViability(
        niche="test",
        best_formats=[FacelessFormat.STOCK_FOOTAGE, FacelessFormat.BROLL_VOICEOVER],
        faceless_viability_score=85.0,
    )
    assert viability.faceless_viability_score == 85.0
    assert FacelessFormat.STOCK_FOOTAGE in viability.best_formats


def test_niche_score() -> None:
    score = NicheScore(
        niche="test niche",
        demand_score=80.0,
        competition_score=40.0,
        trend_momentum=70.0,
        virality_score=65.0,
        ctr_potential=75.0,
        faceless_viability=90.0,
        overall_score=72.5,
        rank=1,
    )
    assert score.rank == 1
    assert score.overall_score == 72.5


def test_video_idea() -> None:
    idea = VideoIdea(
        title="Test Video",
        topic="testing",
        angle="tutorial",
        target_keywords=["test", "tutorial"],
    )
    assert idea.title == "Test Video"
    assert len(idea.target_keywords) == 2


def test_niche_report() -> None:
    report = NicheReport(
        seed_keywords=["test"],
        top_niches=[
            NicheScore(niche="test", overall_score=80.0, rank=1),
        ],
    )
    assert len(report.top_niches) == 1
    assert report.seed_keywords == ["test"]
