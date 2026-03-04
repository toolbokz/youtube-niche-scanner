"""Tests for configuration."""
from __future__ import annotations

from app.config.settings import Settings, load_settings, reset_settings


def test_default_settings() -> None:
    reset_settings()
    settings = load_settings("/nonexistent/path.yaml")
    assert settings.app.name == "Growth Strategist"
    assert settings.database.url == "sqlite:///data/db/growth_strategist.db"
    assert settings.ranking.weights.demand == 0.30
    reset_settings()


def test_settings_weights_sum() -> None:
    settings = Settings()
    w = settings.ranking.weights
    total = w.demand + w.competition + w.trend_momentum + w.virality + w.ctr_potential + w.faceless_viability
    assert abs(total - 1.0) < 0.001


def test_connector_configs() -> None:
    settings = Settings()
    assert settings.connectors.youtube_autocomplete.enabled is True
    assert settings.connectors.youtube_data_api.enabled is False
    assert settings.connectors.youtube_search.rate_limit_per_second == 1.0


def test_analysis_config() -> None:
    settings = Settings()
    assert settings.analysis.max_keywords_per_batch == 500
    assert settings.analysis.top_niches_count == 20
    assert settings.analysis.videos_per_niche == 10
