"""Tests for the Video Factory pipeline.

Tests cover:
- Concept generation
- Script generation
- Voice generation (placeholder)
- Subtitle generation
- Thumbnail generation
- Metadata generation
- Video assembly pipeline
- Factory orchestrator
- Job manager

All AI and external APIs are mocked.
"""
from __future__ import annotations

import asyncio
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.config.settings import reset_settings, load_settings
from app.video_factory.models import (
    JobStatus,
    VideoConcept,
    VideoScript,
    ScriptSection,
    VoiceConfig,
    VoiceoverResult,
    ClipSelectionResult,
    ClipSource,
    VideoTimeline,
    TimelineEntry,
    AssemblyConfig,
    AssemblyResult,
    SubtitleEntry,
    SubtitleResult,
    ThumbnailConcept,
    ThumbnailResult,
    VideoMetadata,
    VideoFactoryOutput,
    FactoryJob,
)


def setup_module() -> None:
    reset_settings()
    load_settings()


# ── Fixtures ───────────────────────────────────────────────────────────────────

def _sample_concept() -> VideoConcept:
    return VideoConcept(
        title="What Nobody Tells You About Passive Income",
        concept="An exploration of passive income myths and realities",
        target_audience="People aged 25-40 interested in financial freedom",
        engagement_hook="Did you know 90% of passive income advice is wrong?",
        emotional_trigger="curiosity",
        video_structure=["Hook", "Intro", "Main 1", "Main 2", "Conclusion", "CTA"],
        estimated_duration_minutes=8,
        niche="passive income",
    )


def _sample_script() -> VideoScript:
    sections = [
        ScriptSection(
            section_type="hook",
            section_title="Opening Hook",
            content="What if everything you know about passive income is wrong?",
            duration_seconds=10,
            visual_notes="Shocking statistic on screen",
            transition_note="Quick cut",
        ),
        ScriptSection(
            section_type="intro",
            section_title="Introduction",
            content="Welcome back. Today we dive into passive income myths.",
            duration_seconds=25,
            visual_notes="Channel branding",
            transition_note="Smooth transition",
        ),
        ScriptSection(
            section_type="main_1",
            section_title="The Myths",
            content="Most people think passive income means doing nothing. But the reality is very different.",
            duration_seconds=90,
            visual_notes="Data visualizations",
            transition_note="Bridge to next section",
        ),
        ScriptSection(
            section_type="conclusion",
            section_title="Conclusion",
            content="The key takeaway is that passive income requires upfront work.",
            duration_seconds=30,
            visual_notes="Summary graphic",
            transition_note="",
        ),
        ScriptSection(
            section_type="cta",
            section_title="Call to Action",
            content="Like and subscribe for more passive income content!",
            duration_seconds=15,
            visual_notes="Subscribe animation",
            transition_note="",
        ),
    ]
    return VideoScript(
        title="What Nobody Tells You About Passive Income",
        sections=sections,
        total_word_count=80,
        estimated_duration_seconds=170,
        target_audience="People interested in passive income",
        tone="engaging",
    )


def _sample_voiceover() -> VoiceoverResult:
    return VoiceoverResult(
        audio_path="/tmp/test_voiceover.wav",
        duration_seconds=170.0,
        provider="placeholder",
        sample_rate=24000,
        sections_timestamps=[
            {"section_index": 0, "section_type": "hook", "start_time": 0, "end_time": 10, "duration": 10},
            {"section_index": 1, "section_type": "intro", "start_time": 10, "end_time": 35, "duration": 25},
            {"section_index": 2, "section_type": "main_1", "start_time": 35, "end_time": 125, "duration": 90},
            {"section_index": 3, "section_type": "conclusion", "start_time": 125, "end_time": 155, "duration": 30},
            {"section_index": 4, "section_type": "cta", "start_time": 155, "end_time": 170, "duration": 15},
        ],
    )


def _sample_clips() -> ClipSelectionResult:
    return ClipSelectionResult(
        clips=[
            ClipSource(section_index=0, section_title="Hook", source_type="stock", duration_seconds=10),
            ClipSource(section_index=1, section_title="Intro", source_type="stock", duration_seconds=25),
            ClipSource(section_index=2, section_title="Main", source_type="stock", duration_seconds=90),
            ClipSource(section_index=3, section_title="Conclusion", source_type="stock", duration_seconds=30),
            ClipSource(section_index=4, section_title="CTA", source_type="text_overlay", duration_seconds=15),
        ],
        total_clips=5,
        total_duration_seconds=170,
        coverage_pct=100.0,
    )


# ── Model Tests ────────────────────────────────────────────────────────────────

class TestModels:
    def test_job_status_enum(self) -> None:
        assert JobStatus.QUEUED.value == "queued"
        assert JobStatus.COMPLETED.value == "completed"
        assert JobStatus.FAILED.value == "failed"

    def test_video_concept_model(self) -> None:
        concept = _sample_concept()
        assert concept.niche == "passive income"
        assert concept.title == "What Nobody Tells You About Passive Income"
        data = concept.model_dump()
        assert data["emotional_trigger"] == "curiosity"

    def test_video_script_model(self) -> None:
        script = _sample_script()
        assert len(script.sections) == 5
        assert script.sections[0].section_type == "hook"
        assert script.estimated_duration_seconds == 170

    def test_factory_job_model(self) -> None:
        job = FactoryJob(job_id="abc123", niche="test", status=JobStatus.QUEUED)
        assert job.progress_pct == 0.0
        assert job.stages_completed == []

    def test_video_factory_output_model(self) -> None:
        output = VideoFactoryOutput(job_id="abc123", niche="test")
        assert output.status == JobStatus.QUEUED
        assert output.video_path == ""


# ── Concept Engine Tests ───────────────────────────────────────────────────────

class TestConceptEngine:
    def test_fallback_concept(self) -> None:
        from app.video_factory.concept_engine import ConceptEngine

        engine = ConceptEngine()
        concept = engine._fallback_concept("passive income")
        assert "passive income" in concept.concept.lower() or "passive income" in concept.niche
        assert concept.title != ""
        assert len(concept.video_structure) > 0

    @pytest.mark.asyncio
    async def test_generate_with_mock_ai(self) -> None:
        from app.video_factory.concept_engine import ConceptEngine

        mock_result = {
            "title": "AI-Generated Title",
            "concept": "A great concept",
            "target_audience": "Everyone",
            "engagement_hook": "Check this out!",
            "emotional_trigger": "excitement",
            "video_structure": ["Hook", "Main", "CTA"],
            "estimated_duration_minutes": 10,
        }

        with patch("app.ai.client.get_ai_client") as mock_client:
            mock_client.return_value.generate_json.return_value = mock_result
            engine = ConceptEngine()
            concept = await engine.generate("test niche")
            assert concept.title == "AI-Generated Title"

    @pytest.mark.asyncio
    async def test_generate_fallback_on_ai_failure(self) -> None:
        from app.video_factory.concept_engine import ConceptEngine

        with patch("app.ai.client.get_ai_client", side_effect=Exception("No AI")):
            engine = ConceptEngine()
            concept = await engine.generate("passive income")
            assert concept.title != ""
            assert concept.niche == "passive income"


# ── Script Generator Tests ─────────────────────────────────────────────────────

class TestScriptGenerator:
    def test_fallback_script(self) -> None:
        from app.video_factory.script_generator import ScriptGenerator

        gen = ScriptGenerator()
        concept = _sample_concept()
        script = gen._fallback_script("passive income", concept)
        assert len(script.sections) > 0
        assert script.sections[0].section_type == "hook"
        assert script.sections[-1].section_type == "cta"
        assert script.total_word_count > 0

    @pytest.mark.asyncio
    async def test_generate_fallback_on_failure(self) -> None:
        from app.video_factory.script_generator import ScriptGenerator

        with patch("app.ai.client.get_ai_client", side_effect=Exception("No AI")):
            gen = ScriptGenerator()
            concept = _sample_concept()
            script = await gen.generate("passive income", concept)
            assert len(script.sections) > 0


# ── Voice Generator Tests ──────────────────────────────────────────────────────

class TestVoiceGenerator:
    @pytest.mark.asyncio
    async def test_placeholder_generation(self) -> None:
        from app.video_factory.voice_generator import VoiceGenerator

        with tempfile.TemporaryDirectory() as tmpdir:
            gen = VoiceGenerator(config=VoiceConfig(provider="placeholder"))
            script = _sample_script()
            result = await gen.generate(script, tmpdir)
            assert result.provider == "placeholder"
            assert result.duration_seconds > 0
            assert os.path.exists(result.audio_path)
            assert len(result.sections_timestamps) == len(script.sections)

    def test_estimate_timestamps(self) -> None:
        from app.video_factory.voice_generator import VoiceGenerator

        script = _sample_script()
        timestamps = VoiceGenerator._estimate_timestamps(script, 170.0)
        assert len(timestamps) == 5
        assert timestamps[0]["start_time"] == 0.0
        assert timestamps[-1]["end_time"] > 0


# ── Clip Selector Tests ───────────────────────────────────────────────────────

class TestClipSelector:
    def test_generate_default_clips(self) -> None:
        from app.video_factory.clip_selector import ClipSelector

        selector = ClipSelector()
        script = _sample_script()
        clips = selector._generate_default_clips("passive income", script)
        assert len(clips) == len(script.sections)
        assert clips[0].section_index == 0


# ── Video Assembler Tests ─────────────────────────────────────────────────────

class TestVideoAssembler:
    def test_build_timeline(self) -> None:
        from app.video_factory.video_assembler import VideoAssembler

        assembler = VideoAssembler()
        script = _sample_script()
        clips = _sample_clips()
        voiceover = _sample_voiceover()

        timeline = assembler.build_timeline(script, clips, voiceover)
        assert len(timeline.entries) == len(script.sections)
        assert timeline.total_duration_seconds > 0
        assert timeline.has_intro  # hook entry
        assert timeline.has_outro  # cta entry

    def test_timeline_ordering(self) -> None:
        from app.video_factory.video_assembler import VideoAssembler

        assembler = VideoAssembler()
        script = _sample_script()
        clips = _sample_clips()
        voiceover = _sample_voiceover()

        timeline = assembler.build_timeline(script, clips, voiceover)
        times = [e.start_time for e in timeline.entries]
        assert times == sorted(times), "Timeline entries should be in chronological order"


# ── Subtitle Generator Tests ──────────────────────────────────────────────────

class TestSubtitleGenerator:
    @pytest.mark.asyncio
    async def test_generate_subtitles(self) -> None:
        from app.video_factory.subtitle_generator import SubtitleGenerator

        with tempfile.TemporaryDirectory() as tmpdir:
            gen = SubtitleGenerator()
            script = _sample_script()
            voiceover = _sample_voiceover()

            result = await gen.generate(script, voiceover, tmpdir)
            assert result.total_entries > 0
            assert os.path.exists(result.srt_path)

            # Verify SRT format
            content = Path(result.srt_path).read_text()
            assert "-->" in content
            assert "1\n" in content

    def test_split_into_sentences(self) -> None:
        from app.video_factory.subtitle_generator import SubtitleGenerator

        sentences = SubtitleGenerator._split_into_sentences(
            "Hello world. This is a test! Is it working? Yes it is."
        )
        assert len(sentences) == 4

    def test_srt_time_format(self) -> None:
        from app.video_factory.subtitle_generator import _format_srt_time

        assert _format_srt_time(0.0) == "00:00:00,000"
        assert _format_srt_time(61.5) == "00:01:01,500"
        assert _format_srt_time(3661.123) == "01:01:01,123"


# ── Thumbnail Generator Tests ─────────────────────────────────────────────────

class TestThumbnailGenerator:
    def test_hex_to_rgb(self) -> None:
        from app.video_factory.thumbnail_generator import ThumbnailGenerator

        assert ThumbnailGenerator._hex_to_rgb("#FF0000") == (255, 0, 0)
        assert ThumbnailGenerator._hex_to_rgb("#00FF00") == (0, 255, 0)
        assert ThumbnailGenerator._hex_to_rgb("invalid") == (128, 128, 128)

    @pytest.mark.asyncio
    async def test_generate_placeholder_thumbnail(self) -> None:
        from app.video_factory.thumbnail_generator import ThumbnailGenerator

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "thumb.png")
            result = ThumbnailGenerator._create_placeholder_thumbnail(path)
            assert result is True
            assert os.path.exists(path)
            assert os.path.getsize(path) > 0


# ── Metadata Generator Tests ──────────────────────────────────────────────────

class TestMetadataGenerator:
    def test_fallback_metadata(self) -> None:
        from app.video_factory.metadata_generator import MetadataGenerator

        gen = MetadataGenerator()
        concept = _sample_concept()
        script = _sample_script()
        metadata = gen._fallback_metadata("passive income", concept, script)

        assert metadata.title != ""
        assert len(metadata.tags) > 0
        assert len(metadata.chapters) > 0
        assert "passive income" in metadata.description.lower()

    @pytest.mark.asyncio
    async def test_generate_writes_json(self) -> None:
        from app.video_factory.metadata_generator import MetadataGenerator

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("app.ai.client.get_ai_client", side_effect=Exception("No AI")):
                gen = MetadataGenerator()
                concept = _sample_concept()
                script = _sample_script()

                metadata = await gen.generate("passive income", concept, script, tmpdir)
                assert metadata.title != ""

                # Check JSON was written
                json_path = os.path.join(tmpdir, "metadata.json")
                assert os.path.exists(json_path)
                data = json.loads(Path(json_path).read_text())
                assert "title" in data


# ── Factory Orchestrator Tests ─────────────────────────────────────────────────

class TestFactoryOrchestrator:
    @pytest.mark.asyncio
    async def test_full_pipeline_with_mocks(self) -> None:
        """Test the full pipeline by mocking all AI calls."""
        from app.video_factory.factory_orchestrator import FactoryOrchestrator

        with tempfile.TemporaryDirectory() as tmpdir:
            orchestrator = FactoryOrchestrator(
                output_base=tmpdir,
                voice_config=VoiceConfig(provider="placeholder"),
                assembly_config=AssemblyConfig(use_gpu=False),
            )

            # Mock the AI client to avoid actual API calls
            mock_concept = {
                "title": "Test Video",
                "concept": "A test concept",
                "target_audience": "Testers",
                "engagement_hook": "Check this!",
                "emotional_trigger": "curiosity",
                "video_structure": ["Hook", "Main", "CTA"],
                "estimated_duration_minutes": 5,
            }

            with patch("app.ai.client.get_ai_client") as mock_ai:
                mock_ai.return_value.generate_json.return_value = mock_concept
                mock_ai.return_value.available = True
                # Side-effect-free mock — all engines will use fallback
                # since generate_json returns a dict (concept engine) and the
                # rest fall through to their own fallback paths on error
                mock_ai.return_value.generate_flash.side_effect = Exception("skip")

                output = await orchestrator.run(
                    "test niche",
                    assembly_config=AssemblyConfig(use_gpu=False),
                )

                assert output.status == JobStatus.COMPLETED
                assert output.concept.title == "Test Video"
                assert len(output.script.sections) > 0
                assert output.voiceover.duration_seconds > 0
                assert output.subtitles.total_entries > 0
                assert output.metadata.title != ""


# ── Job Manager Tests ──────────────────────────────────────────────────────────

class TestJobManager:
    def test_create_job(self) -> None:
        from app.video_factory.job_manager import FactoryJobManager

        manager = FactoryJobManager()
        assert len(manager.jobs) == 0

    def test_get_nonexistent_job(self) -> None:
        from app.video_factory.job_manager import FactoryJobManager

        manager = FactoryJobManager()
        assert manager.get_job("nonexistent") is None

    def test_list_empty_jobs(self) -> None:
        from app.video_factory.job_manager import FactoryJobManager

        manager = FactoryJobManager()
        assert manager.list_jobs() == []

    def test_singleton(self) -> None:
        from app.video_factory.job_manager import get_job_manager

        m1 = get_job_manager()
        m2 = get_job_manager()
        assert m1 is m2
