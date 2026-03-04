"""Thumbnail Pattern Analysis Engine — analyzes visual patterns in top thumbnails.

Collects thumbnails from top YouTube results per niche, extracts visual signals
(dominant colors, text presence, face detection, contrast, clutter), clusters
into style groups, and outputs actionable design insights.

This module uses lightweight heuristics on image data (PIL/Pillow) rather than
heavy ML models, keeping it local and low-cost.
"""
from __future__ import annotations

import asyncio
import io
import math
from collections import Counter
from typing import Any

from app.connectors.youtube_search import YouTubeSearchConnector
from app.core.logging import get_logger
from app.core.models import (
    SearchResult,
    ThumbnailPatternResult,
    ThumbnailSignals,
    ThumbnailStyleGroup,
)

logger = get_logger(__name__)

# YouTube thumbnail URL patterns — maxresdefault falls back to hqdefault
_THUMBNAIL_URL = "https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"

# Named color buckets for dominant-color labelling
_COLOR_NAMES: dict[str, tuple[int, int, int]] = {
    "red": (220, 50, 50),
    "orange": (230, 150, 30),
    "yellow": (240, 220, 50),
    "green": (50, 180, 70),
    "cyan": (50, 200, 210),
    "blue": (50, 100, 220),
    "purple": (150, 60, 200),
    "pink": (230, 100, 170),
    "white": (240, 240, 240),
    "black": (30, 30, 30),
    "gray": (128, 128, 128),
}


class ThumbnailAnalysisEngine:
    """Analyze thumbnail visual patterns for a niche."""

    def __init__(self, yt_search: YouTubeSearchConnector) -> None:
        self.yt_search = yt_search

    async def analyze_niche(
        self,
        niche: str,
        keywords: list[str],
        max_thumbnails: int = 15,
    ) -> ThumbnailPatternResult:
        """Analyze thumbnails from top videos in a niche.

        Steps:
          1. Search YouTube for niche keywords.
          2. Download thumbnails.
          3. Extract visual signals from each thumbnail.
          4. Cluster into style groups.
          5. Generate insights and recommendations.
        """
        # 1. Gather video IDs
        search_keywords = [niche] + keywords[:3]
        search_keywords = list(dict.fromkeys(search_keywords))[:4]

        all_results: list[SearchResult] = []
        seen_ids: set[str] = set()

        for kw in search_keywords:
            try:
                results = await self.yt_search.search(kw, max_results=10)
                for r in results:
                    if r.video_id and r.video_id not in seen_ids:
                        seen_ids.add(r.video_id)
                        all_results.append(r)
            except Exception as e:
                logger.warning("thumb_search_error", keyword=kw, error=str(e))

        all_results = all_results[:max_thumbnails]

        # 2-3. Download and analyze thumbnails
        signals: list[ThumbnailSignals] = []
        for video in all_results:
            sig = await self._analyze_thumbnail(video)
            if sig:
                signals.append(sig)

        # 4. Cluster into style groups
        style_groups = self._cluster_styles(signals, all_results)

        # 5. Generate insight text
        insight = self._generate_insight(signals, style_groups, niche)
        recommendations = self._generate_recommendations(signals, style_groups)

        result = ThumbnailPatternResult(
            niche=niche,
            total_analyzed=len(signals),
            signals=signals,
            style_groups=style_groups,
            insight=insight,
            recommendations=recommendations,
        )

        logger.info(
            "thumbnail_analysis_complete",
            niche=niche,
            thumbnails=len(signals),
            groups=len(style_groups),
        )
        return result

    async def analyze_batch(
        self,
        niche_keywords: dict[str, list[str]],
    ) -> dict[str, ThumbnailPatternResult]:
        """Analyze thumbnails for multiple niches."""
        results: dict[str, ThumbnailPatternResult] = {}
        for niche, keywords in niche_keywords.items():
            results[niche] = await self.analyze_niche(niche, keywords)
        return results

    # ── Thumbnail Download & Analysis ─────────────────────────────────

    async def _analyze_thumbnail(
        self, video: SearchResult,
    ) -> ThumbnailSignals | None:
        """Download and analyze a single thumbnail image."""
        try:
            from PIL import Image  # type: ignore[import-untyped]
        except ImportError:
            # Pillow not installed — return heuristic-only signals
            return self._heuristic_signals(video)

        url = _THUMBNAIL_URL.format(video_id=video.video_id)

        try:
            import httpx
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(url)
                if response.status_code != 200:
                    return self._heuristic_signals(video)

            img = Image.open(io.BytesIO(response.content)).convert("RGB")
            return self._extract_signals(img, video)

        except Exception as e:
            logger.debug("thumb_download_error", video_id=video.video_id, error=str(e))
            return self._heuristic_signals(video)

    def _extract_signals(self, img: Any, video: SearchResult) -> ThumbnailSignals:
        """Extract visual signals from a PIL Image."""
        from PIL import ImageStat  # type: ignore[import-untyped]

        width, height = img.size
        pixels = list(img.getdata())
        total_pixels = len(pixels)

        # Dominant colors — sample and quantize
        sample = pixels[::max(1, total_pixels // 500)]  # Sample ~500 pixels
        dominant_colors = self._quantize_colors(sample)

        # Brightness / contrast / saturation from ImageStat
        stat = ImageStat.Stat(img)
        r_mean, g_mean, b_mean = stat.mean[:3]
        brightness = (r_mean + g_mean + b_mean) / (3 * 255) * 100
        r_std, g_std, b_std = stat.stddev[:3]
        contrast = (r_std + g_std + b_std) / 3

        # Saturation estimate (difference between max and min channels)
        saturation = max(r_mean, g_mean, b_mean) - min(r_mean, g_mean, b_mean)

        # Text detection heuristic: high-contrast edges in the image
        has_text, text_coverage = self._detect_text_heuristic(img)

        # Face detection heuristic: skin-tone pixel ratio
        has_face = self._detect_face_heuristic(pixels, total_pixels)

        # Visual clutter: entropy-based
        clutter = self._calculate_clutter(img)

        return ThumbnailSignals(
            video_id=video.video_id,
            video_title=video.title,
            dominant_colors=dominant_colors,
            has_text=has_text,
            text_coverage_pct=round(text_coverage, 1),
            has_face=has_face,
            contrast_level=round(contrast, 1),
            brightness=round(brightness, 1),
            saturation=round(saturation, 1),
            visual_clutter_score=round(clutter, 1),
        )

    def _heuristic_signals(self, video: SearchResult) -> ThumbnailSignals:
        """Fallback when Pillow is unavailable — title-based heuristics."""
        title = video.title.lower()

        # Guess text presence from title patterns
        has_text = any(w in title for w in ["top", "best", "worst", "how", "why", "vs"])
        has_face = any(w in title for w in ["vlog", "react", "interview", "podcast"])

        return ThumbnailSignals(
            video_id=video.video_id,
            video_title=video.title,
            dominant_colors=["unknown"],
            has_text=has_text,
            text_coverage_pct=30.0 if has_text else 10.0,
            has_face=has_face,
            contrast_level=50.0,
            brightness=50.0,
            saturation=50.0,
            visual_clutter_score=40.0,
        )

    # ── Color Analysis ────────────────────────────────────────────────

    @staticmethod
    def _quantize_colors(
        pixels: list[tuple[int, int, int]],
    ) -> list[str]:
        """Map sampled pixels to named color buckets and return top 3."""
        bucket_counts: Counter[str] = Counter()

        for r, g, b in pixels:
            best_name = "gray"
            best_dist = float("inf")
            for name, (cr, cg, cb) in _COLOR_NAMES.items():
                dist = math.sqrt((r - cr) ** 2 + (g - cg) ** 2 + (b - cb) ** 2)
                if dist < best_dist:
                    best_dist = dist
                    best_name = name
            bucket_counts[best_name] += 1

        return [name for name, _ in bucket_counts.most_common(3)]

    # ── Text Detection Heuristic ──────────────────────────────────────

    @staticmethod
    def _detect_text_heuristic(img: Any) -> tuple[bool, float]:
        """Estimate text presence via edge density in the upper portion."""
        try:
            from PIL import ImageFilter  # type: ignore[import-untyped]

            # Crop upper 40 % (where text overlays usually appear)
            w, h = img.size
            upper = img.crop((0, 0, w, int(h * 0.4)))
            edges = upper.convert("L").filter(ImageFilter.FIND_EDGES)

            # Count high-edge pixels
            edge_pixels = list(edges.getdata())
            strong_edges = sum(1 for p in edge_pixels if p > 100)
            total = len(edge_pixels)
            edge_ratio = strong_edges / max(total, 1) * 100

            has_text = edge_ratio > 8.0
            return has_text, min(edge_ratio, 60.0)

        except Exception:
            return False, 0.0

    # ── Face Detection Heuristic ──────────────────────────────────────

    @staticmethod
    def _detect_face_heuristic(
        pixels: list[tuple[int, int, int]], total: int,
    ) -> bool:
        """Estimate face presence by skin-tone pixel ratio."""
        skin_count = 0
        sample_step = max(1, total // 1000)

        for i in range(0, total, sample_step):
            r, g, b = pixels[i]
            # Common skin-tone ranges (YCbCr-inspired heuristic)
            if r > 95 and g > 40 and b > 20:
                if max(r, g, b) - min(r, g, b) > 15:
                    if abs(r - g) > 15 and r > g and r > b:
                        skin_count += 1

        skin_ratio = skin_count / max(1, total // sample_step)
        return skin_ratio > 0.15

    # ── Visual Clutter ────────────────────────────────────────────────

    @staticmethod
    def _calculate_clutter(img: Any) -> float:
        """Estimate visual complexity via pixel-value entropy."""
        try:
            gray = img.convert("L")
            histogram = gray.histogram()
            total = sum(histogram)
            entropy = 0.0
            for count in histogram:
                if count > 0:
                    p = count / total
                    entropy -= p * math.log2(p)

            # Normalize: max entropy for 256 bins = 8.0
            return min(100.0, (entropy / 8.0) * 100)
        except Exception:
            return 40.0

    # ── Style Clustering ──────────────────────────────────────────────

    def _cluster_styles(
        self,
        signals: list[ThumbnailSignals],
        videos: list[SearchResult],
    ) -> list[ThumbnailStyleGroup]:
        """Cluster thumbnails into style groups by visual similarity."""
        if not signals:
            return []

        # Simple rule-based clustering (avoids sklearn dependency here)
        groups: dict[str, list[ThumbnailSignals]] = {
            "high_contrast_text": [],
            "face_focused": [],
            "colorful_minimal": [],
            "dark_moody": [],
            "bright_clean": [],
        }

        for sig in signals:
            if sig.has_face and sig.has_text:
                groups["face_focused"].append(sig)
            elif sig.has_text and sig.contrast_level > 60:
                groups["high_contrast_text"].append(sig)
            elif sig.brightness < 35:
                groups["dark_moody"].append(sig)
            elif sig.brightness > 65 and sig.visual_clutter_score < 50:
                groups["bright_clean"].append(sig)
            else:
                groups["colorful_minimal"].append(sig)

        # Build view map
        view_map: dict[str, int] = {}
        for v in videos:
            view_map[v.video_id] = v.view_count

        # Convert to style group models
        result: list[ThumbnailStyleGroup] = []
        for i, (label, sigs) in enumerate(groups.items()):
            if not sigs:
                continue

            all_colors: list[str] = []
            for s in sigs:
                all_colors.extend(s.dominant_colors)
            color_counts = Counter(all_colors)
            top_colors = [c for c, _ in color_counts.most_common(3)]

            avg_views = sum(view_map.get(s.video_id, 0) for s in sigs) / max(len(sigs), 1)

            result.append(ThumbnailStyleGroup(
                group_id=i,
                style_label=label.replace("_", " ").title(),
                count=len(sigs),
                avg_views=round(avg_views),
                dominant_colors=top_colors,
                text_prevalence=round(
                    sum(1 for s in sigs if s.has_text) / len(sigs) * 100, 1
                ),
                face_prevalence=round(
                    sum(1 for s in sigs if s.has_face) / len(sigs) * 100, 1
                ),
                avg_contrast=round(
                    sum(s.contrast_level for s in sigs) / len(sigs), 1
                ),
            ))

        result.sort(key=lambda g: g.avg_views, reverse=True)
        return result

    # ── Insight Generation ────────────────────────────────────────────

    def _generate_insight(
        self,
        signals: list[ThumbnailSignals],
        groups: list[ThumbnailStyleGroup],
        niche: str,
    ) -> str:
        """Generate a human-readable insight string."""
        if not signals:
            return f"No thumbnails analyzed for '{niche}'."

        text_pct = sum(1 for s in signals if s.has_text) / len(signals) * 100
        face_pct = sum(1 for s in signals if s.has_face) / len(signals) * 100
        avg_contrast = sum(s.contrast_level for s in signals) / len(signals)

        # Top colors across all thumbnails
        all_colors: list[str] = []
        for s in signals:
            all_colors.extend(s.dominant_colors)
        top_colors = [c for c, _ in Counter(all_colors).most_common(3)]
        color_str = "/".join(top_colors) if top_colors else "varied"

        parts: list[str] = [
            f"High-performing thumbnails in '{niche}' commonly use "
            f"{color_str} color schemes"
        ]

        if text_pct > 50:
            parts.append(f"with large text overlays ({text_pct:.0f}% prevalence)")
        if face_pct > 40:
            parts.append(f"and human faces ({face_pct:.0f}% prevalence)")
        if avg_contrast > 60:
            parts.append("featuring high contrast for visual pop")

        if groups:
            best = groups[0]
            parts.append(
                f". The most-viewed style is '{best.style_label}' "
                f"(avg {best.avg_views:,.0f} views)"
            )

        return " ".join(parts) + "."

    def _generate_recommendations(
        self,
        signals: list[ThumbnailSignals],
        groups: list[ThumbnailStyleGroup],
    ) -> list[str]:
        """Produce actionable thumbnail design recommendations."""
        recs: list[str] = []

        if not signals:
            return ["Insufficient data for recommendations."]

        text_pct = sum(1 for s in signals if s.has_text) / len(signals) * 100
        face_pct = sum(1 for s in signals if s.has_face) / len(signals) * 100
        avg_brightness = sum(s.brightness for s in signals) / len(signals)

        if text_pct > 60:
            recs.append("Use bold, large text overlay — it's standard in this niche.")
        elif text_pct < 30:
            recs.append("Minimal text on thumbnails performs well here — focus on visual imagery.")

        if face_pct > 50:
            recs.append("Include an expressive human face for emotional connection.")
        elif face_pct < 20:
            recs.append("Faces are rare in this niche — object/concept-focused thumbnails work best.")

        if avg_brightness > 60:
            recs.append("Use bright, well-lit imagery to match niche conventions.")
        elif avg_brightness < 35:
            recs.append("Dark/moody colour palettes perform well here.")

        # Color recommendation from best-performing group
        if groups:
            best = groups[0]
            if best.dominant_colors:
                color_list = ", ".join(best.dominant_colors)
                recs.append(
                    f"Top colour palette: {color_list} "
                    f"(from '{best.style_label}' style group)."
                )

        if not recs:
            recs.append("Experiment with high-contrast colours and clear focal points.")

        return recs
