"""Pipeline Orchestrator — parallelised analysis pipeline.

Performance improvements over v1:
- Steps 1 & 2 (keyword expansion + trend discovery) run **concurrently**.
- Per-niche analysis (steps 4-7) runs **all niches in parallel** via
  asyncio.gather with bounded concurrency (semaphore).
- Strategy generation for ranked niches also parallelised.
- Timing breakdowns logged per step for observability.
"""
from __future__ import annotations

import asyncio
import time
from typing import Any

from app.config import get_settings
from app.connectors.google_trends import GoogleTrendsConnector
from app.connectors.keyword_scraper import KeywordScraperConnector
from app.connectors.reddit import RedditConnector
from app.connectors.youtube_autocomplete import YouTubeAutocompleteConnector
from app.connectors.youtube_search import YouTubeSearchConnector
from app.competition_analysis.engine import CompetitionAnalysisEngine
from app.ctr_prediction.engine import CTRPredictionEngine
from app.discovery_engine.engine import DiscoveryEngine
from app.faceless_viability.engine import FacelessViabilityEngine
from app.keyword_expansion.engine import KeywordExpansionEngine
from app.niche_clustering.engine import NicheClusteringEngine
from app.ranking_engine.engine import NicheRankingEngine
from app.report_generation.engine import ReportGenerationEngine
from app.thumbnail_analysis.engine import ThumbnailAnalysisEngine
from app.topic_velocity.engine import TopicVelocityEngine
from app.trend_discovery.engine import TrendDiscoveryEngine
from app.video_strategy.blueprint import BlueprintAssembler
from app.video_strategy.engine import VideoStrategyEngine
from app.viral_opportunity_detector.engine import ViralOpportunityDetector
from app.virality_prediction.engine import ViralityPredictionEngine
from app.core.logging import get_logger
from app.core.models import (
    NicheReport,
    ViralOpportunity,
    TopicVelocityResult,
    ThumbnailPatternResult,
    KeywordCluster,
)

logger = get_logger(__name__)

# Max parallel niche analysis tasks — prevents HTTP connection storms
_NICHE_CONCURRENCY = 6


def _elapsed_since(t0: float) -> float:
    return round(time.time() - t0, 2)


class PipelineOrchestrator:
    """Orchestrates the complete niche discovery and strategy generation pipeline."""

    def __init__(self) -> None:
        settings = get_settings()
        connectors = settings.connectors

        # Initialize connectors
        self.yt_autocomplete = YouTubeAutocompleteConnector(connectors.youtube_autocomplete)
        self.yt_search = YouTubeSearchConnector(connectors.youtube_search)
        self.google_trends = GoogleTrendsConnector(connectors.google_trends)
        self.reddit = RedditConnector(connectors.reddit)
        self.keyword_scraper = KeywordScraperConnector(connectors.youtube_autocomplete)

        # Initialize engines
        self.trend_engine = TrendDiscoveryEngine(
            self.google_trends, self.reddit, self.yt_autocomplete, self.yt_search
        )
        self.keyword_engine = KeywordExpansionEngine(self.yt_autocomplete, self.keyword_scraper)
        self.clustering_engine = NicheClusteringEngine()
        self.competition_engine = CompetitionAnalysisEngine(self.yt_search)
        self.virality_engine = ViralityPredictionEngine()
        self.ctr_engine = CTRPredictionEngine()
        self.faceless_engine = FacelessViabilityEngine()
        self.ranking_engine = NicheRankingEngine()
        self.video_strategy_engine = VideoStrategyEngine()
        self.blueprint_assembler = BlueprintAssembler()
        self.report_engine = ReportGenerationEngine()

        # Advanced engines
        self.discovery_engine = DiscoveryEngine(
            self.google_trends, self.reddit, self.yt_autocomplete, self.yt_search
        )
        self.viral_opportunity_detector = ViralOpportunityDetector(self.yt_search)
        self.topic_velocity_engine = TopicVelocityEngine(self.yt_search)
        self.thumbnail_analysis_engine = ThumbnailAnalysisEngine(self.yt_search)

        # Semaphore for bounded concurrency
        self._niche_sem = asyncio.Semaphore(_NICHE_CONCURRENCY)

    # ── Single-niche analysis (runs under semaphore) ─────────────────

    async def _analyze_single_niche(
        self,
        cluster: KeywordCluster,
        demand_map: dict[str, float],
        trend_map: dict[str, float] | None = None,
    ) -> tuple[str, dict[str, Any]]:
        """Analyse one niche — all its sub-tasks run concurrently."""
        async with self._niche_sem:
            niche_name = cluster.name
            keywords = cluster.keywords

            # Fire all async analyses concurrently
            competition_task = self.competition_engine.analyze_niche(niche_name, keywords)
            viral_opp_task = self.viral_opportunity_detector.analyze_niche(niche_name, keywords)
            velocity_task = self.topic_velocity_engine.analyze_niche(niche_name, keywords)
            thumbnail_task = self.thumbnail_analysis_engine.analyze_niche(niche_name, keywords)

            competition, viral_opp_result, velocity_result, thumbnail_result = (
                await asyncio.gather(
                    competition_task, viral_opp_task, velocity_task, thumbnail_task,
                    return_exceptions=True,
                )
            )

            # Handle exceptions gracefully
            if isinstance(competition, BaseException):
                logger.warning("niche_competition_error", niche=niche_name, error=str(competition))
                competition = None
            if isinstance(viral_opp_result, BaseException):
                logger.warning("niche_viral_opp_error", niche=niche_name, error=str(viral_opp_result))
                viral_opp_result = None
            if isinstance(velocity_result, BaseException):
                logger.warning("niche_velocity_error", niche=niche_name, error=str(velocity_result))
                velocity_result = None
            if isinstance(thumbnail_result, BaseException):
                logger.warning("niche_thumbnail_error", niche=niche_name, error=str(thumbnail_result))
                thumbnail_result = None

            # Sync engines — CPU-light, run directly
            virality = self.virality_engine.analyze_niche(niche_name, keywords)
            ctr = self.ctr_engine.analyze_niche(niche_name, keywords)
            faceless = self.faceless_engine.analyze_niche(niche_name, keywords)

            # Demand score from expansion breadth + blended trend signal
            kw_demands = [demand_map.get(kw, 50.0) for kw in keywords if kw in demand_map]
            demand_score = sum(kw_demands) / len(kw_demands) if kw_demands else 50.0

            # Trend momentum — from actual Google Trends momentum data
            _tmap = trend_map or {}
            kw_trends = [_tmap.get(kw, 0.0) for kw in keywords if kw in _tmap]
            trend_momentum = sum(kw_trends) / len(kw_trends) if kw_trends else 50.0

            data: dict[str, Any] = {
                "demand_score": demand_score,
                "competition": competition,
                "trend_momentum": trend_momentum,
                "virality": virality,
                "ctr": ctr,
                "faceless": faceless,
                "viral_opportunity": viral_opp_result,
                "topic_velocity": velocity_result,
                "thumbnail_result": thumbnail_result,
                "keywords": keywords,
            }
            return niche_name, data

    # ── Full pipeline ────────────────────────────────────────────────

    async def run_full_pipeline(
        self,
        seed_keywords: list[str],
        top_n: int | None = None,
        videos_per_niche: int | None = None,
    ) -> NicheReport:
        """Execute the complete pipeline end-to-end with maximum parallelism.

        Steps 1-2 run concurrently (keyword expansion ∥ trend discovery).
        Steps 4-7 run all niches in parallel (bounded by semaphore).
        Steps 9-10 strategy generation parallelised across niches.
        """
        settings = get_settings()
        if top_n is None:
            top_n = settings.analysis.top_niches_count
        if videos_per_niche is None:
            videos_per_niche = settings.analysis.videos_per_niche

        start_time = time.time()
        step_timings: dict[str, float] = {}
        logger.info("pipeline_started", seeds=seed_keywords)

        # ── Steps 1 + 2: Keyword Expansion ∥ Trend Discovery (concurrent) ──
        t0 = time.time()
        logger.info("steps_1_2_concurrent_expansion_trends")

        async def _expand() -> dict[str, list[str]]:
            return await self.keyword_engine.expand_batch(seed_keywords, use_prefixes=False)

        async def _trends(kws: list[str]) -> list[dict[str, Any]]:
            return await self.trend_engine.discover_trends(kws)

        # Start keyword expansion
        expand_task = asyncio.create_task(_expand())
        # Run trend discovery on seed keywords first (we'll get expanded later)
        seed_trends_task = asyncio.create_task(_trends(seed_keywords[:30]))

        expanded, seed_trend_results = await asyncio.gather(expand_task, seed_trends_task)

        all_keywords: list[str] = list(seed_keywords)
        for kw_list in expanded.values():
            all_keywords.extend(kw_list)
        all_keywords = list(dict.fromkeys(all_keywords))  # Deduplicate

        # Build trend momentum scores from seed trends
        trend_map: dict[str, float] = {}
        for tr in seed_trend_results:
            trend_map[tr["keyword"]] = tr["trend_momentum_score"]

        # Build demand proxy from keyword expansion breadth:
        # keywords that expanded into more suggestions have higher demand.
        demand_map: dict[str, float] = {}
        for seed, expansions in expanded.items():
            # More autocomplete suggestions → higher demand (normalized to 0-100)
            expansion_score = min(100.0, len(expansions) * 3.0)
            demand_map[seed] = expansion_score
            # Expanded keywords inherit a fraction of the seed's demand
            for kw in expansions:
                demand_map.setdefault(kw, expansion_score * 0.7)
        # Overlay trend data as supplemental demand signal
        for kw, momentum in trend_map.items():
            if kw in demand_map:
                # Blend: 60% expansion breadth + 40% trend momentum
                demand_map[kw] = demand_map[kw] * 0.6 + momentum * 0.4
            else:
                demand_map[kw] = momentum

        step_timings["steps_1_2_expand_trends"] = _elapsed_since(t0)
        logger.info("steps_1_2_done", keywords=len(all_keywords),
                     trends=len(seed_trend_results), time_s=step_timings["steps_1_2_expand_trends"])

        # ── Step 3: Niche Clustering (CPU-only, fast) ──
        t0 = time.time()
        logger.info("step_3_niche_clustering")
        clusters = self.clustering_engine.cluster_keywords(all_keywords, seed_keywords)
        clusters = self.clustering_engine.merge_small_clusters(clusters, min_size=3)

        if not clusters:
            logger.warning("no_clusters_formed")
            clusters = [
                KeywordCluster(
                    cluster_id=i, name=kw, keywords=[kw], seed_keyword=kw, size=1,
                )
                for i, kw in enumerate(seed_keywords)
            ]

        step_timings["step_3_clustering"] = _elapsed_since(t0)
        logger.info("clusters_formed", count=len(clusters), time_s=step_timings["step_3_clustering"])

        # ── Steps 4-7: Per-niche analysis — ALL NICHES IN PARALLEL ──
        t0 = time.time()
        logger.info("steps_4_7_parallel_niche_analysis", niche_count=len(clusters))

        niche_results = await asyncio.gather(
            *(self._analyze_single_niche(cluster, demand_map, trend_map) for cluster in clusters),
            return_exceptions=True,
        )

        niche_data: dict[str, dict[str, Any]] = {}
        all_viral_opportunities: dict[str, list[ViralOpportunity]] = {}
        all_topic_velocities: dict[str, TopicVelocityResult] = {}
        all_thumbnail_patterns: dict[str, ThumbnailPatternResult] = {}

        for result in niche_results:
            if isinstance(result, BaseException):
                logger.warning("niche_analysis_failed", error=str(result))
                continue
            niche_name, data = result
            niche_data[niche_name] = data

            viral_opp = data.get("viral_opportunity")
            if viral_opp and hasattr(viral_opp, "opportunities") and viral_opp.opportunities:
                all_viral_opportunities[niche_name] = viral_opp.opportunities

            velocity = data.get("topic_velocity")
            if velocity:
                all_topic_velocities[niche_name] = velocity

            thumbnail = data.get("thumbnail_result")
            if thumbnail:
                all_thumbnail_patterns[niche_name] = thumbnail

        step_timings["steps_4_7_niche_analysis"] = _elapsed_since(t0)
        logger.info("steps_4_7_done", niches=len(niche_data),
                     time_s=step_timings["steps_4_7_niche_analysis"])

        # ── Step 8: Niche Ranking ──
        t0 = time.time()
        logger.info("step_8_ranking")
        top_niches = self.ranking_engine.get_top_niches(niche_data, top_n)
        step_timings["step_8_ranking"] = _elapsed_since(t0)
        logger.info("top_niches_ranked", count=len(top_niches), time_s=step_timings["step_8_ranking"])

        # ── Step 8b: Optional AI Enhancement (only top-ranked niches) ──
        ai_insights: dict[str, Any] = {}
        try:
            from app.config import get_settings as _gs
            if _gs().vertex_ai.enabled:
                t0 = time.time()
                from app.ai.service import run_full_ai_analysis

                _tmp_report = {
                    "top_niches": [n.model_dump(mode="json") for n in top_niches],
                    "viral_opportunities": {
                        k: [o.model_dump(mode="json") for o in v]
                        for k, v in all_viral_opportunities.items()
                    },
                    "topic_velocities": {
                        k: v.model_dump(mode="json")
                        for k, v in all_topic_velocities.items()
                    },
                    "thumbnail_patterns": {
                        k: v.model_dump(mode="json")
                        for k, v in all_thumbnail_patterns.items()
                    },
                }
                logger.info("step_8b_ai_enhancement")
                ai_insights = await run_full_ai_analysis(_tmp_report)
                step_timings["step_8b_ai"] = _elapsed_since(t0)
                logger.info("ai_enhancement_complete", sections=list(ai_insights.keys()),
                             time_s=step_timings.get("step_8b_ai"))
        except Exception as exc:
            logger.warning("ai_enhancement_skipped", error=str(exc))

        # ── Steps 9-10: Strategy & Blueprint Generation (parallel) ──
        t0 = time.time()
        logger.info("steps_9_10_strategy_generation")
        channel_concepts = []
        video_blueprints: dict[str, list[Any]] = {}

        def _generate_for_niche(niche_score):  # type: ignore[no-untyped-def]
            niche_name = niche_score.niche
            faceless_data = niche_data.get(niche_name, {}).get("faceless")
            concept = self.video_strategy_engine.generate_channel_concept(niche_score, faceless_data)
            ideas = self.video_strategy_engine.generate_video_ideas(niche_score, count=videos_per_niche)
            blueprints = self.blueprint_assembler.assemble_batch(ideas, niche_score)
            return concept, niche_name, blueprints

        # Strategy generation is CPU-bound, run in executor for parallelism
        loop = asyncio.get_running_loop()
        strategy_tasks = [
            loop.run_in_executor(None, _generate_for_niche, ns) for ns in top_niches
        ]
        strategy_results = await asyncio.gather(*strategy_tasks, return_exceptions=True)

        for result in strategy_results:
            if isinstance(result, BaseException):
                logger.warning("strategy_gen_error", error=str(result))
                continue
            concept, niche_name, blueprints = result
            channel_concepts.append(concept)
            video_blueprints[niche_name] = blueprints

        step_timings["steps_9_10_strategy"] = _elapsed_since(t0)
        logger.info("steps_9_10_done", time_s=step_timings["steps_9_10_strategy"])

        # ── Step 11: Report ──
        elapsed = round(time.time() - start_time, 1)

        report = self.report_engine.generate_report(
            seed_keywords=seed_keywords,
            top_niches=top_niches,
            channel_concepts=channel_concepts,
            video_blueprints=video_blueprints,
            viral_opportunities=all_viral_opportunities,
            topic_velocities=all_topic_velocities,
            thumbnail_patterns=all_thumbnail_patterns,
            ai_insights=ai_insights,
            metadata={
                "total_keywords_analyzed": len(all_keywords),
                "total_clusters": len(clusters),
                "pipeline_duration_seconds": elapsed,
                "step_timings": step_timings,
                "viral_opportunities_found": sum(
                    len(v) for v in all_viral_opportunities.values()
                ),
                "niches_with_velocity_data": len(all_topic_velocities),
                "niches_with_thumbnail_analysis": len(all_thumbnail_patterns),
                "ai_enhanced": bool(ai_insights and "error" not in ai_insights),
            },
        )

        # Save reports
        paths = self.report_engine.save_all(report)

        logger.info(
            "pipeline_completed",
            duration_seconds=elapsed,
            niches=len(top_niches),
            blueprints=sum(len(v) for v in video_blueprints.values()),
            step_timings=step_timings,
        )

        return report

    async def run_discovery_pipeline(
        self,
        max_seeds: int = 20,
        deep: bool = False,
        top_n: int | None = None,
        videos_per_niche: int | None = None,
    ) -> NicheReport:
        """Automatic discovery mode — no user seed keywords required.

        Uses the DiscoveryEngine to find trending topics, then feeds
        them through the standard analysis pipeline.
        """
        if deep:
            max_seeds = max(max_seeds, 50)
            if top_n is None:
                top_n = 50

        logger.info("discovery_pipeline_started", deep=deep, max_seeds=max_seeds)

        discovered = await self.discovery_engine.discover_topics(
            max_seeds=max_seeds, deep=deep
        )

        if not discovered:
            logger.warning("no_topics_discovered")
            discovered_keywords = ["youtube growth", "content creation", "side hustle"]
        else:
            discovered_keywords = [d.topic for d in discovered]

        logger.info("discovery_seeds_generated", count=len(discovered_keywords))

        report = await self.run_full_pipeline(
            seed_keywords=discovered_keywords,
            top_n=top_n,
            videos_per_niche=videos_per_niche,
        )

        # Enrich metadata with discovery info
        report.metadata["discovery_mode"] = True
        report.metadata["deep_mode"] = deep
        report.metadata["auto_discovered_seeds"] = len(discovered_keywords)
        report.metadata["discovery_sources"] = list(
            {d.source for d in discovered}
        ) if discovered else []

        return report

    async def close(self) -> None:
        """Close all connector HTTP clients."""
        await asyncio.gather(
            self.yt_autocomplete.close(),
            self.yt_search.close(),
            self.google_trends.close(),
            self.reddit.close(),
            self.keyword_scraper.close(),
            return_exceptions=True,
        )
