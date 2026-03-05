"""Tests for the refactored Video Processing Architecture.

Covers:
- Hardware detection (GPU encoder probing, system resources)
- Segment extractor (stream copy, parallel extraction, re-encode fallback)
- Video assembler (single-pass encoding, GPU args, CPU fallback)
- Job scheduler (concurrency limiting, resource throttling)
- Config integration (VideoProcessingConfig)

All external calls (ffmpeg, ffprobe, /proc reads) are mocked.
"""
from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ═══════════════════════════════════════════════════════════════════════
#  Hardware Detector Tests
# ═══════════════════════════════════════════════════════════════════════


class TestHardwareDetector:
    """Test GPU encoder detection, binary checks, and system resource reading."""

    @pytest.mark.asyncio
    async def test_check_encoder_success(self) -> None:
        from app.video_factory.hardware_detector import _check_encoder

        async def mock_exec(*args, **kwargs):
            m = AsyncMock()
            m.returncode = 0
            m.communicate = AsyncMock(return_value=(b"", b""))
            return m

        with patch("asyncio.create_subprocess_exec", side_effect=mock_exec):
            assert await _check_encoder("h264_nvenc") is True

    @pytest.mark.asyncio
    async def test_check_encoder_failure(self) -> None:
        from app.video_factory.hardware_detector import _check_encoder

        async def mock_exec(*args, **kwargs):
            m = AsyncMock()
            m.returncode = 1
            m.communicate = AsyncMock(return_value=(b"", b"encoder not found"))
            return m

        with patch("asyncio.create_subprocess_exec", side_effect=mock_exec):
            assert await _check_encoder("h264_nvenc") is False

    @pytest.mark.asyncio
    async def test_check_encoder_exception(self) -> None:
        from app.video_factory.hardware_detector import _check_encoder

        with patch(
            "asyncio.create_subprocess_exec",
            side_effect=FileNotFoundError("ffmpeg not found"),
        ):
            assert await _check_encoder("h264_nvenc") is False

    @pytest.mark.asyncio
    async def test_check_binary_success(self) -> None:
        from app.video_factory.hardware_detector import _check_binary

        async def mock_exec(*args, **kwargs):
            m = AsyncMock()
            m.returncode = 0
            m.communicate = AsyncMock(return_value=(b"ffmpeg version 6.0", b""))
            return m

        with patch("asyncio.create_subprocess_exec", side_effect=mock_exec):
            assert await _check_binary("ffmpeg") is True

    @pytest.mark.asyncio
    async def test_check_binary_not_found(self) -> None:
        from app.video_factory.hardware_detector import _check_binary

        with patch(
            "asyncio.create_subprocess_exec",
            side_effect=FileNotFoundError,
        ):
            assert await _check_binary("ffmpeg") is False

    def test_get_cpu_count(self) -> None:
        from app.video_factory.hardware_detector import _get_cpu_count

        with patch("os.cpu_count", return_value=8):
            assert _get_cpu_count() == 8

    def test_get_cpu_count_none_fallback(self) -> None:
        from app.video_factory.hardware_detector import _get_cpu_count

        with patch("os.cpu_count", return_value=None):
            assert _get_cpu_count() == 1

    def test_get_total_memory_linux(self) -> None:
        from app.video_factory.hardware_detector import _get_total_memory_gb

        meminfo = "MemTotal:       16384000 kB\nMemFree:         8192000 kB\n"
        with patch("platform.system", return_value="Linux"), \
             patch("builtins.open", MagicMock(
                 return_value=MagicMock(
                     __enter__=lambda s: iter(meminfo.splitlines(True)),
                     __exit__=MagicMock(return_value=False),
                 ),
             )):
            result = _get_total_memory_gb()
            assert result > 0

    def test_get_system_load_keys(self) -> None:
        from app.video_factory.hardware_detector import get_system_load

        result = get_system_load()
        assert "cpu_percent" in result
        assert "memory_percent" in result
        assert isinstance(result["cpu_percent"], float)
        assert isinstance(result["memory_percent"], float)

    @pytest.mark.asyncio
    async def test_detect_hardware_no_ffmpeg(self) -> None:
        """When ffmpeg isn't found, return defaults with ffmpeg_available=False."""
        from app.video_factory.hardware_detector import detect_hardware

        async def mock_exec(*args, **kwargs):
            m = AsyncMock()
            m.returncode = 1  # not found
            m.communicate = AsyncMock(return_value=(b"", b""))
            return m

        with patch("asyncio.create_subprocess_exec", side_effect=mock_exec):
            caps = await detect_hardware()

        assert caps.ffmpeg_available is False
        assert caps.recommended_encoder == "libx264"
        assert caps.available_gpu_encoders == []

    @pytest.mark.asyncio
    async def test_detect_hardware_with_nvenc(self) -> None:
        """When NVENC is available, it should be recommended."""
        from app.video_factory.hardware_detector import detect_hardware

        call_count = 0

        async def mock_exec(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            m = AsyncMock()
            cmd_str = " ".join(str(a) for a in args)
            if "-version" in cmd_str:
                # ffmpeg / ffprobe binary check
                m.returncode = 0
            elif "h264_nvenc" in cmd_str:
                m.returncode = 0  # NVENC works
            else:
                m.returncode = 1  # Others fail
            m.communicate = AsyncMock(return_value=(b"", b""))
            return m

        with patch("asyncio.create_subprocess_exec", side_effect=mock_exec):
            caps = await detect_hardware()

        assert caps.ffmpeg_available is True
        assert "h264_nvenc" in caps.available_gpu_encoders
        assert caps.recommended_encoder == "h264_nvenc"

    @pytest.mark.asyncio
    async def test_detect_hardware_forced_encoder(self) -> None:
        """When a specific encoder is forced, only test that one."""
        from app.video_factory.hardware_detector import detect_hardware

        async def mock_exec(*args, **kwargs):
            m = AsyncMock()
            m.returncode = 0
            m.communicate = AsyncMock(return_value=(b"", b""))
            return m

        with patch("asyncio.create_subprocess_exec", side_effect=mock_exec):
            caps = await detect_hardware(prefer_encoder="h264_qsv")

        assert caps.recommended_encoder == "h264_qsv"
        assert caps.available_gpu_encoders == ["h264_qsv"]

    @pytest.mark.asyncio
    async def test_detect_hardware_forced_encoder_unavailable(self) -> None:
        """When a forced encoder isn't available, fall back to libx264."""
        from app.video_factory.hardware_detector import detect_hardware

        call_idx = 0

        async def mock_exec(*args, **kwargs):
            nonlocal call_idx
            call_idx += 1
            m = AsyncMock()
            cmd_str = " ".join(str(a) for a in args)
            if "-version" in cmd_str:
                m.returncode = 0
            else:
                m.returncode = 1  # encoder test fails
            m.communicate = AsyncMock(return_value=(b"", b""))
            return m

        with patch("asyncio.create_subprocess_exec", side_effect=mock_exec):
            caps = await detect_hardware(prefer_encoder="h264_qsv")

        assert caps.recommended_encoder == "libx264"
        assert caps.available_gpu_encoders == []

    @pytest.mark.asyncio
    async def test_detect_hardware_cpu_fallback(self) -> None:
        """When no GPU encoders are available, use libx264."""
        from app.video_factory.hardware_detector import detect_hardware

        async def mock_exec(*args, **kwargs):
            m = AsyncMock()
            cmd_str = " ".join(str(a) for a in args)
            if "-version" in cmd_str:
                m.returncode = 0
            else:
                m.returncode = 1  # all GPU encoders fail
            m.communicate = AsyncMock(return_value=(b"", b""))
            return m

        with patch("asyncio.create_subprocess_exec", side_effect=mock_exec):
            caps = await detect_hardware()

        assert caps.recommended_encoder == "libx264"
        assert caps.available_gpu_encoders == []
        assert caps.ffmpeg_available is True

    @pytest.mark.asyncio
    async def test_cached_get_hardware_capabilities(self) -> None:
        """get_hardware_capabilities caches the result."""
        import app.video_factory.hardware_detector as hd

        # Reset cache
        hd._cached = None

        async def mock_exec(*args, **kwargs):
            m = AsyncMock()
            m.returncode = 0
            m.communicate = AsyncMock(return_value=(b"", b""))
            return m

        with patch("asyncio.create_subprocess_exec", side_effect=mock_exec):
            caps1 = await hd.get_hardware_capabilities()
            caps2 = await hd.get_hardware_capabilities()

        assert caps1 is caps2  # Same object — cached

        # force_refresh gives a new object
        with patch("asyncio.create_subprocess_exec", side_effect=mock_exec):
            caps3 = await hd.get_hardware_capabilities(force_refresh=True)
        assert caps3 is not caps1

        # Clean up
        hd._cached = None

    def test_hardware_capabilities_defaults(self) -> None:
        from app.video_factory.hardware_detector import HardwareCapabilities

        caps = HardwareCapabilities()
        assert caps.available_gpu_encoders == []
        assert caps.recommended_encoder == "libx264"
        assert caps.cpu_count == 1
        assert caps.max_parallel_clips == 2
        assert caps.ffmpeg_available is False


# ═══════════════════════════════════════════════════════════════════════
#  Segment Extractor — Stream Copy & Parallel Tests
# ═══════════════════════════════════════════════════════════════════════


class TestSegmentExtractorStreamCopy:
    """Test that the segment extractor defaults to stream copy and parallel mode."""

    def test_default_is_stream_copy(self) -> None:
        from app.video_factory.segment_extractor import SegmentExtractor

        ext = SegmentExtractor()
        assert ext.reencode is False

    def test_explicit_reencode(self) -> None:
        from app.video_factory.segment_extractor import SegmentExtractor

        ext = SegmentExtractor(reencode=True)
        assert ext.reencode is True

    def test_parallel_config(self) -> None:
        from app.video_factory.segment_extractor import SegmentExtractor

        ext = SegmentExtractor(max_parallel=8)
        assert ext.max_parallel == 8

    def test_parallel_minimum_is_1(self) -> None:
        from app.video_factory.segment_extractor import SegmentExtractor

        ext = SegmentExtractor(max_parallel=0)
        assert ext.max_parallel == 1

    @pytest.mark.asyncio
    async def test_stream_copy_ffmpeg_command(self) -> None:
        """Verify that stream copy uses -c copy, not -c:v libx264."""
        from app.video_factory.segment_extractor import SegmentExtractor

        captured_cmds: list[list[str]] = []

        with tempfile.TemporaryDirectory() as tmpdir:
            src_path = os.path.join(tmpdir, "src.mp4")
            Path(src_path).write_bytes(b"\x00" * 2048)

            extractor = SegmentExtractor(
                output_base=tmpdir,
                reencode=False,
                max_parallel=2,
            )

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

            async def mock_exec(*args, **kwargs):
                captured_cmds.append(list(str(a) for a in args))
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
            # Find the extraction command (not the probe command)
            extract_cmds = [c for c in captured_cmds if "-c" in c and "copy" in c]
            assert len(extract_cmds) >= 1, f"Expected stream copy cmd, got: {captured_cmds}"

            cmd = extract_cmds[0]
            # Should have -c copy (not -c:v libx264)
            assert "copy" in cmd
            assert "libx264" not in cmd

    @pytest.mark.asyncio
    async def test_reencode_ffmpeg_command(self) -> None:
        """Verify that re-encode mode uses -c:v libx264."""
        from app.video_factory.segment_extractor import SegmentExtractor

        captured_cmds: list[list[str]] = []

        with tempfile.TemporaryDirectory() as tmpdir:
            src_path = os.path.join(tmpdir, "src.mp4")
            Path(src_path).write_bytes(b"\x00" * 2048)

            extractor = SegmentExtractor(
                output_base=tmpdir,
                reencode=True,
                max_parallel=2,
            )

            segments = [
                {
                    "source_video_id": "vid_001",
                    "timestamp_start": "0:10",
                    "timestamp_end": "0:30",
                    "segment_type": "hook",
                    "position": 0,
                },
            ]
            source_lookup = {"vid_001": src_path}

            async def mock_exec(*args, **kwargs):
                captured_cmds.append(list(str(a) for a in args))
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
            extract_cmds = [c for c in captured_cmds if "libx264" in c]
            assert len(extract_cmds) >= 1, "Expected re-encode cmd with libx264"

    @pytest.mark.asyncio
    async def test_parallel_extraction_respects_semaphore(self) -> None:
        """Multiple clips should extract with bounded concurrency."""
        from app.video_factory.segment_extractor import SegmentExtractor

        max_concurrent = 0
        current_concurrent = 0
        lock = asyncio.Lock()

        with tempfile.TemporaryDirectory() as tmpdir:
            src_path = os.path.join(tmpdir, "src.mp4")
            Path(src_path).write_bytes(b"\x00" * 2048)

            extractor = SegmentExtractor(
                output_base=tmpdir,
                reencode=False,
                max_parallel=2,
            )

            segments = [
                {
                    "source_video_id": "vid_001",
                    "timestamp_start": f"0:{i*10}",
                    "timestamp_end": f"0:{i*10 + 20}",
                    "segment_type": "body",
                    "position": i,
                }
                for i in range(5)
            ]
            source_lookup = {"vid_001": src_path}

            async def mock_exec(*args, **kwargs):
                nonlocal max_concurrent, current_concurrent
                async with lock:
                    current_concurrent += 1
                    max_concurrent = max(max_concurrent, current_concurrent)

                # Simulate some work
                await asyncio.sleep(0.01)

                async with lock:
                    current_concurrent -= 1

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

            assert len(result.clips) == 5
            # Semaphore should limit to 2 concurrent
            assert max_concurrent <= 2


# ═══════════════════════════════════════════════════════════════════════
#  Video Assembler — Single-Pass Encoding & GPU Tests
# ═══════════════════════════════════════════════════════════════════════


class TestCompilationAssemblerEncoding:
    """Test single-pass encoding, encoder arg building, and GPU fallback."""

    def test_default_encoder_is_cpu(self) -> None:
        from app.video_factory.video_assembler import CompilationAssembler

        assembler = CompilationAssembler()
        assert assembler.encoder == "libx264"

    def test_custom_encoder(self) -> None:
        from app.video_factory.video_assembler import CompilationAssembler

        assembler = CompilationAssembler(encoder="h264_nvenc")
        assert assembler.encoder == "h264_nvenc"

    def test_build_encoder_args_cpu(self) -> None:
        from app.video_factory.video_assembler import CompilationAssembler

        assembler = CompilationAssembler(
            encoder="libx264",
            cpu_preset="veryfast",
            crf=20,
        )
        args = assembler._build_encoder_args()

        assert "-c:v" in args
        idx = args.index("-c:v")
        assert args[idx + 1] == "libx264"

        assert "-preset" in args
        idx = args.index("-preset")
        assert args[idx + 1] == "veryfast"

        assert "-crf" in args
        idx = args.index("-crf")
        assert args[idx + 1] == "20"

        # Should NOT have NVENC-specific flags
        assert "-rc" not in args

    def test_build_encoder_args_nvenc(self) -> None:
        from app.video_factory.video_assembler import CompilationAssembler

        assembler = CompilationAssembler(
            encoder="h264_nvenc",
            gpu_preset="fast",
            crf=22,
        )
        args = assembler._build_encoder_args()

        idx = args.index("-c:v")
        assert args[idx + 1] == "h264_nvenc"

        idx = args.index("-preset")
        assert args[idx + 1] == "fast"

        # NVENC quality settings
        assert "-rc" in args
        assert "vbr" in args
        assert "-cq" in args
        assert "22" in args

        # No CRF for GPU
        assert "-crf" not in args

    def test_build_encoder_args_qsv(self) -> None:
        from app.video_factory.video_assembler import CompilationAssembler

        assembler = CompilationAssembler(encoder="h264_qsv", gpu_preset="fast")
        args = assembler._build_encoder_args()

        idx = args.index("-c:v")
        assert args[idx + 1] == "h264_qsv"

        # QSV should not have NVENC-specific flags
        assert "-rc" not in args
        assert "-cq" not in args

    def test_build_encoder_args_includes_scale_filter(self) -> None:
        from app.video_factory.video_assembler import CompilationAssembler

        assembler = CompilationAssembler(encoder="libx264")
        args = assembler._build_encoder_args()

        assert "-vf" in args
        idx = args.index("-vf")
        vf = args[idx + 1]
        assert "scale=" in vf
        assert "pad=" in vf
        assert "setsar=1" in vf

    def test_build_encoder_args_audio(self) -> None:
        from app.video_factory.video_assembler import CompilationAssembler

        assembler = CompilationAssembler()
        args = assembler._build_encoder_args()

        assert "-c:a" in args
        idx = args.index("-c:a")
        assert args[idx + 1] == "aac"
        assert "-b:a" in args

    @pytest.mark.asyncio
    async def test_encode_final_gpu_fallback_to_cpu(self) -> None:
        """If GPU encoder fails, it falls back to CPU."""
        from app.video_factory.video_assembler import CompilationAssembler

        with tempfile.TemporaryDirectory() as tmpdir:
            assembler = CompilationAssembler(encoder="h264_nvenc")
            concat_file = os.path.join(tmpdir, "concat.txt")
            output_path = os.path.join(tmpdir, "output.mp4")
            Path(concat_file).write_text("file '/tmp/clip.mp4'\n")

            call_idx = 0

            async def mock_exec(*args, **kwargs):
                nonlocal call_idx
                call_idx += 1
                m = AsyncMock()
                if call_idx == 1:
                    # GPU attempt fails
                    m.returncode = 1
                    m.communicate = AsyncMock(return_value=(b"", b"encoder error"))
                else:
                    # CPU fallback succeeds
                    m.returncode = 0
                    Path(output_path).write_bytes(b"\x00" * 50_000)
                    m.communicate = AsyncMock(return_value=(b"", b""))
                return m

            with patch("asyncio.create_subprocess_exec", side_effect=mock_exec):
                success = await assembler._encode_final(concat_file, output_path)

            assert success is True
            assert assembler.encoder == "libx264"  # Should have fallen back

    @pytest.mark.asyncio
    async def test_encode_final_cpu_success(self) -> None:
        """CPU encoding succeeds on first attempt."""
        from app.video_factory.video_assembler import CompilationAssembler

        with tempfile.TemporaryDirectory() as tmpdir:
            assembler = CompilationAssembler(encoder="libx264")
            concat_file = os.path.join(tmpdir, "concat.txt")
            output_path = os.path.join(tmpdir, "output.mp4")
            Path(concat_file).write_text("file '/tmp/clip.mp4'\n")

            async def mock_exec(*args, **kwargs):
                Path(output_path).write_bytes(b"\x00" * 50_000)
                m = AsyncMock()
                m.returncode = 0
                m.communicate = AsyncMock(return_value=(b"", b""))
                return m

            with patch("asyncio.create_subprocess_exec", side_effect=mock_exec):
                success = await assembler._encode_final(concat_file, output_path)

            assert success is True

    @pytest.mark.asyncio
    async def test_run_concat_cmd_builds_correct_command(self) -> None:
        """Verify the concat command structure."""
        from app.video_factory.video_assembler import CompilationAssembler

        captured_cmds: list[list[str]] = []

        with tempfile.TemporaryDirectory() as tmpdir:
            assembler = CompilationAssembler(encoder="libx264")
            concat_file = os.path.join(tmpdir, "concat.txt")
            output_path = os.path.join(tmpdir, "output.mp4")
            Path(concat_file).write_text("file '/tmp/clip.mp4'\n")

            async def mock_exec(*args, **kwargs):
                captured_cmds.append(list(str(a) for a in args))
                Path(output_path).write_bytes(b"\x00" * 50_000)
                m = AsyncMock()
                m.returncode = 0
                m.communicate = AsyncMock(return_value=(b"", b""))
                return m

            codec_args = ["-c:v", "libx264", "-preset", "veryfast"]
            with patch("asyncio.create_subprocess_exec", side_effect=mock_exec):
                result = await assembler._run_concat_cmd(
                    concat_file, output_path, codec_args,
                )

            assert result is True
            assert len(captured_cmds) == 1
            cmd = captured_cmds[0]
            assert "ffmpeg" in cmd[0]
            assert "-f" in cmd
            assert "concat" in cmd
            assert "-safe" in cmd
            assert "-pix_fmt" in cmd
            assert "-movflags" in cmd


# ═══════════════════════════════════════════════════════════════════════
#  Job Scheduler Tests
# ═══════════════════════════════════════════════════════════════════════

class TestJobScheduler:
    """Test resource-aware job scheduling and concurrency limiting."""

    def test_scheduler_defaults(self) -> None:
        from app.video_factory.job_scheduler import JobScheduler

        sched = JobScheduler()
        assert sched.max_concurrent == 2
        assert sched.cpu_threshold == 90.0
        assert sched.memory_threshold == 85.0
        assert sched.active_jobs == 0
        assert sched.queued_jobs == 0

    def test_scheduler_custom_config(self) -> None:
        from app.video_factory.job_scheduler import JobScheduler

        sched = JobScheduler(
            max_concurrent=4,
            cpu_threshold=80.0,
            memory_threshold=75.0,
        )
        assert sched.max_concurrent == 4
        assert sched.cpu_threshold == 80.0
        assert sched.memory_threshold == 75.0

    def test_scheduler_stats(self) -> None:
        from app.video_factory.job_scheduler import JobScheduler

        sched = JobScheduler(max_concurrent=3)
        with patch(
            "app.video_factory.job_scheduler.get_system_load",
            return_value={"cpu_percent": 30.0, "memory_percent": 50.0},
        ):
            stats = sched.stats

        assert stats["active_jobs"] == 0
        assert stats["queued_jobs"] == 0
        assert stats["max_concurrent"] == 3
        assert stats["cpu_percent"] == 30.0
        assert stats["memory_percent"] == 50.0
        assert stats["throttled"] is False

    def test_scheduler_stats_throttled(self) -> None:
        from app.video_factory.job_scheduler import JobScheduler

        sched = JobScheduler(cpu_threshold=50.0)
        with patch(
            "app.video_factory.job_scheduler.get_system_load",
            return_value={"cpu_percent": 80.0, "memory_percent": 40.0},
        ):
            stats = sched.stats

        assert stats["throttled"] is True

    @pytest.mark.asyncio
    async def test_schedule_runs_job(self) -> None:
        from app.video_factory.job_scheduler import JobScheduler

        sched = JobScheduler(max_concurrent=2)
        executed = False

        async def job():
            nonlocal executed
            executed = True
            return "done"

        with patch(
            "app.video_factory.job_scheduler.get_system_load",
            return_value={"cpu_percent": 10.0, "memory_percent": 20.0},
        ):
            task = await sched.schedule(job)
            await task

        assert executed is True

    @pytest.mark.asyncio
    async def test_schedule_limits_concurrency(self) -> None:
        """No more than max_concurrent jobs run simultaneously."""
        from app.video_factory.job_scheduler import JobScheduler

        sched = JobScheduler(max_concurrent=2)
        max_concurrent = 0
        current_concurrent = 0
        lock = asyncio.Lock()

        async def tracked_job():
            nonlocal max_concurrent, current_concurrent
            async with lock:
                current_concurrent += 1
                max_concurrent = max(max_concurrent, current_concurrent)
            await asyncio.sleep(0.05)
            async with lock:
                current_concurrent -= 1

        with patch(
            "app.video_factory.job_scheduler.get_system_load",
            return_value={"cpu_percent": 10.0, "memory_percent": 20.0},
        ):
            tasks = []
            for _ in range(5):
                task = await sched.schedule(tracked_job)
                tasks.append(task)
            await asyncio.gather(*tasks)

        assert max_concurrent <= 2

    @pytest.mark.asyncio
    async def test_schedule_waits_for_resources(self) -> None:
        """Job waits when system load is above threshold."""
        from app.video_factory.job_scheduler import JobScheduler

        sched = JobScheduler(
            max_concurrent=2,
            cpu_threshold=50.0,
            poll_interval=0.01,  # fast poll for testing
        )
        call_count = 0
        executed = False

        def mock_load():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                return {"cpu_percent": 80.0, "memory_percent": 30.0}
            return {"cpu_percent": 20.0, "memory_percent": 30.0}

        async def job():
            nonlocal executed
            executed = True

        with patch(
            "app.video_factory.job_scheduler.get_system_load",
            side_effect=mock_load,
        ):
            task = await sched.schedule(job)
            await task

        assert executed is True
        assert call_count >= 3  # At least 2 throttled + 1 released

    def test_is_overloaded_cpu(self) -> None:
        from app.video_factory.job_scheduler import JobScheduler

        sched = JobScheduler(cpu_threshold=80.0, memory_threshold=85.0)
        assert sched._is_overloaded({"cpu_percent": 90.0, "memory_percent": 50.0}) is True
        assert sched._is_overloaded({"cpu_percent": 70.0, "memory_percent": 50.0}) is False

    def test_is_overloaded_memory(self) -> None:
        from app.video_factory.job_scheduler import JobScheduler

        sched = JobScheduler(cpu_threshold=80.0, memory_threshold=85.0)
        assert sched._is_overloaded({"cpu_percent": 50.0, "memory_percent": 90.0}) is True
        assert sched._is_overloaded({"cpu_percent": 50.0, "memory_percent": 80.0}) is False

    def test_get_job_scheduler_singleton(self) -> None:
        import app.video_factory.job_scheduler as js

        # Reset singleton
        js._scheduler = None

        with patch("app.video_factory.job_scheduler.get_settings") as mock_settings:
            mock_vp = MagicMock()
            mock_vp.max_concurrent_video_jobs = 3
            mock_vp.cpu_load_pause_threshold = 85.0
            mock_vp.memory_load_pause_threshold = 80.0
            mock_settings.return_value.video_processing = mock_vp

            s1 = js.get_job_scheduler()
            s2 = js.get_job_scheduler()

        assert s1 is s2
        assert s1.max_concurrent == 3
        assert s1.cpu_threshold == 85.0
        assert s1.memory_threshold == 80.0

        # Clean up
        js._scheduler = None


# ═══════════════════════════════════════════════════════════════════════
#  Config Integration Tests
# ═══════════════════════════════════════════════════════════════════════


class TestVideoProcessingConfig:
    """Test that VideoProcessingConfig integrates properly with Settings."""

    def test_default_values(self) -> None:
        from app.config.settings import VideoProcessingConfig

        cfg = VideoProcessingConfig()
        assert cfg.enable_stream_copy is True
        assert cfg.enable_gpu_acceleration is True
        assert cfg.gpu_encoder == "auto"
        assert cfg.cpu_preset == "veryfast"
        assert cfg.gpu_preset == "fast"
        assert cfg.crf == 20
        assert cfg.max_parallel_clip_tasks == 4
        assert cfg.max_concurrent_video_jobs == 2
        assert cfg.cpu_load_pause_threshold == 90.0
        assert cfg.memory_load_pause_threshold == 85.0

    def test_custom_values(self) -> None:
        from app.config.settings import VideoProcessingConfig

        cfg = VideoProcessingConfig(
            enable_stream_copy=False,
            enable_gpu_acceleration=False,
            gpu_encoder="h264_nvenc",
            cpu_preset="medium",
            crf=18,
            max_parallel_clip_tasks=8,
            max_concurrent_video_jobs=4,
        )
        assert cfg.enable_stream_copy is False
        assert cfg.enable_gpu_acceleration is False
        assert cfg.gpu_encoder == "h264_nvenc"
        assert cfg.cpu_preset == "medium"
        assert cfg.crf == 18
        assert cfg.max_parallel_clip_tasks == 8
        assert cfg.max_concurrent_video_jobs == 4

    def test_settings_has_video_processing(self) -> None:
        """The Settings model should include video_processing config."""
        from app.config.settings import Settings

        # Check the field exists on the model
        assert "video_processing" in Settings.model_fields
