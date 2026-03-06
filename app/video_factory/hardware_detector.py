"""Video Factory — Hardware Detection.

Detects available GPU encoders and system resources to configure
the optimal FFmpeg encoding pipeline.

Supported GPU encoders (in priority order):
- NVIDIA NVENC   (h264_nvenc)
- Intel QuickSync (h264_qsv)
- Apple VideoToolbox (h264_videotoolbox)
"""
from __future__ import annotations

import asyncio
import os
import platform
from dataclasses import dataclass, field

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class HardwareCapabilities:
    """Detected hardware capabilities."""

    # GPU encoders available (in priority order)
    available_gpu_encoders: list[str] = field(default_factory=list)
    recommended_encoder: str = "libx264"

    # System resources
    cpu_count: int = 1
    total_memory_gb: float = 0.0

    # Derived settings
    max_parallel_clips: int = 2
    ffmpeg_available: bool = False
    ffprobe_available: bool = False


# Encoder priority — first available wins
_GPU_ENCODERS = [
    ("h264_nvenc", "NVIDIA NVENC"),
    ("h264_qsv", "Intel QuickSync"),
    ("h264_videotoolbox", "Apple VideoToolbox"),
]


async def _check_encoder(encoder: str) -> bool:
    """Test whether an FFmpeg encoder is usable by running a quick encode test."""
    try:
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "nullsrc=s=64x64:d=0.1",
            "-c:v", encoder,
            "-frames:v", "1",
            "-f", "null", "-",
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await asyncio.wait_for(proc.communicate(), timeout=10.0)
        return proc.returncode == 0
    except Exception:
        return False


async def _check_binary(name: str) -> bool:
    """Check if a binary (ffmpeg / ffprobe) is on the PATH."""
    try:
        proc = await asyncio.create_subprocess_exec(
            name, "-version",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await asyncio.wait_for(proc.communicate(), timeout=5.0)
        return proc.returncode == 0
    except Exception:
        return False


def _get_cpu_count() -> int:
    """Return usable CPU count."""
    try:
        return os.cpu_count() or 1
    except Exception:
        return 1


def _get_total_memory_gb() -> float:
    """Return total system memory in GB."""
    try:
        if platform.system() == "Linux":
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        kb = int(line.split()[1])
                        return round(kb / (1024 * 1024), 1)
        elif platform.system() == "Darwin":
            import subprocess
            out = subprocess.check_output(["sysctl", "-n", "hw.memsize"]).decode().strip()
            return round(int(out) / (1024 ** 3), 1)
    except Exception:
        pass
    return 0.0


def get_system_load() -> dict[str, float]:
    """Return current CPU and memory usage percentages.

    Returns
    -------
    dict with keys ``cpu_percent`` and ``memory_percent``.
    """
    result: dict[str, float] = {"cpu_percent": 0.0, "memory_percent": 0.0}
    try:
        # CPU: 1-minute load average as percentage of cores
        load_1m = os.getloadavg()[0]
        cores = os.cpu_count() or 1
        result["cpu_percent"] = round((load_1m / cores) * 100, 1)
    except (OSError, AttributeError):
        pass

    try:
        if platform.system() == "Linux":
            with open("/proc/meminfo") as f:
                info: dict[str, int] = {}
                for line in f:
                    parts = line.split()
                    if parts[0] in ("MemTotal:", "MemAvailable:"):
                        info[parts[0].rstrip(":")] = int(parts[1])
                if "MemTotal" in info and "MemAvailable" in info:
                    used = info["MemTotal"] - info["MemAvailable"]
                    result["memory_percent"] = round((used / info["MemTotal"]) * 100, 1)
    except Exception:
        pass

    return result


async def detect_hardware(
    prefer_encoder: str = "auto",
) -> HardwareCapabilities:
    """Detect hardware capabilities for the video pipeline.

    Parameters
    ----------
    prefer_encoder : str
        ``auto`` — detect best available; or force a specific encoder name.

    Returns
    -------
    HardwareCapabilities
    """
    caps = HardwareCapabilities()

    # System info
    caps.cpu_count = _get_cpu_count()
    caps.total_memory_gb = _get_total_memory_gb()
    caps.max_parallel_clips = max(1, caps.cpu_count // 2)

    # Check FFmpeg / FFprobe
    ffmpeg_ok, ffprobe_ok = await asyncio.gather(
        _check_binary("ffmpeg"),
        _check_binary("ffprobe"),
    )
    caps.ffmpeg_available = ffmpeg_ok
    caps.ffprobe_available = ffprobe_ok

    if not ffmpeg_ok:
        logger.warning("ffmpeg_not_found")
        return caps

    # If a specific encoder is forced (not "auto"), test only that one
    if prefer_encoder and prefer_encoder != "auto" and prefer_encoder != "libx264":
        ok = await _check_encoder(prefer_encoder)
        if ok:
            caps.available_gpu_encoders = [prefer_encoder]
            caps.recommended_encoder = prefer_encoder
            logger.info("gpu_encoder_forced", encoder=prefer_encoder)
        else:
            logger.warning("forced_encoder_unavailable", encoder=prefer_encoder)
            caps.recommended_encoder = "libx264"
        return caps

    # Auto-detect GPUs in priority order
    for encoder, label in _GPU_ENCODERS:
        ok = await _check_encoder(encoder)
        if ok:
            caps.available_gpu_encoders.append(encoder)
            logger.info("gpu_encoder_available", encoder=encoder, label=label)

    if caps.available_gpu_encoders:
        caps.recommended_encoder = caps.available_gpu_encoders[0]
    else:
        caps.recommended_encoder = "libx264"
        logger.info("no_gpu_encoder_found_using_cpu")

    logger.info(
        "hardware_detection_complete",
        encoder=caps.recommended_encoder,
        gpus=caps.available_gpu_encoders,
        cpus=caps.cpu_count,
        ram_gb=caps.total_memory_gb,
        max_parallel_clips=caps.max_parallel_clips,
    )
    return caps


# ── Module-level cache ─────────────────────────────────────────────────────────

_cached: HardwareCapabilities | None = None


async def get_hardware_capabilities(
    prefer_encoder: str = "auto",
    force_refresh: bool = False,
) -> HardwareCapabilities:
    """Cached version of :func:`detect_hardware`."""
    global _cached
    if _cached is None or force_refresh:
        _cached = await detect_hardware(prefer_encoder)
    return _cached
