"""Tests for analysis engines (unit tests using mock/synthetic data)."""
from __future__ import annotations

from app.virality_prediction.engine import ViralityPredictionEngine
from app.ctr_prediction.engine import CTRPredictionEngine
from app.faceless_viability.engine import FacelessViabilityEngine
from app.niche_clustering.engine import NicheClusteringEngine
from app.ranking_engine.engine import NicheRankingEngine
from app.core.models import CompetitionMetrics, ViralityMetrics, CTRMetrics, FacelessViability
from app.config.settings import reset_settings, load_settings


def setup_module() -> None:
    reset_settings()
    load_settings()


# ── Virality Engine ────────────────────────────────────────────────────────────

def test_virality_engine_basic() -> None:
    engine = ViralityPredictionEngine()
    metrics = engine.analyze_niche("shocking truth about money secrets", ["money", "secrets", "hidden truth"])
    assert 0 <= metrics.virality_probability <= 100
    assert metrics.curiosity_gap > 0
    assert metrics.emotional_trigger >= 0


def test_virality_engine_low_viral() -> None:
    engine = ViralityPredictionEngine()
    metrics = engine.analyze_niche("basic gardening", ["soil", "plants", "watering"])
    assert metrics.virality_probability < 80


def test_virality_batch() -> None:
    engine = ViralityPredictionEngine()
    results = engine.analyze_batch({
        "tech": ["ai", "software"],
        "cooking": ["recipe", "meal"],
    })
    assert len(results) == 2
    assert "tech" in results
    assert "cooking" in results


# ── CTR Engine ─────────────────────────────────────────────────────────────────

def test_ctr_engine_basic() -> None:
    engine = CTRPredictionEngine()
    metrics = engine.analyze_niche("top 10 secret money hacks", ["money", "hack", "secret"])
    assert 0 <= metrics.ctr_potential <= 100
    assert metrics.power_words_score > 0


def test_ctr_engine_numbers() -> None:
    engine = CTRPredictionEngine()
    metrics = engine.analyze_niche("5 best investments", ["investing", "top 5"])
    assert metrics.numbers_lists_score > 0


# ── Faceless Engine ────────────────────────────────────────────────────────────

def test_faceless_engine_screen_recording() -> None:
    engine = FacelessViabilityEngine()
    result = engine.analyze_niche("programming tutorial", ["coding", "software", "tutorial"])
    assert result.faceless_viability_score > 30
    assert result.screen_recording_score > 0


def test_faceless_engine_stock_footage() -> None:
    engine = FacelessViabilityEngine()
    result = engine.analyze_niche("travel documentary", ["nature", "wildlife", "travel"])
    assert result.stock_footage_score > 0


def test_faceless_engine_camera_penalty() -> None:
    engine = FacelessViabilityEngine()
    result = engine.analyze_niche("vlog day in my life", ["vlog", "daily routine"])
    # Should have lower score due to camera requirement
    result2 = engine.analyze_niche("data science tutorial", ["programming", "coding", "software"])
    assert result.faceless_viability_score <= result2.faceless_viability_score


# ── Clustering Engine ──────────────────────────────────────────────────────────

def test_clustering_basic() -> None:
    engine = NicheClusteringEngine(min_cluster_size=2)
    keywords = [
        "python tutorial", "learn python", "python basics",
        "javascript tutorial", "learn javascript", "javascript basics",
        "web development guide", "frontend development", "backend development",
    ]
    clusters = engine.cluster_keywords(keywords)
    assert len(clusters) > 0
    total_kws = sum(c.size for c in clusters)
    assert total_kws > 0


def test_clustering_small_input() -> None:
    engine = NicheClusteringEngine()
    clusters = engine.cluster_keywords(["python"])
    assert len(clusters) == 1


def test_clustering_empty() -> None:
    engine = NicheClusteringEngine()
    clusters = engine.cluster_keywords([])
    assert len(clusters) == 0


# ── Ranking Engine ─────────────────────────────────────────────────────────────

def test_ranking_engine() -> None:
    engine = NicheRankingEngine()

    niche_data = {
        "high_opp": {
            "demand_score": 90.0,
            "competition": CompetitionMetrics(niche="high_opp", competition_score=20.0),
            "trend_momentum": 85.0,
            "virality": ViralityMetrics(niche="high_opp", virality_probability=80.0),
            "ctr": CTRMetrics(niche="high_opp", ctr_potential=75.0),
            "faceless": FacelessViability(niche="high_opp", faceless_viability_score=90.0),
            "keywords": ["test"],
        },
        "low_opp": {
            "demand_score": 30.0,
            "competition": CompetitionMetrics(niche="low_opp", competition_score=90.0),
            "trend_momentum": 20.0,
            "virality": ViralityMetrics(niche="low_opp", virality_probability=25.0),
            "ctr": CTRMetrics(niche="low_opp", ctr_potential=30.0),
            "faceless": FacelessViability(niche="low_opp", faceless_viability_score=40.0),
            "keywords": ["test"],
        },
    }

    ranked = engine.rank_niches(niche_data)
    assert len(ranked) == 2
    assert ranked[0].niche == "high_opp"
    assert ranked[0].rank == 1
    assert ranked[1].rank == 2
    assert ranked[0].overall_score > ranked[1].overall_score


def test_ranking_top_n() -> None:
    engine = NicheRankingEngine()
    niche_data = {
        f"niche_{i}": {
            "demand_score": float(50 + i),
            "keywords": ["test"],
        }
        for i in range(20)
    }
    top = engine.get_top_niches(niche_data, top_n=5)
    assert len(top) == 5
    assert top[0].rank == 1
