"""Tests for new analysis engines: viral opportunity, topic velocity, thumbnail analysis."""
from __future__ import annotations

import math
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.config.settings import reset_settings, load_settings
from app.core.models import (
    CompetitionMetrics,
    CTRMetrics,
    DiscoverySource,
    FacelessViability,
    NicheScore,
    SearchResult,
    ThumbnailPatternResult,
    ThumbnailSignals,
    ThumbnailStyleGroup,
    TopicVelocityResult,
    ViralityMetrics,
    ViralOpportunity,
    ViralOpportunityResult,
    WeeklyUploadVolume,
)
from app.ranking_engine.engine import NicheRankingEngine
from app.viral_opportunity_detector.engine import ViralOpportunityDetector
from app.topic_velocity.engine import TopicVelocityEngine
from app.thumbnail_analysis.engine import ThumbnailAnalysisEngine


def setup_module() -> None:
    reset_settings()
    load_settings()


# ── Helper: build fake search results ─────────────────────────────────


def _make_result(
    video_id: str = "vid1",
    title: str = "Test Video",
    channel_name: str = "TestChannel",
    channel_subs: int = 1000,
    views: int = 500_000,
    published: str = "2 days ago",
) -> SearchResult:
    return SearchResult(
        video_id=video_id,
        title=title,
        channel_name=channel_name,
        channel_subscribers=channel_subs,
        view_count=views,
        published_date=published,
    )


# ═══════════════════════════════════════════════════════════════════════
#  Viral Opportunity Detector
# ═══════════════════════════════════════════════════════════════════════


class TestViralOpportunityDetector:
    """Unit tests for ViralOpportunityDetector internals."""

    def _make_detector(self) -> ViralOpportunityDetector:
        mock_search = AsyncMock()
        return ViralOpportunityDetector(mock_search)

    # ── _estimate_age_days ────────────────────────────────────────────

    def test_estimate_age_days_hours(self) -> None:
        assert ViralOpportunityDetector._estimate_age_days("5 hours ago") == 0

    def test_estimate_age_days_days(self) -> None:
        assert ViralOpportunityDetector._estimate_age_days("3 days ago") == 3

    def test_estimate_age_days_weeks(self) -> None:
        assert ViralOpportunityDetector._estimate_age_days("2 weeks ago") == 14

    def test_estimate_age_days_months(self) -> None:
        assert ViralOpportunityDetector._estimate_age_days("1 month ago") == 30

    def test_estimate_age_days_years(self) -> None:
        assert ViralOpportunityDetector._estimate_age_days("1 year ago") == 365

    def test_estimate_age_days_yesterday(self) -> None:
        assert ViralOpportunityDetector._estimate_age_days("yesterday") == 1

    def test_estimate_age_days_empty(self) -> None:
        assert ViralOpportunityDetector._estimate_age_days("") is None

    def test_estimate_age_days_garbage(self) -> None:
        assert ViralOpportunityDetector._estimate_age_days("no date here") is None

    # ── _calculate_opportunity_score ──────────────────────────────────

    def test_opportunity_score_high_ratio(self) -> None:
        """Very high view-to-sub ratio should score highly."""
        score = ViralOpportunityDetector._calculate_opportunity_score(
            views=2_000_000, subs=1_000, age_days=3,
        )
        assert score > 50

    def test_opportunity_score_old_video(self) -> None:
        """Old videos should penalize recency."""
        recent = ViralOpportunityDetector._calculate_opportunity_score(
            views=500_000, subs=5_000, age_days=2,
        )
        old = ViralOpportunityDetector._calculate_opportunity_score(
            views=500_000, subs=5_000, age_days=55,
        )
        assert recent > old

    def test_opportunity_score_ranges(self) -> None:
        score = ViralOpportunityDetector._calculate_opportunity_score(
            views=600_000, subs=10_000, age_days=10,
        )
        assert 0 <= score <= 100

    # ── _detect_anomalies ─────────────────────────────────────────────

    def test_detect_anomalies_finds_viral(self) -> None:
        detector = self._make_detector()
        results = [
            _make_result(video_id="v1", channel_subs=5_000, views=800_000, published="1 week ago"),
            _make_result(video_id="v2", channel_subs=200_000, views=300_000, published="3 days ago"),
        ]
        opps = detector._detect_anomalies(results)
        # Only v1 qualifies (< 50k subs, > 500k views)
        assert len(opps) == 1
        assert opps[0].video_id == "v1"

    def test_detect_anomalies_relaxed_threshold(self) -> None:
        detector = self._make_detector()
        results = [
            _make_result(video_id="v1", channel_subs=5_000, views=150_000, published="5 days ago"),
        ]
        opps = detector._detect_anomalies(results)
        # Relaxed: <10k subs, >100k views
        assert len(opps) == 1

    def test_detect_anomalies_ignores_big_channels(self) -> None:
        detector = self._make_detector()
        results = [
            _make_result(video_id="v1", channel_subs=1_000_000, views=5_000_000, published="1 day ago"),
        ]
        opps = detector._detect_anomalies(results)
        assert len(opps) == 0

    def test_detect_anomalies_ignores_old_videos(self) -> None:
        detector = self._make_detector()
        results = [
            _make_result(video_id="v1", channel_subs=5_000, views=800_000, published="3 months ago"),
        ]
        opps = detector._detect_anomalies(results)
        assert len(opps) == 0

    # ── async analyze_niche ───────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_analyze_niche_integration(self) -> None:
        mock_search = AsyncMock()
        mock_search.search = AsyncMock(return_value=[
            _make_result(video_id="v1", channel_subs=3_000, views=700_000, published="4 days ago"),
            _make_result(video_id="v2", channel_subs=500_000, views=1_000_000, published="1 day ago"),
        ])
        detector = ViralOpportunityDetector(mock_search)
        result = await detector.analyze_niche("test niche", ["kw1", "kw2"])
        assert isinstance(result, ViralOpportunityResult)
        assert result.niche == "test niche"
        assert 0 <= result.viral_opportunity_score <= 100


# ═══════════════════════════════════════════════════════════════════════
#  Topic Velocity Engine
# ═══════════════════════════════════════════════════════════════════════


class TestTopicVelocityEngine:
    """Unit tests for TopicVelocityEngine internals."""

    def _make_engine(self) -> TopicVelocityEngine:
        mock_search = AsyncMock()
        return TopicVelocityEngine(mock_search)

    # ── _parse_age_days ───────────────────────────────────────────────

    def test_parse_age_days_days(self) -> None:
        assert TopicVelocityEngine._parse_age_days("5 days ago") == 5

    def test_parse_age_days_weeks(self) -> None:
        assert TopicVelocityEngine._parse_age_days("3 weeks ago") == 21

    def test_parse_age_days_empty(self) -> None:
        assert TopicVelocityEngine._parse_age_days("") is None

    # ── _bucket_by_week ───────────────────────────────────────────────

    def test_bucket_by_week_basic(self) -> None:
        engine = self._make_engine()
        results = [
            _make_result(published="1 day ago"),
            _make_result(published="2 days ago"),
            _make_result(published="10 days ago"),
            _make_result(published="20 days ago"),
            _make_result(published="30 days ago"),
        ]
        buckets = engine._bucket_by_week(results)
        assert len(buckets) == 5
        # Oldest first
        assert buckets[0].week_label.endswith("ago") or buckets[0].week_label == "This week"
        # Most recent bucket should have videos from days 1–6
        most_recent = buckets[-1]
        assert most_recent.week_label == "This week"
        assert most_recent.upload_count >= 2

    def test_bucket_by_week_empty(self) -> None:
        engine = self._make_engine()
        buckets = engine._bucket_by_week([])
        assert len(buckets) == 5
        assert all(b.upload_count == 0 for b in buckets)

    # ── _calculate_growth_rate ────────────────────────────────────────

    def test_growth_rate_doubling(self) -> None:
        weekly = [
            WeeklyUploadVolume(week_label="4 weeks ago", upload_count=5),
            WeeklyUploadVolume(week_label="3 weeks ago", upload_count=6),
            WeeklyUploadVolume(week_label="2 weeks ago", upload_count=7),
            WeeklyUploadVolume(week_label="1 week ago", upload_count=8),
            WeeklyUploadVolume(week_label="This week", upload_count=10),
        ]
        rate = TopicVelocityEngine._calculate_growth_rate(weekly)
        assert rate == pytest.approx(2.0)  # 10 / 5

    def test_growth_rate_zero_oldest(self) -> None:
        weekly = [
            WeeklyUploadVolume(week_label="old", upload_count=0),
            WeeklyUploadVolume(week_label="new", upload_count=5),
        ]
        rate = TopicVelocityEngine._calculate_growth_rate(weekly)
        assert rate == 5.0  # Returns float(newest)

    def test_growth_rate_empty(self) -> None:
        rate = TopicVelocityEngine._calculate_growth_rate([])
        assert rate == 0.0

    # ── _calculate_acceleration ───────────────────────────────────────

    def test_acceleration_positive(self) -> None:
        weekly = [
            WeeklyUploadVolume(week_label="w4", upload_count=2),
            WeeklyUploadVolume(week_label="w3", upload_count=3),
            WeeklyUploadVolume(week_label="w2", upload_count=5),
            WeeklyUploadVolume(week_label="w1", upload_count=8),
            WeeklyUploadVolume(week_label="w0", upload_count=12),
        ]
        accel = TopicVelocityEngine._calculate_acceleration(weekly)
        # Deltas: 1, 2, 3, 4 → Second deltas: 1, 1, 1 → mean 1.0
        assert accel > 0

    def test_acceleration_steady(self) -> None:
        weekly = [
            WeeklyUploadVolume(week_label=f"w{i}", upload_count=5)
            for i in range(5)
        ]
        accel = TopicVelocityEngine._calculate_acceleration(weekly)
        assert accel == 0.0

    def test_acceleration_short(self) -> None:
        weekly = [
            WeeklyUploadVolume(week_label="w1", upload_count=3),
            WeeklyUploadVolume(week_label="w0", upload_count=5),
        ]
        accel = TopicVelocityEngine._calculate_acceleration(weekly)
        assert accel == 0.0

    # ── _compute_velocity_score ───────────────────────────────────────

    def test_velocity_score_ranges(self) -> None:
        weekly = [
            WeeklyUploadVolume(week_label="w4", upload_count=2),
            WeeklyUploadVolume(week_label="w3", upload_count=3),
            WeeklyUploadVolume(week_label="w2", upload_count=4),
            WeeklyUploadVolume(week_label="w1", upload_count=6),
            WeeklyUploadVolume(week_label="w0", upload_count=10),
        ]
        score = TopicVelocityEngine._compute_velocity_score(
            growth_rate=5.0, acceleration=1.5, weekly=weekly,
        )
        assert 0 <= score <= 100

    def test_velocity_score_zero_growth(self) -> None:
        weekly = [WeeklyUploadVolume(week_label="w0", upload_count=0)]
        score = TopicVelocityEngine._compute_velocity_score(
            growth_rate=0, acceleration=0, weekly=weekly,
        )
        assert score == 0.0

    @pytest.mark.asyncio
    async def test_analyze_niche_integration(self) -> None:
        mock_search = AsyncMock()
        mock_search.search = AsyncMock(return_value=[
            _make_result(video_id=f"v{i}", published=f"{i} days ago")
            for i in range(1, 10)
        ])
        engine = TopicVelocityEngine(mock_search)
        result = await engine.analyze_niche("test niche", ["kw"])
        assert isinstance(result, TopicVelocityResult)
        assert result.niche == "test niche"
        assert len(result.weekly_volumes) == 5
        assert 0 <= result.velocity_score <= 100


# ═══════════════════════════════════════════════════════════════════════
#  Thumbnail Analysis Engine
# ═══════════════════════════════════════════════════════════════════════


class TestThumbnailAnalysisEngine:
    """Unit tests for ThumbnailAnalysisEngine internals."""

    def _make_engine(self) -> ThumbnailAnalysisEngine:
        mock_search = AsyncMock()
        return ThumbnailAnalysisEngine(mock_search)

    # ── _quantize_colors ──────────────────────────────────────────────

    def test_quantize_colors_red(self) -> None:
        pixels = [(220, 30, 30)] * 100
        result = ThumbnailAnalysisEngine._quantize_colors(pixels)
        assert "red" in result

    def test_quantize_colors_white(self) -> None:
        pixels = [(250, 250, 250)] * 100
        result = ThumbnailAnalysisEngine._quantize_colors(pixels)
        assert "white" in result

    def test_quantize_colors_mixed(self) -> None:
        pixels = [(220, 30, 30)] * 50 + [(30, 30, 220)] * 50
        result = ThumbnailAnalysisEngine._quantize_colors(pixels)
        assert len(result) >= 2

    def test_quantize_colors_returns_max_3(self) -> None:
        pixels = (
            [(220, 30, 30)] * 30
            + [(30, 30, 220)] * 30
            + [(30, 220, 30)] * 30
            + [(240, 240, 50)] * 30
        )
        result = ThumbnailAnalysisEngine._quantize_colors(pixels)
        assert len(result) <= 3

    # ── _detect_face_heuristic ────────────────────────────────────────

    def test_detect_face_skin_tone(self) -> None:
        """Pixels matching skin-tone heuristic should trigger face detection."""
        # Skin-tone: R>95, G>40, B>20, max-min>15, |R-G|>15, R>G, R>B
        skin_pixels = [(180, 130, 80)] * 200
        result = ThumbnailAnalysisEngine._detect_face_heuristic(skin_pixels, len(skin_pixels))
        assert result is True

    def test_detect_face_no_skin(self) -> None:
        """Pure blue pixels should not trigger face detection."""
        blue_pixels = [(30, 30, 220)] * 200
        result = ThumbnailAnalysisEngine._detect_face_heuristic(blue_pixels, len(blue_pixels))
        assert result is False

    # ── _heuristic_signals ────────────────────────────────────────────

    def test_heuristic_signals_text_keywords(self) -> None:
        engine = self._make_engine()
        video = _make_result(title="Top 10 Best Cameras")
        sig = engine._heuristic_signals(video)
        assert sig.has_text is True

    def test_heuristic_signals_no_keywords(self) -> None:
        engine = self._make_engine()
        video = _make_result(title="Relaxing Music Stream")
        sig = engine._heuristic_signals(video)
        assert sig.has_text is False

    def test_heuristic_signals_face_keywords(self) -> None:
        engine = self._make_engine()
        video = _make_result(title="My Daily Vlog Routine")
        sig = engine._heuristic_signals(video)
        assert sig.has_face is True

    # ── _cluster_styles ───────────────────────────────────────────────

    def test_cluster_styles_groups(self) -> None:
        engine = self._make_engine()
        signals = [
            ThumbnailSignals(
                video_id="v1", has_text=True, has_face=True,
                contrast_level=70, brightness=60, visual_clutter_score=40,
            ),
            ThumbnailSignals(
                video_id="v2", has_text=True, has_face=False,
                contrast_level=80, brightness=50, visual_clutter_score=30,
            ),
            ThumbnailSignals(
                video_id="v3", has_text=False, has_face=False,
                contrast_level=30, brightness=20, visual_clutter_score=60,
            ),
        ]
        videos = [
            _make_result(video_id="v1", views=100_000),
            _make_result(video_id="v2", views=200_000),
            _make_result(video_id="v3", views=50_000),
        ]
        groups = engine._cluster_styles(signals, videos)
        assert len(groups) > 0
        assert all(isinstance(g, ThumbnailStyleGroup) for g in groups)

    def test_cluster_styles_empty(self) -> None:
        engine = self._make_engine()
        groups = engine._cluster_styles([], [])
        assert groups == []

    # ── _generate_recommendations ─────────────────────────────────────

    def test_recommendations_text_heavy(self) -> None:
        engine = self._make_engine()
        signals = [
            ThumbnailSignals(has_text=True, brightness=70),
            ThumbnailSignals(has_text=True, brightness=65),
            ThumbnailSignals(has_text=True, brightness=60),
        ]
        recs = engine._generate_recommendations(signals, [])
        assert any("text" in r.lower() for r in recs)

    def test_recommendations_empty(self) -> None:
        engine = self._make_engine()
        recs = engine._generate_recommendations([], [])
        assert len(recs) >= 1


# ═══════════════════════════════════════════════════════════════════════
#  Ranking Engine (updated formula)
# ═══════════════════════════════════════════════════════════════════════


class TestRankingEngineUpdated:
    """Verify the updated ranking formula includes new signals."""

    def test_ranking_with_viral_and_velocity(self) -> None:
        engine = NicheRankingEngine()
        niche_data = {
            "hot_niche": {
                "demand_score": 80.0,
                "competition": CompetitionMetrics(niche="hot", competition_score=30.0),
                "trend_momentum": 75.0,
                "virality": ViralityMetrics(niche="hot", virality_probability=70.0),
                "ctr": CTRMetrics(niche="hot", ctr_potential=65.0),
                "faceless": FacelessViability(niche="hot", faceless_viability_score=80.0),
                "viral_opportunity": ViralOpportunityResult(
                    niche="hot", viral_opportunity_score=90.0,
                ),
                "topic_velocity": TopicVelocityResult(
                    niche="hot", velocity_score=85.0,
                ),
                "keywords": ["test"],
            },
            "cold_niche": {
                "demand_score": 40.0,
                "competition": CompetitionMetrics(niche="cold", competition_score=80.0),
                "trend_momentum": 30.0,
                "virality": ViralityMetrics(niche="cold", virality_probability=25.0),
                "ctr": CTRMetrics(niche="cold", ctr_potential=30.0),
                "faceless": FacelessViability(niche="cold", faceless_viability_score=40.0),
                "viral_opportunity": ViralOpportunityResult(
                    niche="cold", viral_opportunity_score=10.0,
                ),
                "topic_velocity": TopicVelocityResult(
                    niche="cold", velocity_score=5.0,
                ),
                "keywords": ["test"],
            },
        }
        ranked = engine.rank_niches(niche_data)
        assert ranked[0].niche == "hot_niche"
        assert ranked[0].viral_opportunity_score == 90.0
        assert ranked[0].topic_velocity_score == 85.0

    def test_ranking_without_new_signals(self) -> None:
        """Still works when viral_opportunity / topic_velocity are missing."""
        engine = NicheRankingEngine()
        niche_data = {
            "basic": {
                "demand_score": 60.0,
                "keywords": ["test"],
            },
        }
        ranked = engine.rank_niches(niche_data)
        assert len(ranked) == 1
        # Defaults changed from 0.0 to 30.0 to avoid penalising niches
        # that simply haven't been analysed for these signals yet.
        assert ranked[0].viral_opportunity_score == 30.0
        assert ranked[0].topic_velocity_score == 30.0


# ═══════════════════════════════════════════════════════════════════════
#  Model Tests
# ═══════════════════════════════════════════════════════════════════════


class TestNewModels:
    """Basic model construction tests."""

    def test_viral_opportunity(self) -> None:
        opp = ViralOpportunity(
            video_title="test", video_id="v1",
            channel_name="ch1", channel_subscribers=5000,
            video_views=1_000_000, video_age_days=5,
            views_to_sub_ratio=200.0, opportunity_score=75.0,
        )
        assert opp.views_to_sub_ratio == 200.0

    def test_topic_velocity_result(self) -> None:
        result = TopicVelocityResult(
            niche="tech", growth_rate=2.5, acceleration=0.8, velocity_score=70.0,
        )
        assert result.velocity_score == 70.0

    def test_thumbnail_signals_defaults(self) -> None:
        sig = ThumbnailSignals()
        assert sig.has_text is False
        assert sig.dominant_colors == []

    def test_discovery_source(self) -> None:
        src = DiscoverySource(topic="ai tools", source="google_trends", score=0.85)
        assert src.topic == "ai tools"

    def test_niche_report_new_fields(self) -> None:
        from app.core.models import NicheReport
        report = NicheReport()
        assert report.viral_opportunities == {}
        assert report.topic_velocities == {}
        assert report.thumbnail_patterns == {}
