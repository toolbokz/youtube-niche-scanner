"""Niche Ranking Engine - weighted scoring model for niche prioritization."""
from __future__ import annotations

from typing import Any

from app.config import get_settings
from app.core.logging import get_logger
from app.core.models import (
    CompetitionMetrics,
    CTRMetrics,
    FacelessViability,
    NicheScore,
    ViralityMetrics,
)

logger = get_logger(__name__)


class NicheRankingEngine:
    """Rank niches using a weighted scoring algorithm.

    Niche Score =
      0.30 * Demand Score
    + 0.25 * (100 - Competition Score)  # Lower competition = higher opportunity
    + 0.15 * Trend Momentum
    + 0.15 * Virality Score
    + 0.10 * CTR Potential
    + 0.05 * Faceless Viability
    """

    def __init__(self) -> None:
        settings = get_settings()
        self.weights = settings.ranking.weights

    def rank_niches(
        self,
        niche_data: dict[str, dict[str, Any]],
    ) -> list[NicheScore]:
        """Rank niches given aggregated analysis data.

        Args:
            niche_data: Dict mapping niche name to a dict with keys:
                - demand_score (float 0-100)
                - competition (CompetitionMetrics)
                - trend_momentum (float 0-100)
                - virality (ViralityMetrics)
                - ctr (CTRMetrics)
                - faceless (FacelessViability)
                - keywords (list[str])
        """
        scores: list[NicheScore] = []

        for niche_name, data in niche_data.items():
            demand = float(data.get("demand_score", 50.0))

            competition: CompetitionMetrics | None = data.get("competition")
            comp_raw = competition.competition_score if competition else 50.0
            # Invert: low competition = high opportunity
            comp_opportunity = 100.0 - comp_raw

            trend = float(data.get("trend_momentum", 50.0))

            virality: ViralityMetrics | None = data.get("virality")
            vir_score = virality.virality_probability if virality else 50.0

            ctr: CTRMetrics | None = data.get("ctr")
            ctr_score = ctr.ctr_potential if ctr else 50.0

            faceless: FacelessViability | None = data.get("faceless")
            face_score = faceless.faceless_viability_score if faceless else 50.0

            # Weighted composite
            overall = (
                demand * self.weights.demand
                + comp_opportunity * self.weights.competition
                + trend * self.weights.trend_momentum
                + vir_score * self.weights.virality
                + ctr_score * self.weights.ctr_potential
                + face_score * self.weights.faceless_viability
            )

            # Normalize to 0-100
            overall = max(0.0, min(100.0, overall))

            scores.append(NicheScore(
                niche=niche_name,
                demand_score=round(demand, 1),
                competition_score=round(comp_raw, 1),
                trend_momentum=round(trend, 1),
                virality_score=round(vir_score, 1),
                ctr_potential=round(ctr_score, 1),
                faceless_viability=round(face_score, 1),
                overall_score=round(overall, 1),
                keywords=data.get("keywords", []),
            ))

        # Sort and assign ranks
        scores.sort(key=lambda s: s.overall_score, reverse=True)
        for i, score in enumerate(scores):
            score.rank = i + 1

        logger.info("niches_ranked", total=len(scores))
        return scores

    def get_top_niches(
        self,
        niche_data: dict[str, dict[str, Any]],
        top_n: int | None = None,
    ) -> list[NicheScore]:
        """Rank and return top N niches."""
        if top_n is None:
            top_n = get_settings().analysis.top_niches_count

        all_ranked = self.rank_niches(niche_data)
        return all_ranked[:top_n]
