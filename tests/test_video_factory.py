"""Tests for the Video Factory — Compilation Pipeline.

Tests cover models, YouTube downloader, segment extractor, clip validator,
copyright guard, compilation assembler, factory orchestrator, and job manager.
All external calls (yt-dlp, ffmpeg, ffprobe, AI) are mocked.
"""
from __future__ import annotations

import asyncio
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

import pytest

from app.video_factory.models import (
    AssemblyConfig,
    AssemblyResult,
    CompilationTimeline,
    CompilationTimelineEntry,
    CopyrightIssueInfo,
    CopyrightReportInfo,
    DownloadedVideoInfo,
    DownloadStageResult,
    ExtractedClipInfo,
    ExtractionStageResult,
    FactoryJob,
    JobStatus,
    ThumbnailConcept,
    ThumbnailResult,
    VideoFactoryOutput,
    VideoMetadata,
    VideoOrientation,
    VideoSettings,
)


# ═══════════════════════════════════════════════════════════════════════
#  Shared fixtures / helpers
# ═══════════════════════════════════════════════════════════════════════

def _sample_settings(
    duration: int = 5,
    orientation: VideoOrientation = VideoOrientation.LANDSCAPE,
) -> VideoSettings:
    return VideoSettings(
        target_duration_minutes=duration,
        orientation=orientation,
        max_source_resolution=1080,
        transition_style="crossfade",
        use_gpu=False,
        copyright_strict=False,
    )


def _sample_downloaded_videos() -> list[DownloadedVideoInfo]:
    return [
        DownloadedVideoInfo(
            video_id="vid_001",
            title="Source Video 1",
            file_path="/tmp/test/source_videos/vid_001.mp4",
            duration_seconds=600.0,
            width=1920,
            height=1080,
            file_size_mb=120.0,
        ),
        DownloadedVideoInfo(
            video_id="vid_002",
            title="Source Video 2",
            file_path="/tmp/test/source_videos/vid_002.mp4",
            duration_seconds=480.0,
            width=1920,
            height=1080,
            file_size_mb=95.0,
        ),
    ]


def _sample_clips() -> list[ExtractedClipInfo]:
    return [
        ExtractedClipInfo(
            clip_id="clip_000",
            source_video_id="vid_001",
            file_path="/tmp/test/clips/clip_000.mp4",
            start_seconds=10.0,
            end_seconds=30.0,
            duration_seconds=20.0,
            segment_type="hook",
            energy_level="high",
            position=0,
            width=1920,
            height=1080,
            file_size_mb=4.5,
            is_valid=True,
        ),
        ExtractedClipInfo(
            clip_id="clip_001",
            source_video_id="vid_001",
            file_path="/tmp/test/clips/clip_001.mp4",
            start_seconds=120.0,
            end_seconds=180.0,
            duration_seconds=60.0,
            segment_type="highlight",
            energy_level="medium",
            position=1,
            width=1920,
            height=1080,
            file_size_mb=12.0,
            is_valid=True,
        ),
        ExtractedClipInfo(
            clip_id="clip_002",
            source_video_id="vid_002",
            file_path="/tmp/test/clips/clip_002.mp4",
            start_seconds=45.0,
            end_seconds=90.0,
            duration_seconds=45.0,
            segment_type="reaction",
            energy_level="high",
            position=2,
            width=1920,
            height=1080,
            file_size_mb=9.0,
            is_valid=True,
        ),
    ]


def _sample_timeline() -> CompilationTimeline:
    return CompilationTimeline(
        entries=[
            CompilationTimelineEntry(
                position=0,
                clip_id="clip_000",
                clip_file_path="/tmp/test/clips/clip_000.mp4",
                source_video_id="vid_001",
                start_seconds=10.0,
                end_seconds=30.0,
                duration_seconds=20.0,
                segment_type="hook",
                energy_level="high",
                transition="fade_in",
            ),
            CompilationTimelineEntry(
                position=1,
                clip_id="clip_001",
                clip_file_path="/tmp/test/clips/clip_001.mp4",
                source_video_id="vid_001",
                start_seconds=120.0,
                end_seconds=180.0,
                duration_seconds=60.0,
                segment_type="highlight",
                energy_level="medium",
                transition="crossfade",
            ),
            CompilationTimelineEntry(
                position=2,
                clip_id="clip_002",
                clip_file_path="/tmp/test/clips/clip_002.mp4",
                source_video_id="vid_002",
                start_seconds=45.0,
                end_seconds=90.0,
                duration_seconds=45.0,
                segment_type="reaction",
                energy_level="high",
                transition="fade_out",
            ),
        ],
        total_duration_seconds=125.0,
        target_duration_seconds=300.0,
    )


# ═══════════════════════════════════════════════════════════════════════
#  Model Tests
# ═══════════════════════════════════════════════════════════════════════

class TestModels:
    """Test Pydantic model creation, defaults, and computed properties."""

    def test_job_status_enum(self) -> None:
        assert JobStatus.QUEUED.value == "queued"
        assert JobStatus.DOWNLOADING_VIDEOS.value == "downloading_videos"
        assert JobStatus.COMPLETED.value == "completed"
        assert JobStatus.FAILED.value == "failed"
        # Ensure all compilation stages exist
        stages = [s.value for s in JobStatus]
        for expected in (
            "fetching_strategy", "downloading_videos", "extracting_segments",
            "validating_clips", "copyright_check", "building_timeline",
            "assembling_video", "generating_thumbnail", "generating_metadata",
            "cleaning_temp",
        ):
            assert expected in stages

    def test_video_orientation_enum(self) -> None:
        assert VideoOrientation.LANDSCAPE.value == "landscape"
        assert VideoOrientation.PORTRAIT.value == "portrait"

    def test_video_settings_landscape(self) -> None:
        s = VideoSettings(orientation=VideoOrientation.LANDSCAPE)
        assert s.resolution == "1920x1080"
        assert s.width == 1920
        assert s.height == 1080

    def test_video_settings_portrait(self) -> None:
        s = VideoSettings(orientation=VideoOrientation.PORTRAIT)
        assert s.resolution == "1080x1920"
        assert s.width == 1080
        assert s.height == 1920

    def test_video_settings_defaults(self) -> None:
        s = VideoSettings()
        assert s.target_duration_minutes == 8
        assert s.max_source_resolution == 1080
        assert s.transition_style == "crossfade"
        assert s.transition_duration == 0.5
        assert s.use_gpu is True
        assert s.reencode_clips is True
        assert s.include_audio_from_clips is True
        assert s.copyright_strict is False

    def test_downloaded_video_info(self) -> None:
        dv = DownloadedVideoInfo(
            video_id="abc123",
            title="Test Video",
            file_path="/tmp/abc123.mp4",
            duration_seconds=300.0,
            file_size_mb=50.0,
        )
        assert dv.video_id == "abc123"
        assert dv.duration_seconds == 300.0

    def test_extracted_clip_info(self) -> None:
        clip = ExtractedClipInfo(
            clip_id="clip_000",
            source_video_id="abc123",
            file_path="/tmp/clip_000.mp4",
            start_seconds=10.0,
            end_seconds=30.0,
            duration_seconds=20.0,
            segment_type="hook",
            energy_level="high",
            position=0,
            is_valid=True,
        )
        assert clip.clip_id == "clip_000"
        assert clip.duration_seconds == 20.0
        assert clip.is_valid is True

    def test_copyright_report_info_defaults(self) -> None:
        cr = CopyrightReportInfo()
        assert cr.is_safe is True
        assert cr.issues == []
        assert cr.unique_sources == 0

    def test_compilation_timeline(self) -> None:
        tl = _sample_timeline()
        assert len(tl.entries) == 3
        assert tl.total_duration_seconds == 125.0
        assert tl.target_duration_seconds == 300.0

    def test_assembly_config_defaults(self) -> None:
        ac = AssemblyConfig()
        assert ac.resolution == "1920x1080"
        assert ac.fps == 30
        assert ac.use_gpu is True

    def test_assembly_result(self) -> None:
        ar = AssemblyResult(
            draft_video_path="/tmp/draft.mp4",
            duration_seconds=125.0,
            file_size_mb=45.0,
            resolution="1920x1080",
            clips_used=3,
        )
        assert ar.clips_used == 3
        assert ar.file_size_mb == 45.0

    def test_thumbnail_result(self) -> None:
        tr = ThumbnailResult(thumbnail_path="/tmp/thumb.png")
        assert tr.width == 1280
        assert tr.height == 720

    def test_video_metadata(self) -> None:
        m = VideoMetadata(
            title="Best Compilation",
            description="A great compilation",
            tags=["tag1", "tag2"],
            category="Entertainment",
        )
        assert m.title == "Best Compilation"
        assert len(m.tags) == 2
        assert m.category == "Entertainment"

    def test_factory_output_defaults(self) -> None:
        out = VideoFactoryOutput()
        assert out.status == JobStatus.QUEUED
        assert out.video_path == ""
        assert out.error == ""
        assert isinstance(out.settings, VideoSettings)
        assert isinstance(out.downloads, DownloadStageResult)
        assert isinstance(out.extraction, ExtractionStageResult)
        assert isinstance(out.copyright_report, CopyrightReportInfo)
        assert isinstance(out.timeline, CompilationTimeline)

    def test_factory_job_defaults(self) -> None:
        job = FactoryJob(job_id="abc", niche="gaming")
        assert job.status == JobStatus.QUEUED
        assert job.progress_pct == 0.0
        assert isinstance(job.settings, VideoSettings)
        assert job.stages_completed == []


# ═══════════════════════════════════════════════════════════════════════
#  YouTube Downloader Tests
# ═══════════════════════════════════════════════════════════════════════

class TestYouTubeDownloader:
    def test_parse_timestamp(self) -> None:
        from app.video_factory.youtube_downloader import _parse_timestamp

        assert _parse_timestamp("2:12") == 132.0
        assert _parse_timestamp("1:05:30") == 3930.0
        assert _parse_timestamp("30") == 30.0

    @pytest.mark.asyncio
    async def test_download_source_videos_success(self) -> None:
        from app.video_factory.youtube_downloader import YouTubeDownloader

        with tempfile.TemporaryDirectory() as tmpdir:
            downloader = YouTubeDownloader(output_base=tmpdir)

            # Create a fake downloaded file so the downloader finds it
            source_dir = os.path.join(tmpdir, "test_job", "source_videos")
            os.makedirs(source_dir, exist_ok=True)
            fake_mp4 = os.path.join(source_dir, "abc123.mp4")
            Path(fake_mp4).write_bytes(b"\x00" * 1024)

            # Mock the subprocess call to simulate yt-dlp success
            mock_proc = AsyncMock()
            mock_proc.returncode = 0
            mock_proc.communicate = AsyncMock(return_value=(b"", b""))

            # Also need to handle info.json
            info_json_path = os.path.join(source_dir, "abc123.info.json")
            with open(info_json_path, "w") as f:
                json.dump({
                    "id": "abc123",
                    "title": "Test Source",
                    "duration": 300,
                    "width": 1920,
                    "height": 1080,
                }, f)

            with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
                result = await downloader.download_source_videos(
                    [{"video_id": "abc123"}],
                    "test_job",
                )

            assert len(result.downloaded) == 1
            assert result.downloaded[0].video_id == "abc123"
            assert result.source_dir == source_dir

    @pytest.mark.asyncio
    async def test_download_no_videos_raises(self) -> None:
        from app.video_factory.youtube_downloader import YouTubeDownloader

        with tempfile.TemporaryDirectory() as tmpdir:
            downloader = YouTubeDownloader(output_base=tmpdir)

            # Mock subprocess to fail
            mock_proc = AsyncMock()
            mock_proc.returncode = 1
            mock_proc.communicate = AsyncMock(return_value=(b"", b"Error!"))

            with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
                with pytest.raises(RuntimeError, match="Failed to download any source videos"):
                    await downloader.download_source_videos(
                        [{"video_id": "bad_id"}],
                        "test_job",
                    )

    @pytest.mark.asyncio
    async def test_download_skips_missing_url(self) -> None:
        from app.video_factory.youtube_downloader import YouTubeDownloader

        with tempfile.TemporaryDirectory() as tmpdir:
            downloader = YouTubeDownloader(output_base=tmpdir)

            # Provide entry with no video_id and no url
            # plus one valid entry that will also fail at download
            mock_proc = AsyncMock()
            mock_proc.returncode = 1
            mock_proc.communicate = AsyncMock(return_value=(b"", b"Error"))

            with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
                with pytest.raises(RuntimeError):
                    await downloader.download_source_videos(
                        [{"video_id": "", "url": ""}, {"video_id": "x"}],
                        "test_job",
                    )


# ═══════════════════════════════════════════════════════════════════════
#  Segment Extractor Tests
# ═══════════════════════════════════════════════════════════════════════

class TestSegmentExtractor:
    def test_parse_timestamp_formats(self) -> None:
        from app.video_factory.segment_extractor import parse_timestamp

        assert parse_timestamp("2:12") == 132.0
        assert parse_timestamp("1:05:30") == 3930.0
        assert parse_timestamp("132.5") == 132.5
        assert parse_timestamp("0:30") == 30.0

    @pytest.mark.asyncio
    async def test_extract_segments_success(self) -> None:
        from app.video_factory.segment_extractor import SegmentExtractor

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create fake source file
            src_path = os.path.join(tmpdir, "src.mp4")
            Path(src_path).write_bytes(b"\x00" * 2048)

            extractor = SegmentExtractor(output_base=tmpdir, target_resolution="1920x1080")

            segments = [
                {
                    "source_video_id": "vid_001",
                    "timestamp_start": "0:10",
                    "timestamp_end": "0:30",
                    "segment_type": "hook",
                    "energy_level": "high",
                    "position": 0,
                },
            ]
            source_lookup = {"vid_001": src_path}

            # Mock ffmpeg subprocess
            async def mock_exec(*args, **kwargs):
                # Create the output file the extractor expects
                for a in args:
                    if str(a).endswith(".mp4") and "clip_" in str(a):
                        Path(a).write_bytes(b"\x00" * 1024)
                m = AsyncMock()
                m.returncode = 0
                m.communicate = AsyncMock(return_value=(b"", b""))
                return m

            with patch("asyncio.create_subprocess_exec", side_effect=mock_exec):
                result = await extractor.extract_segments(
                    segments, source_lookup, "test_job",
                )

            assert len(result.clips) == 1
            assert result.clips[0].clip_id == "clip_000"
            assert result.clips[0].source_video_id == "vid_001"
            assert result.clips[0].duration_seconds == 20.0
            assert result.total_duration_seconds == 20.0

    @pytest.mark.asyncio
    async def test_extract_skips_short_clips(self) -> None:
        from app.video_factory.segment_extractor import SegmentExtractor

        with tempfile.TemporaryDirectory() as tmpdir:
            src_path = os.path.join(tmpdir, "src.mp4")
            Path(src_path).write_bytes(b"\x00" * 2048)

            extractor = SegmentExtractor(output_base=tmpdir)

            # Clip with 0.5s duration (below 1s min)
            segments = [
                {
                    "source_video_id": "vid_001",
                    "timestamp_start": "0:10",
                    "timestamp_end": "0:10.5",
                },
            ]
            source_lookup = {"vid_001": src_path}

            with pytest.raises(RuntimeError, match="Failed to extract"):
                await extractor.extract_segments(
                    segments, source_lookup, "test_job",
                )

    @pytest.mark.asyncio
    async def test_extract_skips_missing_source(self) -> None:
        from app.video_factory.segment_extractor import SegmentExtractor

        with tempfile.TemporaryDirectory() as tmpdir:
            extractor = SegmentExtractor(output_base=tmpdir)

            segments = [
                {
                    "source_video_id": "missing_vid",
                    "timestamp_start": "0:10",
                    "timestamp_end": "0:30",
                },
            ]
            source_lookup = {}  # no source available

            with pytest.raises(RuntimeError, match="Failed to extract"):
                await extractor.extract_segments(
                    segments, source_lookup, "test_job",
                )


# ═══════════════════════════════════════════════════════════════════════
#  Clip Validator Tests
# ═══════════════════════════════════════════════════════════════════════

class TestClipValidator:
    @pytest.mark.asyncio
    async def test_validate_valid_clip(self) -> None:
        from app.video_factory.clip_validator import ClipValidator

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a fake clip file big enough
            clip_path = os.path.join(tmpdir, "clip_000.mp4")
            Path(clip_path).write_bytes(b"\x00" * 20_000)

            validator = ClipValidator()

            # Mock ffprobe to return valid probe data
            probe_data = {
                "streams": [
                    {
                        "codec_type": "video",
                        "codec_name": "h264",
                        "width": 1920,
                        "height": 1080,
                        "duration": "20.0",
                    },
                    {
                        "codec_type": "audio",
                        "codec_name": "aac",
                    },
                ],
                "format": {"duration": "20.0"},
            }

            with patch.object(validator, "_ffprobe", return_value=probe_data):
                results = await validator.validate_clips(
                    [{"clip_id": "clip_000", "file_path": clip_path}]
                )

            assert len(results) == 1
            assert results[0].is_valid is True
            assert results[0].has_video is True
            assert results[0].has_audio is True
            assert results[0].duration_seconds == 20.0

    @pytest.mark.asyncio
    async def test_validate_all_invalid_raises(self) -> None:
        from app.video_factory.clip_validator import ClipValidator

        validator = ClipValidator()

        with pytest.raises(RuntimeError, match="All.*clips failed validation"):
            await validator.validate_clips(
                [{"clip_id": "bad_clip", "file_path": "/nonexistent/clip.mp4"}]
            )

    @pytest.mark.asyncio
    async def test_validate_too_small_file(self) -> None:
        from app.video_factory.clip_validator import ClipValidator

        with tempfile.TemporaryDirectory() as tmpdir:
            clip_path = os.path.join(tmpdir, "tiny.mp4")
            Path(clip_path).write_bytes(b"\x00" * 100)  # < 10KB min

            validator = ClipValidator()

            with pytest.raises(RuntimeError, match="All.*clips failed"):
                await validator.validate_clips(
                    [{"clip_id": "tiny", "file_path": clip_path}]
                )

    @pytest.mark.asyncio
    async def test_validate_no_video_stream(self) -> None:
        from app.video_factory.clip_validator import ClipValidator

        with tempfile.TemporaryDirectory() as tmpdir:
            clip_path = os.path.join(tmpdir, "audio_only.mp4")
            Path(clip_path).write_bytes(b"\x00" * 20_000)

            validator = ClipValidator()
            probe_data = {
                "streams": [{"codec_type": "audio", "codec_name": "aac"}],
                "format": {"duration": "10.0"},
            }

            with patch.object(validator, "_ffprobe", return_value=probe_data):
                with pytest.raises(RuntimeError, match="All.*clips failed"):
                    await validator.validate_clips(
                        [{"clip_id": "no_vid", "file_path": clip_path}]
                    )

    @pytest.mark.asyncio
    async def test_validate_resolution_mismatch_still_valid(self) -> None:
        from app.video_factory.clip_validator import ClipValidator

        with tempfile.TemporaryDirectory() as tmpdir:
            clip_path = os.path.join(tmpdir, "clip_720p.mp4")
            Path(clip_path).write_bytes(b"\x00" * 20_000)

            validator = ClipValidator(target_resolution="1920x1080")
            probe_data = {
                "streams": [
                    {
                        "codec_type": "video",
                        "codec_name": "h264",
                        "width": 1280,
                        "height": 720,
                        "duration": "15.0",
                    },
                ],
                "format": {"duration": "15.0"},
            }

            with patch.object(validator, "_ffprobe", return_value=probe_data):
                results = await validator.validate_clips(
                    [{"clip_id": "clip_720", "file_path": clip_path}]
                )

            # Resolution mismatch is a warning only — clip still valid
            assert results[0].is_valid is True
            assert results[0].width == 1280
            assert results[0].height == 720
            assert len(results[0].errors) > 0  # should have a mismatch warning


# ═══════════════════════════════════════════════════════════════════════
#  Copyright Guard Tests
# ═══════════════════════════════════════════════════════════════════════

class TestCopyrightGuard:
    def test_basic_safe_report(self) -> None:
        from app.video_factory.copyright_guard import CopyrightGuard

        guard = CopyrightGuard()
        clips = [
            {
                "clip_id": "clip_000",
                "source_video_id": "vid_001",
                "duration_seconds": 20.0,
                "start_seconds": 10.0,
                "end_seconds": 30.0,
            },
            {
                "clip_id": "clip_001",
                "source_video_id": "vid_002",
                "duration_seconds": 15.0,
                "start_seconds": 5.0,
                "end_seconds": 20.0,
            },
        ]
        source_durations = {"vid_001": 600.0, "vid_002": 480.0}

        report = guard.analyze(clips, source_durations)
        assert report.is_safe is True
        assert report.unique_sources == 2
        assert report.clips_checked == 2

    def test_excessive_source_usage_warning(self) -> None:
        from app.video_factory.copyright_guard import CopyrightGuard

        guard = CopyrightGuard(max_source_usage_pct=10.0)
        # Use 20% of a 100s video = 20s
        clips = [
            {
                "clip_id": "clip_000",
                "source_video_id": "vid_001",
                "duration_seconds": 20.0,
                "start_seconds": 0.0,
                "end_seconds": 20.0,
            },
            {
                "clip_id": "clip_001",
                "source_video_id": "vid_002",
                "duration_seconds": 5.0,
                "start_seconds": 0.0,
                "end_seconds": 5.0,
            },
        ]
        source_durations = {"vid_001": 100.0, "vid_002": 200.0}

        report = guard.analyze(clips, source_durations)
        # 20% > 10% max → warning
        assert len(report.issues) > 0
        assert any("20.0%" in i.message for i in report.issues)

    def test_strict_mode_makes_errors(self) -> None:
        from app.video_factory.copyright_guard import CopyrightGuard

        guard = CopyrightGuard(max_source_usage_pct=5.0, strict=True)
        clips = [
            {
                "clip_id": "clip_000",
                "source_video_id": "vid_001",
                "duration_seconds": 30.0,
                "start_seconds": 0.0,
                "end_seconds": 30.0,
            },
            {
                "clip_id": "clip_001",
                "source_video_id": "vid_002",
                "duration_seconds": 5.0,
                "start_seconds": 0.0,
                "end_seconds": 5.0,
            },
        ]
        source_durations = {"vid_001": 100.0, "vid_002": 200.0}

        report = guard.analyze(clips, source_durations)
        assert report.is_safe is False
        assert any(i.severity == "error" for i in report.issues)

    def test_no_clips_is_unsafe(self) -> None:
        from app.video_factory.copyright_guard import CopyrightGuard

        guard = CopyrightGuard()
        report = guard.analyze([], {})
        assert report.is_safe is False
        assert len(report.issues) > 0

    def test_single_source_warning(self) -> None:
        from app.video_factory.copyright_guard import CopyrightGuard

        guard = CopyrightGuard(min_unique_sources=2)
        clips = [
            {
                "clip_id": "clip_000",
                "source_video_id": "vid_001",
                "duration_seconds": 10.0,
                "start_seconds": 0.0,
                "end_seconds": 10.0,
            },
        ]
        source_durations = {"vid_001": 600.0}

        report = guard.analyze(clips, source_durations)
        assert any("unique source" in i.message.lower() for i in report.issues)

    def test_absolute_clip_duration_warning(self) -> None:
        from app.video_factory.copyright_guard import CopyrightGuard

        guard = CopyrightGuard(max_single_clip_abs=30.0)
        clips = [
            {
                "clip_id": "clip_000",
                "source_video_id": "vid_001",
                "duration_seconds": 45.0,
                "start_seconds": 0.0,
                "end_seconds": 45.0,
            },
            {
                "clip_id": "clip_001",
                "source_video_id": "vid_002",
                "duration_seconds": 10.0,
                "start_seconds": 0.0,
                "end_seconds": 10.0,
            },
        ]
        source_durations = {"vid_001": 600.0, "vid_002": 600.0}

        report = guard.analyze(clips, source_durations)
        abs_issues = [i for i in report.issues if "45.0s" in i.message]
        assert len(abs_issues) > 0

    def test_overlapping_segments_detected(self) -> None:
        from app.video_factory.copyright_guard import CopyrightGuard

        guard = CopyrightGuard()
        clips = [
            {
                "clip_id": "clip_000",
                "source_video_id": "vid_001",
                "duration_seconds": 20.0,
                "start_seconds": 10.0,
                "end_seconds": 30.0,
            },
            {
                "clip_id": "clip_001",
                "source_video_id": "vid_001",
                "duration_seconds": 20.0,
                "start_seconds": 25.0,  # overlaps prev (25 < 30)
                "end_seconds": 45.0,
            },
            {
                "clip_id": "clip_002",
                "source_video_id": "vid_002",
                "duration_seconds": 10.0,
                "start_seconds": 0.0,
                "end_seconds": 10.0,
            },
        ]
        source_durations = {"vid_001": 600.0, "vid_002": 600.0}

        report = guard.analyze(clips, source_durations)
        overlap_issues = [i for i in report.issues if "overlap" in i.message.lower()]
        assert len(overlap_issues) > 0


# ═══════════════════════════════════════════════════════════════════════
#  Compilation Assembler Tests
# ═══════════════════════════════════════════════════════════════════════

class TestCompilationAssembler:
    def test_build_timeline_ordering(self) -> None:
        from app.video_factory.video_assembler import CompilationAssembler

        with tempfile.TemporaryDirectory() as tmpdir:
            settings = _sample_settings(duration=5)
            assembler = CompilationAssembler(settings=settings)

            clips = _sample_clips()
            # Create real files for clips
            for clip in clips:
                clip.file_path = os.path.join(tmpdir, f"{clip.clip_id}.mp4")
                Path(clip.file_path).write_bytes(b"\x00" * 1024)
            # Randomize positions
            clips[0].position = 2
            clips[1].position = 0
            clips[2].position = 1

            timeline = assembler.build_timeline(clips)

            # Should be sorted by position
            positions = [e.position for e in timeline.entries]
            assert positions == [0, 1, 2]

    def test_build_timeline_caps_at_target(self) -> None:
        from app.video_factory.video_assembler import CompilationAssembler

        with tempfile.TemporaryDirectory() as tmpdir:
            # Target = 1 minute. Total clips = 125s > 60s → should cap
            settings = _sample_settings(duration=1)
            assembler = CompilationAssembler(settings=settings)

            clips = _sample_clips()
            for clip in clips:
                clip.file_path = os.path.join(tmpdir, f"{clip.clip_id}.mp4")
                Path(clip.file_path).write_bytes(b"\x00" * 1024)

            timeline = assembler.build_timeline(clips)

            assert timeline.total_duration_seconds <= 60.0
            assert timeline.target_duration_seconds == 60.0

    def test_build_timeline_skips_invalid_clips(self) -> None:
        from app.video_factory.video_assembler import CompilationAssembler

        with tempfile.TemporaryDirectory() as tmpdir:
            settings = _sample_settings()
            assembler = CompilationAssembler(settings=settings)

            clips = _sample_clips()
            for clip in clips:
                clip.file_path = os.path.join(tmpdir, f"{clip.clip_id}.mp4")
                Path(clip.file_path).write_bytes(b"\x00" * 1024)
            clips[1].is_valid = False

            timeline = assembler.build_timeline(clips)
            assert len(timeline.entries) == 2  # 3 clips minus 1 invalid

    def test_build_timeline_first_transition_is_fade_in(self) -> None:
        from app.video_factory.video_assembler import CompilationAssembler

        with tempfile.TemporaryDirectory() as tmpdir:
            settings = _sample_settings()
            assembler = CompilationAssembler(settings=settings)
            clips = _sample_clips()
            for clip in clips:
                clip.file_path = os.path.join(tmpdir, f"{clip.clip_id}.mp4")
                Path(clip.file_path).write_bytes(b"\x00" * 1024)
            timeline = assembler.build_timeline(clips)

            assert timeline.entries[0].transition == "fade_in"

    def test_build_timeline_empty_clips(self) -> None:
        from app.video_factory.video_assembler import CompilationAssembler

        settings = _sample_settings()
        assembler = CompilationAssembler(settings=settings)
        timeline = assembler.build_timeline([])

        assert len(timeline.entries) == 0
        assert timeline.total_duration_seconds == 0.0

    def test_write_concat_file(self) -> None:
        from app.video_factory.video_assembler import CompilationAssembler

        with tempfile.TemporaryDirectory() as tmpdir:
            timeline = _sample_timeline()
            concat_path = os.path.join(tmpdir, "concat.txt")

            CompilationAssembler._write_concat_file(timeline, concat_path)

            content = Path(concat_path).read_text()
            lines = [l for l in content.strip().split("\n") if l.startswith("file")]
            assert len(lines) == 3
            # Should have absolute paths
            for line in lines:
                assert line.startswith("file '")
                assert "/" in line  # absolute path

    @pytest.mark.asyncio
    async def test_assemble_empty_timeline_raises(self) -> None:
        from app.video_factory.video_assembler import CompilationAssembler

        settings = _sample_settings()
        assembler = CompilationAssembler(settings=settings)

        empty_timeline = CompilationTimeline()
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(RuntimeError, match="no entries"):
                await assembler.assemble(empty_timeline, tmpdir)

    @pytest.mark.asyncio
    async def test_assemble_success(self) -> None:
        from app.video_factory.video_assembler import CompilationAssembler

        with tempfile.TemporaryDirectory() as tmpdir:
            settings = _sample_settings()
            settings.use_gpu = False

            assembler = CompilationAssembler(settings=settings)
            timeline = _sample_timeline()

            # Mock ffmpeg to create output file
            async def mock_exec(*args, **kwargs):
                # Find the output path (last positional arg)
                out_path = args[-1] if args else None
                if out_path and str(out_path).endswith(".mp4"):
                    Path(out_path).write_bytes(b"\x00" * 50_000)
                m = AsyncMock()
                m.returncode = 0
                m.communicate = AsyncMock(return_value=(b"", b""))
                return m

            with patch("asyncio.create_subprocess_exec", side_effect=mock_exec):
                result = await assembler.assemble(timeline, tmpdir)

            assert result.clips_used == 3
            assert result.duration_seconds == 125.0
            assert result.draft_video_path.endswith("draft_video.mp4")


# ═══════════════════════════════════════════════════════════════════════
#  Thumbnail Generator Tests
# ═══════════════════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════════════════
#  Factory Orchestrator Tests
# ═══════════════════════════════════════════════════════════════════════

class TestFactoryOrchestrator:
    @pytest.mark.asyncio
    async def test_orchestrator_pipeline_with_mocks(self) -> None:
        """Test the full compilation pipeline by mocking all external calls."""
        from app.video_factory.factory_orchestrator import FactoryOrchestrator
        from types import SimpleNamespace

        with tempfile.TemporaryDirectory() as tmpdir:
            settings = _sample_settings()
            orchestrator = FactoryOrchestrator(output_base=tmpdir, settings=settings)

            # Build fake strategy response
            mock_segment = SimpleNamespace(
                source_video_id="vid_001",
                timestamp_start="0:10",
                timestamp_end="0:30",
                segment_type="hook",
                energy_level="high",
                model_dump=lambda: {
                    "source_video_id": "vid_001",
                    "timestamp_start": "0:10",
                    "timestamp_end": "0:30",
                    "segment_type": "hook",
                    "energy_level": "high",
                },
            )
            mock_segment2 = SimpleNamespace(
                source_video_id="vid_002",
                timestamp_start="1:00",
                timestamp_end="1:30",
                segment_type="highlight",
                energy_level="medium",
                model_dump=lambda: {
                    "source_video_id": "vid_002",
                    "timestamp_start": "1:00",
                    "timestamp_end": "1:30",
                    "segment_type": "highlight",
                    "energy_level": "medium",
                },
            )
            mock_source = SimpleNamespace(
                video_id="vid_001",
                title="Source 1",
                channel_name="Channel 1",
                model_dump=lambda: {"video_id": "vid_001", "url": "https://youtube.com/watch?v=vid_001"},
            )
            mock_source2 = SimpleNamespace(
                video_id="vid_002",
                title="Source 2",
                channel_name="Channel 2",
                model_dump=lambda: {"video_id": "vid_002", "url": "https://youtube.com/watch?v=vid_002"},
            )
            mock_structure_item = SimpleNamespace(
                position=0,
                segment=SimpleNamespace(source_video_id="vid_001", timestamp_start="0:10"),
            )
            mock_concept = SimpleNamespace(
                title="Test Compilation",
                description="A test compilation video",
                tags=["test", "compilation"],
                target_audience="testers",
            )
            mock_editing = SimpleNamespace()

            mock_strategy = SimpleNamespace(
                niche="gaming",
                total_source_videos_found=2,
                recommended_segments=[mock_segment, mock_segment2],
                compilation_score=0.85,
                final_video_concept=mock_concept,
                source_videos=[mock_source, mock_source2],
                video_structure=[mock_structure_item],
                editing_guidance=mock_editing,
            )

            # Mock _fetch_strategy
            with patch.object(orchestrator, "_fetch_strategy", return_value=mock_strategy):
                # Mock downloads
                from app.video_factory.youtube_downloader import DownloadedVideo, DownloadResult

                # Create real files for clips
                src_dir = os.path.join(tmpdir, "test_job", "source_videos")
                clips_dir = os.path.join(tmpdir, "test_job", "clips")
                os.makedirs(src_dir, exist_ok=True)
                os.makedirs(clips_dir, exist_ok=True)

                src1 = os.path.join(src_dir, "vid_001.mp4")
                src2 = os.path.join(src_dir, "vid_002.mp4")
                Path(src1).write_bytes(b"\x00" * 5000)
                Path(src2).write_bytes(b"\x00" * 5000)

                clip1 = os.path.join(clips_dir, "clip_000.mp4")
                clip2 = os.path.join(clips_dir, "clip_001.mp4")
                Path(clip1).write_bytes(b"\x00" * 20_000)
                Path(clip2).write_bytes(b"\x00" * 20_000)

                mock_dl_result = DownloadStageResult(
                    downloaded=[
                        DownloadedVideoInfo(
                            video_id="vid_001", title="Source 1",
                            file_path=src1, duration_seconds=600.0,
                            file_size_mb=50.0,
                        ),
                        DownloadedVideoInfo(
                            video_id="vid_002", title="Source 2",
                            file_path=src2, duration_seconds=480.0,
                            file_size_mb=40.0,
                        ),
                    ],
                    source_dir=src_dir,
                    total_size_mb=90.0,
                )

                mock_ext_result = ExtractionStageResult(
                    clips=[
                        ExtractedClipInfo(
                            clip_id="clip_000", source_video_id="vid_001",
                            file_path=clip1, start_seconds=10.0, end_seconds=30.0,
                            duration_seconds=20.0, segment_type="hook",
                            energy_level="high", position=0, is_valid=True,
                        ),
                        ExtractedClipInfo(
                            clip_id="clip_001", source_video_id="vid_002",
                            file_path=clip2, start_seconds=60.0, end_seconds=90.0,
                            duration_seconds=30.0, segment_type="highlight",
                            energy_level="medium", position=1, is_valid=True,
                        ),
                    ],
                    clips_dir=clips_dir,
                    total_duration_seconds=50.0,
                    total_size_mb=2.0,
                )

                mock_validations = [
                    MagicMock(clip_id="clip_000", is_valid=True),
                    MagicMock(clip_id="clip_001", is_valid=True),
                ]

                mock_cr = CopyrightReportInfo(
                    is_safe=True, unique_sources=2,
                    source_usage={"vid_001": 3.3, "vid_002": 6.3},
                )

                mock_timeline = CompilationTimeline(
                    entries=[
                        CompilationTimelineEntry(
                            position=0, clip_id="clip_000",
                            clip_file_path=clip1,
                            source_video_id="vid_001",
                            start_seconds=10.0, end_seconds=30.0,
                            duration_seconds=20.0,
                        ),
                        CompilationTimelineEntry(
                            position=1, clip_id="clip_001",
                            clip_file_path=clip2,
                            source_video_id="vid_002",
                            start_seconds=60.0, end_seconds=90.0,
                            duration_seconds=30.0,
                        ),
                    ],
                    total_duration_seconds=50.0,
                    target_duration_seconds=300.0,
                )

                mock_assembly = AssemblyResult(
                    draft_video_path=os.path.join(tmpdir, "draft_video.mp4"),
                    duration_seconds=50.0,
                    file_size_mb=10.0,
                    resolution="1920x1080",
                    clips_used=2,
                )
                # Create the draft video file so finalize step can copy it
                Path(mock_assembly.draft_video_path).write_bytes(b"\x00" * 5000)

                mock_thumb = ThumbnailResult(
                    thumbnail_path=os.path.join(tmpdir, "thumbnail.png"),
                )
                Path(mock_thumb.thumbnail_path).write_bytes(b"\x00" * 1000)

                mock_meta = VideoMetadata(
                    title="Test Compilation",
                    description="A test",
                    tags=["gaming"],
                )

                with patch.object(orchestrator, "_download_videos", return_value=mock_dl_result), \
                     patch.object(orchestrator, "_extract_segments", return_value=mock_ext_result), \
                     patch.object(orchestrator, "_validate_clips", return_value=mock_validations), \
                     patch.object(orchestrator, "_copyright_check", return_value=mock_cr), \
                     patch.object(orchestrator, "_build_timeline", return_value=mock_timeline), \
                     patch.object(orchestrator, "_assemble_video", return_value=mock_assembly), \
                     patch.object(orchestrator, "_generate_thumbnail", return_value=mock_thumb), \
                     patch.object(orchestrator, "_generate_metadata", return_value=mock_meta):
                    output = await orchestrator.run("gaming", job_id="test_job", settings=settings)

                assert output.status == JobStatus.COMPLETED
                assert output.niche == "gaming"
                assert output.strategy_summary["title"] == "Test Compilation"
                assert len(output.downloads.downloaded) == 2
                assert len(output.extraction.clips) == 2
                assert output.copyright_report.is_safe is True
                assert output.assembly.clips_used == 2
                assert output.metadata.title == "Test Compilation"

    @pytest.mark.asyncio
    async def test_orchestrator_fails_on_strategy_error(self) -> None:
        from app.video_factory.factory_orchestrator import FactoryOrchestrator

        with tempfile.TemporaryDirectory() as tmpdir:
            settings = _sample_settings()
            orchestrator = FactoryOrchestrator(output_base=tmpdir, settings=settings)

            with patch.object(
                orchestrator, "_fetch_strategy",
                side_effect=RuntimeError("No segments found"),
            ):
                with pytest.raises(RuntimeError, match="No segments found"):
                    await orchestrator.run("bad_niche", job_id="fail_job")

    @pytest.mark.asyncio
    async def test_orchestrator_progress_callback(self) -> None:
        from app.video_factory.factory_orchestrator import FactoryOrchestrator

        with tempfile.TemporaryDirectory() as tmpdir:
            settings = _sample_settings()
            orchestrator = FactoryOrchestrator(output_base=tmpdir, settings=settings)

            progress_events: list[tuple[str, float]] = []
            orchestrator.set_progress_callback(
                lambda stage, pct: progress_events.append((stage, pct))
            )

            with patch.object(
                orchestrator, "_fetch_strategy",
                side_effect=RuntimeError("test abort"),
            ):
                with pytest.raises(RuntimeError):
                    await orchestrator.run("test", job_id="cb_job")

            # Should have reported at least "fetching_strategy" before failing
            assert len(progress_events) >= 1
            assert progress_events[0][0] == "fetching_strategy"


# ═══════════════════════════════════════════════════════════════════════
#  Job Manager Tests
# ═══════════════════════════════════════════════════════════════════════

class TestJobManager:
    def test_create_job_manager(self) -> None:
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

    @pytest.mark.asyncio
    async def test_submit_job(self) -> None:
        from app.video_factory.job_manager import FactoryJobManager

        manager = FactoryJobManager()
        settings = _sample_settings()

        # Patch the orchestrator at its import location inside _run_job
        with patch("app.video_factory.factory_orchestrator.FactoryOrchestrator") as MockOrch:
            mock_instance = MagicMock()
            mock_instance.set_progress_callback = MagicMock()

            async def mock_run(*args, **kwargs):
                return VideoFactoryOutput(status=JobStatus.COMPLETED)

            mock_instance.run = mock_run
            MockOrch.return_value = mock_instance

            job = await manager.submit_job("gaming", settings=settings)

            assert job.job_id != ""
            assert job.niche == "gaming"
            assert job.status == JobStatus.QUEUED
            assert manager.get_job(job.job_id) is not None

    def test_list_jobs_with_filter(self) -> None:
        from app.video_factory.job_manager import FactoryJobManager

        manager = FactoryJobManager()
        # Manually add jobs for testing
        job1 = FactoryJob(job_id="j1", niche="a", status=JobStatus.COMPLETED)
        job2 = FactoryJob(job_id="j2", niche="b", status=JobStatus.FAILED)
        job3 = FactoryJob(job_id="j3", niche="c", status=JobStatus.COMPLETED)
        manager._jobs = {"j1": job1, "j2": job2, "j3": job3}

        completed = manager.list_jobs(status_filter=JobStatus.COMPLETED)
        assert len(completed) == 2
        assert all(j.status == JobStatus.COMPLETED for j in completed)

        failed = manager.list_jobs(status_filter=JobStatus.FAILED)
        assert len(failed) == 1
        assert failed[0].job_id == "j2"
