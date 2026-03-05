"""Compilation Video Intelligence — orchestrates source discovery, segment
detection, structure generation, editing guidance, and AI refinement.

Follows the same engine pattern as :class:`ViralOpportunityDetector`:
receives a :class:`YouTubeSearchConnector`, exposes a single ``analyze``
coroutine, and returns a self-contained :class:`CompilationStrategy`.
"""
from __future__ import annotations

import json
import math
import re
from typing import Any

from app.compilation_engine.schemas import (
    CompilationSegment,
    CompilationSourceVideo,
    CompilationStrategy,
    CompilationStructureItem,
    EditingGuidance,
    EnergyLevel,
    FinalVideoConcept,
    SegmentType,
)
from app.connectors.youtube_search import YouTubeSearchConnector
from app.core.logging import get_logger
from app.core.models import SearchResult

logger = get_logger(__name__)

# ── Tunables ──────────────────────────────────────────────────────────────────
_MIN_DURATION_SECONDS = 60       # ignore very short videos (< 1 min)
_MAX_SOURCE_VIDEOS = 15          # cap on source videos per analysis
_IDEAL_COMPILATION_MINUTES = 12  # target length for the compiled output
_SEGMENTS_PER_SOURCE = 2         # max recommended segments per source video


# ═══════════════════════════════════════════════════════════════════════
#  Step 1 — Source Video Discovery
# ═══════════════════════════════════════════════════════════════════════

class _VideoSourceFinder:
    """Finds and scores candidate source videos for a compilation."""

    def __init__(self, yt_search: YouTubeSearchConnector) -> None:
        self.yt_search = yt_search

    async def find_sources(
        self,
        niche: str,
        keywords: list[str],
        max_results_per_keyword: int = 15,
    ) -> list[CompilationSourceVideo]:
        """Search YouTube for the best compilation source material.

        Strategy:
        - Construct compilation-oriented queries ("best of …", "top … moments").
        - Deduplicate by ``video_id``.
        - Score each video by engagement × recency × length suitability.
        """
        raw: list[SearchResult] = []
        seen_ids: set[str] = set()

        # Build diverse queries
        base_queries = [niche] + keywords[:4]
        base_queries = list(dict.fromkeys(base_queries))[:5]

        compilation_prefixes = [
            "best of", "top", "compilation", "highlights", "most viral",
        ]
        queries: list[str] = []
        for q in base_queries:
            queries.append(q)
            for prefix in compilation_prefixes[:2]:
                queries.append(f"{prefix} {q}")
        queries = list(dict.fromkeys(queries))[:10]

        for query in queries:
            try:
                results = await self.yt_search.search(query, max_results=max_results_per_keyword)
                for r in results:
                    if r.video_id and r.video_id not in seen_ids:
                        seen_ids.add(r.video_id)
                        raw.append(r)
            except Exception as exc:
                logger.warning("compilation_source_search_error", query=query, error=str(exc))

        scored = [self._score_video(r) for r in raw if r.duration_seconds >= _MIN_DURATION_SECONDS]
        scored.sort(key=lambda v: v.engagement_score, reverse=True)
        return scored[:_MAX_SOURCE_VIDEOS]

    # ── scoring helpers ──

    @staticmethod
    def _score_video(result: SearchResult) -> CompilationSourceVideo:
        """Compute engagement_score & relevance_score for *result*."""
        views = max(result.view_count, 1)
        subs = max(result.channel_subscribers, 1)

        # Engagement: views / subs ratio, capped for sanity
        vsr = min(views / subs, 500.0) if subs > 0 else 0.0
        engagement = min(100.0, math.log1p(vsr) * 15.0)

        # Length suitability: prefer 3-20 min source videos
        dur = result.duration_seconds
        if 180 <= dur <= 1200:
            length_bonus = 15.0
        elif dur > 1200:
            length_bonus = 5.0
        else:
            length_bonus = 0.0
        engagement += length_bonus

        # Recency bonus
        age = _estimate_age_days(result.published_date)
        if age is not None and age < 30:
            engagement += 10.0
        elif age is not None and age < 90:
            engagement += 5.0

        engagement = min(100.0, engagement)

        url = f"https://www.youtube.com/watch?v={result.video_id}" if result.video_id else ""

        return CompilationSourceVideo(
            video_id=result.video_id,
            title=result.title,
            channel_name=result.channel_name,
            view_count=result.view_count,
            duration_seconds=result.duration_seconds,
            published_date=result.published_date,
            url=url,
            engagement_score=round(engagement, 1),
            relevance_score=round(engagement * 0.8, 1),
        )


# ═══════════════════════════════════════════════════════════════════════
#  Step 2 — Segment Detection
# ═══════════════════════════════════════════════════════════════════════

class _SegmentDetector:
    """Heuristic-based segment extraction from source video metadata.

    Without direct access to the video stream we estimate "highlight
    windows" from title keywords, video duration, and engagement signals.
    """

    # Keywords that hint at an energetic / impactful moment
    _HIGH_ENERGY_KEYWORDS = {
        "insane", "viral", "crazy", "incredible", "unbelievable", "shocking",
        "best", "epic", "amazing", "intense", "extreme", "unexpected",
    }

    @classmethod
    def detect_segments(
        cls,
        source_videos: list[CompilationSourceVideo],
    ) -> list[CompilationSegment]:
        """Generate recommended segments from *source_videos*."""
        segments: list[CompilationSegment] = []

        for video in source_videos:
            dur = max(video.duration_seconds, 30)
            n_segments = min(_SEGMENTS_PER_SOURCE, max(1, dur // 120))

            for i in range(n_segments):
                # Space segments evenly through the video
                ratio_start = i / max(n_segments, 1)
                ratio_end = ratio_start + min(0.15, 1.0 / max(n_segments, 1))
                start_sec = int(dur * ratio_start)
                end_sec = min(int(dur * ratio_end), dur)
                seg_dur = end_sec - start_sec

                energy = cls._infer_energy(video.title, i, n_segments)

                segments.append(CompilationSegment(
                    source_video_id=video.video_id,
                    source_video_title=video.title,
                    timestamp_start=_format_ts(start_sec),
                    timestamp_end=_format_ts(end_sec),
                    duration_seconds=seg_dur,
                    segment_theme=cls._infer_theme(video.title),
                    energy_level=energy,
                    why_include=f"Engagement score {video.engagement_score}/100",
                ))

        return segments

    @classmethod
    def _infer_energy(cls, title: str, seg_idx: int, total: int) -> EnergyLevel:
        title_lower = title.lower()
        has_high_kw = any(kw in title_lower for kw in cls._HIGH_ENERGY_KEYWORDS)
        if has_high_kw:
            return EnergyLevel.HIGH
        if seg_idx == total - 1:
            return EnergyLevel.CLIMAX if total > 1 else EnergyLevel.HIGH
        if seg_idx == 0:
            return EnergyLevel.MEDIUM
        return EnergyLevel.LOW

    @staticmethod
    def _infer_theme(title: str) -> str:
        """Extract a short theme tag from the video title."""
        title_clean = re.sub(r"[^a-zA-Z0-9\s]", "", title)
        words = title_clean.split()[:4]
        return " ".join(words) if words else "general"


# ═══════════════════════════════════════════════════════════════════════
#  Step 3 — Structure & Editing Guidance
# ═══════════════════════════════════════════════════════════════════════

class _CompilationStrategyBuilder:
    """Assembles segments into a paced timeline and generates editing advice."""

    # Energy arc template: hook → build → surprise → build → payoff → outro
    _ARC_TEMPLATE: list[tuple[SegmentType, EnergyLevel]] = [
        (SegmentType.INTRO_HOOK, EnergyLevel.HIGH),
        (SegmentType.REVEAL, EnergyLevel.MEDIUM),
        (SegmentType.EDUCATIONAL, EnergyLevel.LOW),
        (SegmentType.SURPRISE, EnergyLevel.HIGH),
        (SegmentType.DRAMATIC, EnergyLevel.CLIMAX),
        (SegmentType.PAYOFF, EnergyLevel.HIGH),
        (SegmentType.OUTRO_CTA, EnergyLevel.MEDIUM),
    ]

    @classmethod
    def build_structure(
        cls,
        segments: list[CompilationSegment],
    ) -> list[CompilationStructureItem]:
        """Arrange *segments* into a paced compilation timeline."""
        if not segments:
            return []

        # Sort segments by energy for assignment to arc slots
        by_energy: dict[EnergyLevel, list[CompilationSegment]] = {
            e: [] for e in EnergyLevel
        }
        for seg in segments:
            by_energy[seg.energy_level].append(seg)

        items: list[CompilationStructureItem] = []
        position = 1

        for seg_type, desired_energy in cls._ARC_TEMPLATE:
            # Try exact energy match, then fallback to any available
            chosen = cls._pop_segment(by_energy, desired_energy)
            if chosen is None:
                # Try any pool with remaining segments
                for pool_energy in [EnergyLevel.HIGH, EnergyLevel.MEDIUM, EnergyLevel.LOW, EnergyLevel.CLIMAX]:
                    chosen = cls._pop_segment(by_energy, pool_energy)
                    if chosen:
                        break

            items.append(CompilationStructureItem(
                position=position,
                segment_type=seg_type,
                segment=chosen,
                duration_seconds=chosen.duration_seconds if chosen else 15,
                notes=f"{seg_type.value} slot — energy {desired_energy.value}",
            ))
            position += 1

        # Append any remaining segments as extra reveals
        for pool in by_energy.values():
            for leftover in pool:
                items.append(CompilationStructureItem(
                    position=position,
                    segment_type=SegmentType.REVEAL,
                    segment=leftover,
                    duration_seconds=leftover.duration_seconds,
                    notes="additional clip",
                ))
                position += 1

        return items

    @staticmethod
    def _pop_segment(
        pools: dict[EnergyLevel, list[CompilationSegment]],
        energy: EnergyLevel,
    ) -> CompilationSegment | None:
        pool = pools.get(energy, [])
        return pool.pop(0) if pool else None

    @classmethod
    def generate_editing_guidance(cls, niche: str, structure: list[CompilationStructureItem]) -> EditingGuidance:
        """Produce editing recommendations based on the niche and timeline."""
        total_dur = sum(s.duration_seconds for s in structure)
        n_clips = len([s for s in structure if s.segment])

        pacing = "fast-paced" if n_clips > 8 else "moderate" if n_clips > 4 else "cinematic"

        return EditingGuidance(
            transition_style="smooth crossfade with occasional whip-pan for energy spikes",
            text_overlays=[
                f"Numbering (#1, #2 …) for {n_clips} clips",
                f"'{niche}' branding lower-third",
                "Subscribe CTA at outro",
            ],
            sound_effects=["whoosh for transitions", "impact hit for reveals", "subtle bass drop for surprises"],
            background_music_style=f"{pacing} royalty-free {niche.lower()}-themed music",
            pacing_notes=f"Target {pacing} tempo across {total_dur}s of content with {n_clips} clips",
            color_grading_tips="Consistent colour palette across clips; boost saturation by 10-15%",
            audio_mixing_tips="Normalise audio levels; duck music 6 dB under dialogue",
        )

    @classmethod
    def generate_video_concept(
        cls,
        niche: str,
        structure: list[CompilationStructureItem],
        source_videos: list[CompilationSourceVideo],
    ) -> FinalVideoConcept:
        """Create the final compiled-video concept."""
        total_dur = sum(s.duration_seconds for s in structure)
        est_minutes = round(total_dur / 60.0, 1)
        n_clips = len([s for s in structure if s.segment])
        top_views = max((v.view_count for v in source_videos), default=0)

        return FinalVideoConcept(
            title=f"Top {n_clips} Best {niche} Moments You Won't Believe",
            description=(
                f"A curated compilation of the {n_clips} most incredible {niche.lower()} "
                f"moments from across YouTube. Featuring clips with up to "
                f"{top_views:,} views. Watch until the end for the #1 moment!"
            ),
            tags=[niche, f"{niche} compilation", f"best of {niche}", "top moments",
                  f"{niche} highlights", "viral", "must watch", f"{niche} 2024",
                  "compilation", "best clips"],
            target_audience=f"Fans of {niche} content aged 18-34",
            emotional_hook="Escalating reveals keep viewers guessing which clip is #1",
            watch_time_strategy="Numbered countdown format creates anticipation; best clip saved for last",
            estimated_duration_minutes=est_minutes,
            thumbnail_idea=f"Split image: shocked face + most dramatic {niche} moment + bold '#1' text",
        )


# ═══════════════════════════════════════════════════════════════════════
#  Main Orchestrator
# ═══════════════════════════════════════════════════════════════════════

class CompilationAnalyzer:
    """End-to-end compilation video intelligence engine.

    Usage::

        analyzer = CompilationAnalyzer(yt_search)
        strategy = await analyzer.analyze("funny cats", ["cat fails", "cat memes"])
    """

    def __init__(self, yt_search: YouTubeSearchConnector) -> None:
        self.yt_search = yt_search
        self._source_finder = _VideoSourceFinder(yt_search)

    async def analyze(
        self,
        niche: str,
        keywords: list[str],
        *,
        use_ai: bool = True,
    ) -> CompilationStrategy:
        """Run the full compilation analysis pipeline.

        1. Discover source videos.
        2. Detect segments.
        3. Build video structure.
        4. Generate editing guidance.
        5. Generate final video concept.
        6. (optional) AI refinement via Vertex AI.
        """
        logger.info("compilation_analysis_started", niche=niche, keywords=keywords[:5])

        # Step 1
        source_videos = await self._source_finder.find_sources(niche, keywords)
        logger.info("compilation_sources_found", niche=niche, count=len(source_videos))

        if not source_videos:
            return CompilationStrategy(
                niche=niche,
                compilation_score=0.0,
                total_source_videos_found=0,
            )

        # Step 2
        segments = _SegmentDetector.detect_segments(source_videos)

        # Step 3
        structure = _CompilationStrategyBuilder.build_structure(segments)

        # Step 4
        editing = _CompilationStrategyBuilder.generate_editing_guidance(niche, structure)

        # Step 5
        concept = _CompilationStrategyBuilder.generate_video_concept(niche, structure, source_videos)

        # Compilation quality score
        compilation_score = self._compute_score(source_videos, segments, structure)

        # Step 6 — AI refinement
        ai_refinements: dict[str, Any] = {}
        if use_ai:
            ai_refinements = await self._ai_refine(niche, source_videos, segments, structure)

        strategy = CompilationStrategy(
            niche=niche,
            source_videos=source_videos,
            recommended_segments=segments,
            video_structure=structure,
            editing_guidance=editing,
            final_video_concept=concept,
            ai_refinements=ai_refinements,
            compilation_score=round(compilation_score, 1),
            total_source_videos_found=len(source_videos),
        )

        logger.info(
            "compilation_analysis_done",
            niche=niche,
            sources=len(source_videos),
            segments=len(segments),
            score=strategy.compilation_score,
        )
        return strategy

    # ── helpers ──

    @staticmethod
    def _compute_score(
        sources: list[CompilationSourceVideo],
        segments: list[CompilationSegment],
        structure: list[CompilationStructureItem],
    ) -> float:
        """Heuristic quality score for the compilation strategy (0-100)."""
        if not sources:
            return 0.0

        # Source diversity (more unique channels = better)
        unique_channels = len({v.channel_name for v in sources})
        diversity_score = min(30.0, unique_channels * 5.0)

        # Engagement quality
        avg_engagement = sum(v.engagement_score for v in sources) / len(sources)
        engagement_component = min(30.0, avg_engagement * 0.3)

        # Structure completeness (filled slots vs empty)
        filled = len([s for s in structure if s.segment is not None])
        total_slots = max(len(structure), 1)
        completeness = min(20.0, (filled / total_slots) * 20.0)

        # Segment count bonus
        seg_bonus = min(20.0, len(segments) * 2.0)

        return min(100.0, diversity_score + engagement_component + completeness + seg_bonus)

    @staticmethod
    async def _ai_refine(
        niche: str,
        sources: list[CompilationSourceVideo],
        segments: list[CompilationSegment],
        structure: list[CompilationStructureItem],
    ) -> dict[str, Any]:
        """Attempt AI enhancement; return empty dict on failure."""
        try:
            from app.ai.service import generate_compilation_strategy

            src_json = json.dumps(
                [s.model_dump(mode="json") for s in sources[:10]],
                indent=2,
            )
            seg_json = json.dumps(
                [s.model_dump(mode="json") for s in segments[:15]],
                indent=2,
            )
            struct_json = json.dumps(
                [s.model_dump(mode="json") for s in structure[:12]],
                indent=2,
            )

            result = await generate_compilation_strategy(niche, src_json, seg_json, struct_json)
            if "error" not in result:
                return result
            logger.warning("compilation_ai_refinement_failed", error=result.get("error"))
        except Exception as exc:
            logger.warning("compilation_ai_refinement_error", error=str(exc))
        return {}


# ── Utility helpers ───────────────────────────────────────────────────────────

def _estimate_age_days(published_str: str) -> int | None:
    """Parse relative date strings like '3 days ago' → 3."""
    if not published_str:
        return None
    text = published_str.lower().strip()
    if "yesterday" in text:
        return 1
    m = re.search(r"(\d+)\s*(hour|day|week|month|year)", text)
    if not m:
        return None
    num = int(m.group(1))
    unit = m.group(2)
    multipliers = {"hour": 0, "day": 1, "week": 7, "month": 30, "year": 365}
    return num * multipliers.get(unit, 1)


def _format_ts(seconds: int) -> str:
    """Format *seconds* as ``M:SS`` timestamp."""
    m, s = divmod(max(seconds, 0), 60)
    return f"{m}:{s:02d}"
