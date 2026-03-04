"""Pipeline Orchestrator - coordinates the full analysis pipeline."""
from __future__ import annotations

import time
from datetime import datetime
from typing import Any

from app.config import get_settings
from app.connectors.google_trends import GoogleTrendsConnector
from app.connectors.keyword_scraper import KeywordScraperConnector
from app.connectors.reddit import RedditConnector
from app.connectors.youtube_autocomplete import YouTubeAutocompleteConnector
from app.connectors.youtube_search import YouTubeSearchConnector
from app.competition_analysis.engine import CompetitionAnalysisEngine
from app.ctr_prediction.engine import CTRPredictionEngine
from app.faceless_viability.engine import FacelessViabilityEngine
from app.keyword_expansion.engine import KeywordExpansionEngine
from app.niche_clustering.engine import NicheClusteringEngine
from app.ranking_engine.engine import NicheRankingEngine
from app.report_generation.engine import ReportGenerationEngine
from app.trend_discovery.engine import TrendDiscoveryEngine
from app.video_strategy.blueprint import BlueprintAssembler
from app.video_strategy.engine import VideoStrategyEngine
from app.virality_prediction.engine import ViralityPredictionEngine
from app.core.logging import get_logger
from app.core.models import NicheReport

logger = get_logger(__name__)


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

    async def run_full_pipeline(
        self,
        seed_keywords: list[str],
        top_n: int | None = None,
        videos_per_niche: int | None = None,
    ) -> NicheReport:
        """Execute the complete pipeline end-to-end.

        Steps:
        1. Keyword expansion
        2. Trend discovery
        3. Niche clustering
        4. Competition analysis
        5. Virality prediction
        6. CTR prediction
        7. Faceless viability
        8. Niche ranking
        9. Video strategy generation
        10. Blueprint assembly
        11. Report generation
        """
        settings = get_settings()
        if top_n is None:
            top_n = settings.analysis.top_niches_count
        if videos_per_niche is None:
            videos_per_niche = settings.analysis.videos_per_niche

        start_time = time.time()
        logger.info("pipeline_started", seeds=seed_keywords)

        # ── Step 1: Keyword Expansion ──
        logger.info("step_1_keyword_expansion")
        expanded = await self.keyword_engine.expand_batch(seed_keywords, use_prefixes=False)
        all_keywords: list[str] = list(seed_keywords)
        for kw_list in expanded.values():
            all_keywords.extend(kw_list)
        all_keywords = list(dict.fromkeys(all_keywords))  # Deduplicate
        logger.info("keywords_expanded", total=len(all_keywords))

        # ── Step 2: Trend Discovery ──
        logger.info("step_2_trend_discovery")
        # Analyze seeds + top expanded keywords
        trend_keywords = seed_keywords + all_keywords[:20]
        trend_keywords = list(dict.fromkeys(trend_keywords))[:30]
        trend_results = await self.trend_engine.discover_trends(trend_keywords)

        # Build demand scores from trends
        demand_map: dict[str, float] = {}
        for tr in trend_results:
            demand_map[tr["keyword"]] = tr["trend_momentum_score"]

        # ── Step 3: Niche Clustering ──
        logger.info("step_3_niche_clustering")
        clusters = self.clustering_engine.cluster_keywords(all_keywords, seed_keywords)
        clusters = self.clustering_engine.merge_small_clusters(clusters, min_size=3)
        logger.info("clusters_formed", count=len(clusters))

        if not clusters:
            logger.warning("no_clusters_formed")
            # Fallback: create one cluster per seed
            from app.core.models import KeywordCluster
            clusters = [
                KeywordCluster(
                    cluster_id=i,
                    name=kw,
                    keywords=[kw],
                    seed_keyword=kw,
                    size=1,
                )
                for i, kw in enumerate(seed_keywords)
            ]

        # ── Step 4-7: Analysis per niche ──
        logger.info("step_4_7_per_niche_analysis")
        niche_data: dict[str, dict[str, Any]] = {}

        for cluster in clusters:
            niche_name = cluster.name
            keywords = cluster.keywords

            # Competition (async)
            competition = await self.competition_engine.analyze_niche(niche_name, keywords)

            # Virality (sync)
            virality = self.virality_engine.analyze_niche(niche_name, keywords)

            # CTR (sync)
            ctr = self.ctr_engine.analyze_niche(niche_name, keywords)

            # Faceless (sync)
            faceless = self.faceless_engine.analyze_niche(niche_name, keywords)

            # Demand: average trend momentum of known keywords
            kw_demands = [demand_map.get(kw, 50.0) for kw in keywords if kw in demand_map]
            demand_score = sum(kw_demands) / len(kw_demands) if kw_demands else 50.0

            niche_data[niche_name] = {
                "demand_score": demand_score,
                "competition": competition,
                "trend_momentum": demand_score,  # Reuse trend as momentum
                "virality": virality,
                "ctr": ctr,
                "faceless": faceless,
                "keywords": keywords,
            }

        # ── Step 8: Niche Ranking ──
        logger.info("step_8_ranking")
        top_niches = self.ranking_engine.get_top_niches(niche_data, top_n)
        logger.info("top_niches_ranked", count=len(top_niches))

        # ── Step 9-10: Strategy & Blueprint Generation ──
        logger.info("step_9_10_strategy_generation")
        channel_concepts = []
        video_blueprints: dict[str, list[Any]] = {}

        for niche_score in top_niches:
            niche_name = niche_score.niche
            faceless_data = niche_data.get(niche_name, {}).get("faceless")

            # Channel concept
            concept = self.video_strategy_engine.generate_channel_concept(
                niche_score, faceless_data
            )
            channel_concepts.append(concept)

            # Video ideas
            ideas = self.video_strategy_engine.generate_video_ideas(
                niche_score, count=videos_per_niche
            )

            # Full blueprints
            blueprints = self.blueprint_assembler.assemble_batch(ideas, niche_score)
            video_blueprints[niche_name] = blueprints

        # ── Step 11: Report ──
        logger.info("step_11_report_generation")
        elapsed = round(time.time() - start_time, 1)

        report = self.report_engine.generate_report(
            seed_keywords=seed_keywords,
            top_niches=top_niches,
            channel_concepts=channel_concepts,
            video_blueprints=video_blueprints,
            metadata={
                "total_keywords_analyzed": len(all_keywords),
                "total_clusters": len(clusters),
                "pipeline_duration_seconds": elapsed,
            },
        )

        # Save reports
        paths = self.report_engine.save_all(report)

        logger.info(
            "pipeline_completed",
            duration_seconds=elapsed,
            niches=len(top_niches),
            blueprints=sum(len(v) for v in video_blueprints.values()),
            report_paths={k: str(v) for k, v in paths.items()},
        )

        return report

    async def close(self) -> None:
        """Close all connector HTTP clients."""
        await self.yt_autocomplete.close()
        await self.yt_search.close()
        await self.google_trends.close()
        await self.reddit.close()
        await self.keyword_scraper.close()
