"""Tests for the AI (Vertex AI / Gemini) integration layer.

All tests mock the Vertex AI SDK so they run without GCP credentials.
"""
from __future__ import annotations

import json
from datetime import datetime
from unittest.mock import MagicMock, patch, AsyncMock

import pytest

# ══════════════════════════════════════════════════════════════════════════════
#  Client tests
# ══════════════════════════════════════════════════════════════════════════════


class TestVertexAIClient:
    """Tests for app.ai.client.VertexAIClient."""

    def test_client_not_available_without_env(self, monkeypatch):
        """Client reports not-available when env vars are missing."""
        monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
        monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)

        # Re-import to get fresh state
        from app.ai.client import VertexAIClient
        client = VertexAIClient()
        assert client.available is False

    @patch("app.ai.client.VertexAIClient._ensure_init")
    def test_client_available_with_mocked_init(self, mock_init):
        """Client reports available when _ensure_init succeeds."""
        from app.ai.client import VertexAIClient
        client = VertexAIClient()
        # _ensure_init is mocked so it won't raise
        assert client.available is True

    def test_parse_json_response_plain(self):
        """Parse vanilla JSON string."""
        from app.ai.client import _parse_json_response
        text = '{"foo": "bar", "count": 42}'
        result = _parse_json_response(text)
        assert result == {"foo": "bar", "count": 42}

    def test_parse_json_response_with_fences(self):
        """Parse JSON wrapped in ```json fences."""
        from app.ai.client import _parse_json_response
        text = '```json\n{"key": "value"}\n```'
        result = _parse_json_response(text)
        assert result == {"key": "value"}

    def test_parse_json_response_triple_backtick_no_lang(self):
        """Parse JSON wrapped in plain ``` fences."""
        from app.ai.client import _parse_json_response
        text = '```\n{"a": 1}\n```'
        result = _parse_json_response(text)
        assert result == {"a": 1}

    def test_parse_json_response_invalid(self):
        """Return None for unparseable text."""
        from app.ai.client import _parse_json_response
        assert _parse_json_response("not json at all") is None

    @patch("app.ai.client.VertexAIClient._make_config", return_value="mock_config")
    @patch("app.ai.client.VertexAIClient._ensure_init")
    def test_generate_flash(self, mock_init, mock_config):
        """generate_flash delegates to Flash model."""
        from app.ai.client import VertexAIClient
        client = VertexAIClient()
        client._initialised = True

        mock_resp = MagicMock()
        mock_resp.text = "Flash response"
        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_resp
        client._flash_model = mock_model

        result = client.generate_flash("Test prompt")
        assert result == "Flash response"
        mock_model.generate_content.assert_called_once()

    @patch("app.ai.client.VertexAIClient._make_config", return_value="mock_config")
    @patch("app.ai.client.VertexAIClient._ensure_init")
    def test_generate_pro(self, mock_init, mock_config):
        """generate_pro delegates to Pro model."""
        from app.ai.client import VertexAIClient
        client = VertexAIClient()
        client._initialised = True

        mock_resp = MagicMock()
        mock_resp.text = "Pro response"
        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_resp
        client._pro_model = mock_model

        result = client.generate_pro("Test prompt")
        assert result == "Pro response"

    @patch("app.ai.client.VertexAIClient._make_config", return_value="mock_config")
    @patch("app.ai.client.VertexAIClient._ensure_init")
    def test_generate_json_success(self, mock_init, mock_config):
        """generate_json returns parsed dict."""
        from app.ai.client import VertexAIClient
        client = VertexAIClient()
        client._initialised = True

        mock_resp = MagicMock()
        mock_resp.text = '```json\n{"ideas": [1, 2, 3]}\n```'
        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_resp
        client._flash_model = mock_model

        result = client.generate_json("Give me JSON", use_pro=False)
        assert result == {"ideas": [1, 2, 3]}

    @patch("app.ai.client.VertexAIClient._make_config", return_value="mock_config")
    @patch("app.ai.client.VertexAIClient._ensure_init")
    def test_generate_json_failure(self, mock_init, mock_config):
        """generate_json returns None on bad output."""
        from app.ai.client import VertexAIClient
        client = VertexAIClient()
        client._initialised = True

        mock_resp = MagicMock()
        mock_resp.text = "I cannot generate JSON right now"
        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_resp
        client._flash_model = mock_model

        result = client.generate_json("Give me JSON", use_pro=False)
        assert result is None

    def test_singleton_pattern(self):
        """get_ai_client returns the same instance."""
        from app.ai.client import get_ai_client
        a = get_ai_client()
        b = get_ai_client()
        assert a is b


# ══════════════════════════════════════════════════════════════════════════════
#  Prompt tests
# ══════════════════════════════════════════════════════════════════════════════


class TestPrompts:
    """Basic prompt template structure tests."""

    def test_niche_analysis_prompt(self):
        from app.ai.prompts.niche_analysis import niche_analysis_prompt
        niches = [
            {"niche": "ai tools", "overall_score": 82, "demand_score": 75},
            {"niche": "health tips", "overall_score": 70, "demand_score": 65},
        ]
        prompt = niche_analysis_prompt(niches)
        assert "ai tools" in prompt
        assert "health tips" in prompt
        assert "JSON" in prompt

    def test_quick_niche_insight_prompt(self):
        from app.ai.prompts.niche_analysis import quick_niche_insight_prompt
        data = {"niche": "crypto", "overall_score": 60}
        prompt = quick_niche_insight_prompt(data)
        assert "crypto" in prompt
        assert "quick_insight" in prompt

    def test_video_strategy_prompt(self):
        from app.ai.prompts.strategy_generation import video_strategy_prompt
        prompt = video_strategy_prompt("ai tools", ["ai", "tools"])
        assert "ai tools" in prompt
        assert "video_ideas" in prompt

    def test_viral_opportunity_prompt(self):
        from app.ai.prompts.strategy_generation import viral_opportunity_prompt
        anomalies = [{"video_title": "Trending", "video_views": 1000000}]
        prompt = viral_opportunity_prompt("ai tools", anomalies)
        assert "Trending" in prompt

    def test_trend_forecast_prompt(self):
        from app.ai.prompts.trend_interpretation import trend_forecast_prompt
        vels = {"ai": {"growth_rate": 2.5, "acceleration": 0.3, "velocity_score": 80}}
        prompt = trend_forecast_prompt(vels)
        assert "ai" in prompt
        assert "trend_forecast" in prompt

    def test_thumbnail_strategy_prompt(self):
        from app.ai.prompts.thumbnail_analysis_ai import thumbnail_strategy_prompt
        data = {
            "style_groups": [
                {"style_label": "bright", "count": 5, "avg_views": 50000,
                 "dominant_colors": ["red", "blue"], "text_prevalence": 0.8,
                 "face_prevalence": 0.6, "avg_contrast": 7.5}
            ],
            "insight": "Bold colors dominate",
            "recommendations": ["Use red backgrounds"],
            "total_analyzed": 10,
        }
        prompt = thumbnail_strategy_prompt("gaming", data)
        assert "gaming" in prompt
        assert "color_strategy" in prompt


# ══════════════════════════════════════════════════════════════════════════════
#  Service integration tests (mocked)
# ══════════════════════════════════════════════════════════════════════════════


class TestAIService:
    """Tests for app.ai.service — all Vertex AI calls mocked."""

    @pytest.fixture(autouse=True)
    def _patch_cache(self):
        """Disable DB caching for service tests."""
        with patch("app.ai.service._get_cached", new_callable=AsyncMock, return_value=None), \
             patch("app.ai.service._store_cache", new_callable=AsyncMock):
            yield

    @pytest.fixture
    def mock_client(self):
        """Provide a mock VertexAIClient that returns canned JSON."""
        client = MagicMock()
        client.available = True
        client.generate_json.return_value = {"mock": True}
        client.agenerate_json = AsyncMock(return_value={"mock": True})
        return client

    @pytest.mark.asyncio
    async def test_analyze_niches(self, mock_client):
        with patch("app.ai.service.get_ai_client", return_value=mock_client):
            from app.ai.service import analyze_niches
            result = await analyze_niches([
                {"niche": "ai tools", "overall_score": 80, "keywords": ["ai"]},
            ])
        assert "mock" in result
        mock_client.agenerate_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_interpret_viral_opportunities(self, mock_client):
        with patch("app.ai.service.get_ai_client", return_value=mock_client):
            from app.ai.service import interpret_viral_opportunities
            result = await interpret_viral_opportunities("ai tools", [
                {"video_title": "Amazing", "video_views": 500000},
            ])
        assert "mock" in result

    @pytest.mark.asyncio
    async def test_generate_video_strategy(self, mock_client):
        with patch("app.ai.service.get_ai_client", return_value=mock_client):
            from app.ai.service import generate_video_strategy
            result = await generate_video_strategy("ai tools", ["ai", "tools"])
        assert "mock" in result

    @pytest.mark.asyncio
    async def test_analyze_thumbnail_patterns(self, mock_client):
        with patch("app.ai.service.get_ai_client", return_value=mock_client):
            from app.ai.service import analyze_thumbnail_patterns
            result = await analyze_thumbnail_patterns("gaming", {
                "style_groups": [], "total_analyzed": 5,
            })
        assert "mock" in result

    @pytest.mark.asyncio
    async def test_forecast_trends(self, mock_client):
        with patch("app.ai.service.get_ai_client", return_value=mock_client):
            from app.ai.service import forecast_trends
            result = await forecast_trends(
                {"ai": {"growth_rate": 2.0, "velocity_score": 75}},
            )
        assert "mock" in result

    @pytest.mark.asyncio
    async def test_quick_niche_insight(self, mock_client):
        with patch("app.ai.service.get_ai_client", return_value=mock_client):
            from app.ai.service import get_quick_niche_insight
            result = await get_quick_niche_insight({"niche": "crypto", "overall_score": 60})
        assert "mock" in result

    @pytest.mark.asyncio
    async def test_run_full_ai_analysis(self, mock_client):
        with patch("app.ai.service.get_ai_client", return_value=mock_client):
            from app.ai.service import run_full_ai_analysis
            report = {
                "top_niches": [
                    {"niche": "ai tools", "overall_score": 80, "keywords": ["ai"]},
                ],
                "viral_opportunities": {},
                "topic_velocities": {},
                "thumbnail_patterns": {},
            }
            result = await run_full_ai_analysis(report)
        assert "niche_analysis" in result
        assert "video_strategy" in result

    @pytest.mark.asyncio
    async def test_service_returns_error_when_unavailable(self):
        """Service returns error dict when AI client is not available."""
        mock_client = MagicMock()
        mock_client.available = False
        with patch("app.ai.service.get_ai_client", return_value=mock_client):
            from app.ai.service import analyze_niches
            result = await analyze_niches([{"niche": "test"}])
        assert "error" in result


# ══════════════════════════════════════════════════════════════════════════════
#  Database model test
# ══════════════════════════════════════════════════════════════════════════════


class TestAIInsightRecord:
    """Tests for the AIInsightRecord ORM model."""

    def test_model_exists(self):
        from app.database.models import AIInsightRecord
        record = AIInsightRecord(
            cache_key="abc123",
            niche="test niche",
            analysis_type="niche_analysis",
            response={"test": True},
        )
        assert record.niche == "test niche"
        assert record.analysis_type == "niche_analysis"
        assert record.response == {"test": True}


# ══════════════════════════════════════════════════════════════════════════════
#  Config test
# ══════════════════════════════════════════════════════════════════════════════


class TestVertexAIConfig:
    """Tests for VertexAIConfig in settings."""

    def test_default_config(self):
        from app.config.settings import VertexAIConfig
        cfg = VertexAIConfig()
        assert cfg.enabled is False
        assert cfg.region == "us-central1"
        assert cfg.cache_ttl_hours == 24

    def test_settings_has_vertex_ai(self):
        from app.config.settings import Settings
        s = Settings()
        assert hasattr(s, "vertex_ai")
        assert s.vertex_ai.enabled is False


# ══════════════════════════════════════════════════════════════════════════════
#  Core model test
# ══════════════════════════════════════════════════════════════════════════════


class TestNicheReportAI:
    """Tests for the ai_insights field on NicheReport."""

    def test_niche_report_has_ai_insights(self):
        from app.core.models import NicheReport
        report = NicheReport(ai_insights={"test": True})
        assert report.ai_insights == {"test": True}

    def test_niche_report_ai_insights_default(self):
        from app.core.models import NicheReport
        report = NicheReport()
        assert report.ai_insights == {}
