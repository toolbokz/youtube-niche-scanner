"""Tests for report generation."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from app.report_generation.engine import ReportGenerationEngine
from app.core.models import NicheReport, NicheScore, ChannelConcept
from app.config.settings import reset_settings, load_settings


def setup_module() -> None:
    reset_settings()
    load_settings()


def _make_report() -> NicheReport:
    return NicheReport(
        seed_keywords=["test"],
        top_niches=[
            NicheScore(niche="test niche", overall_score=80, rank=1),
        ],
        channel_concepts=[
            ChannelConcept(niche="test niche", posting_cadence="3x/week"),
        ],
        video_blueprints={},
        metadata={"test": True},
    )


def test_json_report() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = ReportGenerationEngine(output_dir=tmpdir)
        report = _make_report()
        path = engine.save_json(report, "test.json")
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["seed_keywords"] == ["test"]
        assert len(data["top_niches"]) == 1


def test_markdown_report() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = ReportGenerationEngine(output_dir=tmpdir)
        report = _make_report()
        path = engine.save_markdown(report, "test.md")
        assert path.exists()
        content = path.read_text()
        assert "# YouTube Niche Discovery Report" in content
        assert "test niche" in content


def test_save_all() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = ReportGenerationEngine(output_dir=tmpdir)
        report = _make_report()
        paths = engine.save_all(report, "full_test")
        assert "json" in paths
        assert "markdown" in paths
        assert paths["json"].exists()
        assert paths["markdown"].exists()
