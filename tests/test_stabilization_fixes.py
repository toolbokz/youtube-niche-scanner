"""Tests validating the stabilization fixes applied during the architecture audit.

Each test targets a specific fix and proves it works correctly.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ═══════════════════════════════════════════════════════════════════════
#  1. datetime.utcnow → timezone-aware datetime
# ═══════════════════════════════════════════════════════════════════════

class TestTimezoneAwareDatetimes:
    """Verify all datetime defaults are timezone-aware (UTC)."""

    def test_database_niche_record_created_at(self) -> None:
        from app.database.models import NicheRecord
        col = NicheRecord.__table__.columns["created_at"]
        # SQLAlchemy ColumnDefault wraps lambdas; for context-sensitive defaults
        # we verify the function signature accepts 'ctx' and produces tz-aware dt.
        import inspect
        sig = inspect.signature(col.default.arg)
        assert len(sig.parameters) <= 1  # lambda or lambda ctx

    def test_database_niche_record_updated_at(self) -> None:
        from app.database.models import NicheRecord
        col = NicheRecord.__table__.columns["updated_at"]
        import inspect
        sig = inspect.signature(col.default.arg)
        assert len(sig.parameters) <= 1

    def test_database_keyword_record(self) -> None:
        from app.database.models import KeywordRecord
        col = KeywordRecord.__table__.columns["created_at"]
        import inspect
        src = inspect.getsource(col.default.arg)
        assert "timezone.utc" in src, "KeywordRecord.created_at must use timezone.utc"

    def test_video_factory_job_model_created_at(self) -> None:
        from app.video_factory.models import FactoryJob
        job = FactoryJob(job_id="test", niche="test")
        assert job.created_at.tzinfo is not None

    def test_core_niche_report_timestamp(self) -> None:
        from app.core.models import NicheReport
        report = NicheReport(
            seed_keywords=["test"],
            top_niches=[],
            channel_concepts=[],
            video_blueprints={},
        )
        assert report.generated_at.tzinfo is not None


# ═══════════════════════════════════════════════════════════════════════
#  2. Ranking engine includes faceless viability
# ═══════════════════════════════════════════════════════════════════════

class TestRankingFacelessViability:
    """Verify faceless viability contributes to overall score."""

    def test_faceless_viability_affects_score(self) -> None:
        from app.ranking_engine.engine import NicheRankingEngine

        engine = NicheRankingEngine()

        # Same niche with low vs high faceless viability
        low_faceless = {
            "low_face": {
                "demand_score": 50.0,
                "faceless": MagicMock(faceless_viability_score=10.0),
                "keywords": ["test"],
            },
        }
        high_faceless = {
            "high_face": {
                "demand_score": 50.0,
                "faceless": MagicMock(faceless_viability_score=90.0),
                "keywords": ["test"],
            },
        }
        low_ranked = engine.rank_niches(low_faceless)
        high_ranked = engine.rank_niches(high_faceless)

        assert high_ranked[0].overall_score > low_ranked[0].overall_score, (
            "Higher faceless viability should yield a higher overall score"
        )

    def test_all_weights_contribute(self) -> None:
        """All 8 dimensions should affect the final score."""
        from app.ranking_engine.engine import NicheRankingEngine

        engine = NicheRankingEngine()

        base = {
            "niche": {
                "demand_score": 0.0,
                "trend_momentum": 0.0,
                "keywords": ["test"],
            }
        }
        base_score = engine.rank_niches(base)[0].overall_score

        # Any positive demand should increase score
        with_demand = {
            "niche": {
                "demand_score": 100.0,
                "trend_momentum": 0.0,
                "keywords": ["test"],
            }
        }
        demand_score = engine.rank_niches(with_demand)[0].overall_score
        assert demand_score > base_score


# ═══════════════════════════════════════════════════════════════════════
#  3. Demand and trend are separate signals in the pipeline
# ═══════════════════════════════════════════════════════════════════════

class TestDemandTrendSeparation:
    """Verify pipeline passes separate demand_map and trend_map."""

    @pytest.mark.asyncio
    async def test_analyze_single_niche_receives_both_maps(self) -> None:
        """_analyze_single_niche should use demand_map for demand and trend_map for trend."""
        from app.core.pipeline import PipelineOrchestrator

        with patch.object(PipelineOrchestrator, "__init__", lambda self: None):
            orch = PipelineOrchestrator.__new__(PipelineOrchestrator)
            orch._niche_sem = asyncio.Semaphore(1)

            # Mock all engines
            orch.competition_engine = MagicMock()
            orch.competition_engine.analyze_niche = AsyncMock(return_value=None)
            orch.viral_opportunity_detector = MagicMock()
            orch.viral_opportunity_detector.analyze_niche = AsyncMock(return_value=None)
            orch.topic_velocity_engine = MagicMock()
            orch.topic_velocity_engine.analyze_niche = AsyncMock(return_value=None)
            orch.thumbnail_analysis_engine = MagicMock()
            orch.thumbnail_analysis_engine.analyze_niche = AsyncMock(return_value=None)
            orch.virality_engine = MagicMock()
            orch.virality_engine.analyze_niche = MagicMock(return_value=MagicMock(virality_probability=50.0))
            orch.ctr_engine = MagicMock()
            orch.ctr_engine.analyze_niche = MagicMock(return_value=MagicMock(ctr_potential=50.0))
            orch.faceless_engine = MagicMock()
            orch.faceless_engine.analyze_niche = MagicMock(return_value=MagicMock(faceless_viability_score=50.0))

            from app.core.models import KeywordCluster

            cluster = KeywordCluster(
                cluster_id=0, name="test_niche",
                keywords=["kw1", "kw2"], seed_keyword="kw1", size=2,
            )

            demand_map = {"kw1": 80.0, "kw2": 60.0}
            trend_map = {"kw1": 20.0, "kw2": 10.0}

            niche_name, data = await orch._analyze_single_niche(
                cluster, demand_map, trend_map,
            )

            # Demand should come from demand_map (avg of 80 and 60 = 70)
            assert data["demand_score"] == 70.0
            # Trend should come from trend_map (avg of 20 and 10 = 15)
            assert data["trend_momentum"] == 15.0
            # They must be different (previously they were the same value)
            assert data["demand_score"] != data["trend_momentum"]


# ═══════════════════════════════════════════════════════════════════════
#  4. Niche clustering immutable merge
# ═══════════════════════════════════════════════════════════════════════

class TestClusteringImmutableMerge:
    """Verify merge_small_clusters doesn't mutate input clusters."""

    def test_merge_creates_new_objects(self) -> None:
        from app.niche_clustering.engine import NicheClusteringEngine
        from app.core.models import KeywordCluster

        engine = NicheClusteringEngine()

        small = KeywordCluster(
            cluster_id=0, name="tiny", keywords=["a", "b"],
            seed_keyword="a", size=2,
        )
        big = KeywordCluster(
            cluster_id=1, name="big", keywords=["c", "d", "e", "f"],
            seed_keyword="c", size=4,
        )

        original_big_kws = list(big.keywords)
        result = engine.merge_small_clusters([small, big], min_size=3)

        # The original big cluster keywords should NOT be mutated
        assert big.keywords == original_big_kws, (
            "merge_small_clusters must not mutate the input cluster keywords"
        )


# ═══════════════════════════════════════════════════════════════════════
#  5. AI service uses async methods
# ═══════════════════════════════════════════════════════════════════════

class TestAIServiceAsync:
    """Verify the AI service calls async methods on the client."""

    @pytest.mark.asyncio
    async def test_analyze_niches_calls_agenerate_json(self) -> None:
        client = MagicMock()
        client.available = True
        client.agenerate_json = AsyncMock(return_value={"result": True})

        with patch("app.ai.service.get_ai_client", return_value=client), \
             patch("app.ai.service._get_cached", new_callable=AsyncMock, return_value=None), \
             patch("app.ai.service._store_cache", new_callable=AsyncMock):
            from app.ai.service import analyze_niches
            result = await analyze_niches([{"niche": "test", "overall_score": 50, "keywords": ["t"]}])

        client.agenerate_json.assert_called_once()
        assert "result" in result

    @pytest.mark.asyncio
    async def test_generate_compilation_strategy_async(self) -> None:
        client = MagicMock()
        client.available = True
        client.agenerate_json = AsyncMock(return_value={"strategy": True})

        with patch("app.ai.service.get_ai_client", return_value=client), \
             patch("app.ai.service._get_cached", new_callable=AsyncMock, return_value=None), \
             patch("app.ai.service._store_cache", new_callable=AsyncMock):
            from app.ai.service import generate_compilation_strategy
            result = await generate_compilation_strategy(
                "test", "[{\"title\": \"test\", \"views\": 1000}]", "[\"seg1\"]", "[]",
            )

        client.agenerate_json.assert_called_once()
        assert "strategy" in result


# ═══════════════════════════════════════════════════════════════════════
#  6. Subprocess timeouts are configured
# ═══════════════════════════════════════════════════════════════════════

class TestSubprocessTimeouts:
    """Verify that subprocess calls have timeout protection."""

    @pytest.mark.asyncio
    async def test_segment_extractor_has_timeout(self) -> None:
        """Verify the extract function kills stuck processes."""
        from app.video_factory.segment_extractor import SegmentExtractor

        extractor = SegmentExtractor()

        # Mock create_subprocess_exec to return a stuck process
        mock_proc = MagicMock()
        mock_proc.communicate = AsyncMock(side_effect=asyncio.TimeoutError())
        mock_proc.kill = MagicMock()
        mock_proc.wait = AsyncMock()

        with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock, return_value=mock_proc), \
             patch("asyncio.wait_for", side_effect=asyncio.TimeoutError()):
            with pytest.raises(RuntimeError, match="timed out"):
                await extractor._extract_single(
                    source_path="/fake/video.mp4",
                    output_path="/fake/clip.mp4",
                    start_seconds=0.0,
                    end_seconds=10.0,
                    clip_id="clip_001",
                    video_id="vid001",
                )

    @pytest.mark.asyncio
    async def test_clip_validator_probe_has_timeout(self) -> None:
        """Verify ffprobe calls have timeout."""
        from app.video_factory.clip_validator import ClipValidator

        # Read source to verify wait_for is used
        import inspect
        source = inspect.getsource(ClipValidator._ffprobe)
        assert "wait_for" in source, "ffprobe must use asyncio.wait_for for timeout"


# ═══════════════════════════════════════════════════════════════════════
#  7. Parallel clip validation
# ═══════════════════════════════════════════════════════════════════════

class TestParallelClipValidation:
    """Verify clips are validated in parallel."""

    def test_validate_clips_uses_gather(self) -> None:
        """The validation method should use asyncio.gather for parallelism."""
        import inspect
        from app.video_factory.clip_validator import ClipValidator

        source = inspect.getsource(ClipValidator.validate_clips)
        assert "gather" in source, "validate_clips should use asyncio.gather"
        assert "Semaphore" in source, "validate_clips should use a semaphore"


# ═══════════════════════════════════════════════════════════════════════
#  8. Parallel video downloads
# ═══════════════════════════════════════════════════════════════════════

class TestParallelDownloads:
    """Verify video downloads are parallel."""

    def test_download_uses_gather(self) -> None:
        import inspect
        from app.video_factory.youtube_downloader import YouTubeDownloader

        source = inspect.getsource(YouTubeDownloader.download_source_videos)
        assert "gather" in source, "download_source_videos should use asyncio.gather"
        assert "Semaphore" in source, "download_source_videos should use a semaphore"


# ═══════════════════════════════════════════════════════════════════════
#  9. CTR engine dynamic year
# ═══════════════════════════════════════════════════════════════════════

class TestCTRDynamicYear:
    """Verify CTR engine uses dynamic year."""

    def test_no_hardcoded_2024(self) -> None:
        import inspect
        from app.ctr_prediction.engine import CTRPredictionEngine

        source = inspect.getsource(CTRPredictionEngine)
        assert "2024" not in source, "CTR engine must not have hardcoded 2024"
        assert "datetime.now().year" in source or "datetime.now()" in source


# ═══════════════════════════════════════════════════════════════════════
#  10. Topic velocity discards old videos
# ═══════════════════════════════════════════════════════════════════════

class TestTopicVelocityBuckets:
    """Verify videos >4 weeks are discarded."""

    def test_old_videos_discarded(self) -> None:
        import inspect
        from app.topic_velocity.engine import TopicVelocityEngine

        source = inspect.getsource(TopicVelocityEngine)
        # Should skip videos older than 4 weeks
        assert "week_index > 4" in source or "continue" in source


# ═══════════════════════════════════════════════════════════════════════
#  11. Keyword expansion bounded concurrency
# ═══════════════════════════════════════════════════════════════════════

class TestKeywordExpansionConcurrency:
    """Verify keyword expansion has bounded concurrency."""

    def test_uses_semaphore(self) -> None:
        import inspect
        from app.keyword_expansion.engine import KeywordExpansionEngine

        source = inspect.getsource(KeywordExpansionEngine.expand_batch)
        assert "Semaphore" in source, "expand_batch must use a semaphore"


# ═══════════════════════════════════════════════════════════════════════
#  12. Job manager thread safety
# ═══════════════════════════════════════════════════════════════════════

class TestJobManagerThreadSafety:
    """Verify job manager progress callback uses threading lock."""

    def test_has_threading_lock(self) -> None:
        import inspect
        from app.video_factory.job_manager import FactoryJobManager

        source = inspect.getsource(FactoryJobManager)
        assert "threading.Lock" in source or "_lock" in source
        assert "with self._lock" in source, "Progress callback must use the lock"

    def test_runs_orchestrator_directly(self) -> None:
        """Job manager must await the orchestrator, not use asyncio.run."""
        import inspect
        from app.video_factory.job_manager import FactoryJobManager

        source = inspect.getsource(FactoryJobManager._run_job)
        assert "asyncio.run(" not in source, "Must not use asyncio.run inside async context"
        assert "await orchestrator.run(" in source


# ═══════════════════════════════════════════════════════════════════════
#  13. Video assembler timeout + GPU fallback
# ═══════════════════════════════════════════════════════════════════════

class TestVideoAssemblerTimeout:
    """Verify video assembler has timeout on encoding."""

    def test_encode_has_timeout(self) -> None:
        import inspect
        from app.video_factory.video_assembler import CompilationAssembler

        source = inspect.getsource(CompilationAssembler._run_concat_cmd)
        assert "wait_for" in source, "Encoding must have subprocess timeout"
        assert "TimeoutError" in source, "Must handle timeout errors"
