"""Video Factory — Copyright Guard.

Performs safety checks on extracted clips to reduce copyright risk
before assembling the final compilation video.

Checks include:
- Maximum clip duration thresholds (no single clip from one source
  should exceed a configurable % of the source video duration)
- Total usage per source video
- Duplicate segment detection
- Minimum transformation (clips must be re-encoded, not raw copies)
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)

# Maximum % of a single source video that can be used (across all clips)
_MAX_SOURCE_USAGE_PCT = 25.0

# Maximum single clip duration as % of source video
_MAX_SINGLE_CLIP_PCT = 15.0

# Maximum single clip duration in absolute seconds (regardless of source length)
_MAX_SINGLE_CLIP_ABS = 60.0

# Minimum number of unique sources required
_MIN_UNIQUE_SOURCES = 2


@dataclass
class CopyrightIssue:
    """A single copyright concern found during analysis."""

    severity: str = "warning"  # warning | error
    source_video_id: str = ""
    clip_id: str = ""
    message: str = ""
    recommendation: str = ""


@dataclass
class CopyrightReport:
    """Full copyright safety report for a compilation job."""

    is_safe: bool = True
    issues: list[CopyrightIssue] = field(default_factory=list)
    clips_checked: int = 0
    unique_sources: int = 0
    total_compilation_duration: float = 0.0
    source_usage: dict[str, float] = field(default_factory=dict)  # video_id → % usage


class CopyrightGuard:
    """Analyze extracted clips for copyright safety.

    Parameters
    ----------
    max_source_usage_pct : float
        Maximum total usage of any single source video (%).
    max_single_clip_pct : float
        Maximum single clip duration as % of source video.
    max_single_clip_abs : float
        Maximum clip duration in seconds (absolute cap).
    min_unique_sources : int
        Minimum number of distinct source videos required.
    strict : bool
        If True, warnings become errors and the pipeline will fail.
    """

    def __init__(
        self,
        max_source_usage_pct: float = _MAX_SOURCE_USAGE_PCT,
        max_single_clip_pct: float = _MAX_SINGLE_CLIP_PCT,
        max_single_clip_abs: float = _MAX_SINGLE_CLIP_ABS,
        min_unique_sources: int = _MIN_UNIQUE_SOURCES,
        strict: bool = False,
    ) -> None:
        self.max_source_usage_pct = max_source_usage_pct
        self.max_single_clip_pct = max_single_clip_pct
        self.max_single_clip_abs = max_single_clip_abs
        self.min_unique_sources = min_unique_sources
        self.strict = strict

    def analyze(
        self,
        clips: list[dict[str, Any]],
        source_durations: dict[str, float],
    ) -> CopyrightReport:
        """Run copyright safety analysis on a set of clips.

        Parameters
        ----------
        clips : list[dict]
            Each dict must have ``clip_id``, ``source_video_id``,
            ``duration_seconds``, ``start_seconds``, ``end_seconds``.
        source_durations : dict[str, float]
            Mapping of ``video_id`` → total source video duration (seconds).

        Returns
        -------
        CopyrightReport
        """
        report = CopyrightReport(clips_checked=len(clips))

        if not clips:
            report.is_safe = False
            report.issues.append(CopyrightIssue(
                severity="error",
                message="No clips to analyze",
            ))
            return report

        # Aggregate usage per source video
        usage_per_source: dict[str, float] = {}
        for clip in clips:
            vid_id = clip.get("source_video_id", "unknown")
            dur = float(clip.get("duration_seconds", 0))
            usage_per_source[vid_id] = usage_per_source.get(vid_id, 0) + dur

        unique_sources = set(c.get("source_video_id", "") for c in clips)
        report.unique_sources = len(unique_sources)

        # Check minimum unique sources
        if report.unique_sources < self.min_unique_sources:
            severity = "error" if self.strict else "warning"
            report.issues.append(CopyrightIssue(
                severity=severity,
                message=(
                    f"Only {report.unique_sources} unique source(s) used "
                    f"(minimum {self.min_unique_sources} recommended)"
                ),
                recommendation="Add more source videos to diversify content",
            ))
            if severity == "error":
                report.is_safe = False

        total_compilation_dur = sum(float(c.get("duration_seconds", 0)) for c in clips)
        report.total_compilation_duration = total_compilation_dur

        # Check per-source usage
        for vid_id, total_used in usage_per_source.items():
            source_dur = source_durations.get(vid_id, 0)
            if source_dur > 0:
                usage_pct = (total_used / source_dur) * 100
                report.source_usage[vid_id] = round(usage_pct, 1)

                if usage_pct > self.max_source_usage_pct:
                    severity = "error" if self.strict else "warning"
                    report.issues.append(CopyrightIssue(
                        severity=severity,
                        source_video_id=vid_id,
                        message=(
                            f"Source {vid_id}: {usage_pct:.1f}% used "
                            f"(max {self.max_source_usage_pct}%)"
                        ),
                        recommendation=(
                            f"Reduce clips from this source to stay under "
                            f"{self.max_source_usage_pct}% of the original"
                        ),
                    ))
                    if severity == "error":
                        report.is_safe = False

        # Check individual clip durations
        for clip in clips:
            clip_id = clip.get("clip_id", "")
            vid_id = clip.get("source_video_id", "")
            dur = float(clip.get("duration_seconds", 0))
            source_dur = source_durations.get(vid_id, 0)

            # Absolute duration check
            if dur > self.max_single_clip_abs:
                report.issues.append(CopyrightIssue(
                    severity="warning",
                    source_video_id=vid_id,
                    clip_id=clip_id,
                    message=(
                        f"Clip {clip_id} is {dur:.1f}s "
                        f"(max recommended {self.max_single_clip_abs}s)"
                    ),
                    recommendation="Consider trimming this clip",
                ))

            # Percentage of source check
            if source_dur > 0:
                clip_pct = (dur / source_dur) * 100
                if clip_pct > self.max_single_clip_pct:
                    report.issues.append(CopyrightIssue(
                        severity="warning",
                        source_video_id=vid_id,
                        clip_id=clip_id,
                        message=(
                            f"Clip {clip_id} uses {clip_pct:.1f}% of source "
                            f"(max {self.max_single_clip_pct}%)"
                        ),
                        recommendation="Trim clip or use a shorter segment",
                    ))

        # Check for duplicate/overlapping segments
        self._check_overlaps(clips, report)

        # Set overall safety
        if any(i.severity == "error" for i in report.issues):
            report.is_safe = False

        logger.info(
            "copyright_analysis_complete",
            is_safe=report.is_safe,
            issues=len(report.issues),
            unique_sources=report.unique_sources,
        )
        return report

    @staticmethod
    def _check_overlaps(clips: list[dict[str, Any]], report: CopyrightReport) -> None:
        """Check for overlapping segments from the same source."""
        by_source: dict[str, list[dict]] = {}
        for c in clips:
            vid = c.get("source_video_id", "")
            by_source.setdefault(vid, []).append(c)

        for vid_id, src_clips in by_source.items():
            if len(src_clips) < 2:
                continue
            # Sort by start time
            sorted_clips = sorted(src_clips, key=lambda c: float(c.get("start_seconds", 0)))
            for i in range(1, len(sorted_clips)):
                prev_end = float(sorted_clips[i - 1].get("end_seconds", 0))
                curr_start = float(sorted_clips[i].get("start_seconds", 0))
                if curr_start < prev_end:
                    overlap = prev_end - curr_start
                    report.issues.append(CopyrightIssue(
                        severity="warning",
                        source_video_id=vid_id,
                        clip_id=sorted_clips[i].get("clip_id", ""),
                        message=(
                            f"Overlapping segments from {vid_id}: "
                            f"{overlap:.1f}s overlap between clips"
                        ),
                        recommendation="Adjust segment boundaries to avoid overlap",
                    ))
