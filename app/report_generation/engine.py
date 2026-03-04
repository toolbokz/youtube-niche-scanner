"""Report Generation Engine - produces JSON and Markdown reports."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from app.config import get_settings
from app.core.logging import get_logger
from app.core.models import (
    ChannelConcept,
    NicheReport,
    NicheScore,
    VideoBlueprint,
)

logger = get_logger(__name__)


class ReportGenerationEngine:
    """Generate structured reports in JSON and Markdown."""

    def __init__(self, output_dir: str | None = None) -> None:
        settings = get_settings()
        self.output_dir = Path(output_dir or settings.reports.output_directory)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_report(
        self,
        seed_keywords: list[str],
        top_niches: list[NicheScore],
        channel_concepts: list[ChannelConcept],
        video_blueprints: dict[str, list[VideoBlueprint]],
        metadata: dict[str, Any] | None = None,
    ) -> NicheReport:
        """Build the complete report model."""
        report = NicheReport(
            seed_keywords=seed_keywords,
            top_niches=top_niches,
            channel_concepts=channel_concepts,
            video_blueprints=video_blueprints,
            metadata=metadata or {},
        )
        return report

    def save_json(self, report: NicheReport, filename: str | None = None) -> Path:
        """Save report as JSON."""
        if filename is None:
            ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"niche_report_{ts}.json"

        path = self.output_dir / filename
        data = report.model_dump(mode="json")

        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)

        logger.info("json_report_saved", path=str(path))
        return path

    def save_markdown(self, report: NicheReport, filename: str | None = None) -> Path:
        """Save report as human-readable Markdown."""
        if filename is None:
            ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"niche_report_{ts}.md"

        path = self.output_dir / filename
        md = self._render_markdown(report)

        with open(path, "w") as f:
            f.write(md)

        logger.info("markdown_report_saved", path=str(path))
        return path

    def _render_markdown(self, report: NicheReport) -> str:
        """Render the report as Markdown."""
        lines: list[str] = []

        # Header
        lines.append("# YouTube Niche Discovery Report")
        lines.append(f"\n**Generated:** {report.generated_at.strftime('%Y-%m-%d %H:%M UTC')}")
        lines.append(f"**Seed Keywords:** {', '.join(report.seed_keywords)}")
        lines.append("")

        # Executive Summary
        lines.append("## Executive Summary")
        lines.append(f"\n- **Total niches analyzed:** {len(report.top_niches)}")
        if report.top_niches:
            best = report.top_niches[0]
            lines.append(f"- **Top niche:** {best.niche} (Score: {best.overall_score}/100)")
            lines.append(f"- **Highest trend momentum:** "
                         f"{max(n.trend_momentum for n in report.top_niches):.1f}")
        lines.append("")

        # ── Top Niches Table ──
        lines.append("## Top Niches Ranked")
        lines.append("")
        lines.append("| Rank | Niche | Score | Demand | Competition | Trend | Virality | CTR | Faceless |")
        lines.append("|------|-------|-------|--------|-------------|-------|----------|-----|----------|")

        for n in report.top_niches:
            lines.append(
                f"| {n.rank} | {n.niche} | **{n.overall_score}** | "
                f"{n.demand_score} | {n.competition_score} | {n.trend_momentum} | "
                f"{n.virality_score} | {n.ctr_potential} | {n.faceless_viability} |"
            )
        lines.append("")

        # ── Channel Concepts ──
        lines.append("## Channel Concepts")
        lines.append("")

        for concept in report.channel_concepts:
            lines.append(f"### {concept.niche}")
            lines.append(f"\n**Channel Name Ideas:** {', '.join(concept.channel_name_ideas)}")
            lines.append(f"\n**Positioning:** {concept.positioning}")
            lines.append(f"\n**Posting Cadence:** {concept.posting_cadence}")
            lines.append(f"\n**Estimated RPM:** ${concept.estimated_rpm:.2f}")
            lines.append(f"\n**Time to Monetization:** ~{concept.time_to_monetization_months} months")

            if concept.audience:
                lines.append(f"\n**Target Audience:** {concept.audience.age_range}")
                if concept.audience.pain_points:
                    lines.append("\n**Pain Points:**")
                    for pp in concept.audience.pain_points:
                        lines.append(f"- {pp}")
            lines.append("")

        # ── Video Blueprints ──
        lines.append("## Video Blueprints")
        lines.append("")

        for niche_name, blueprints in report.video_blueprints.items():
            lines.append(f"### {niche_name}")
            lines.append("")

            for i, bp in enumerate(blueprints, 1):
                lines.append(f"#### Video {i}: {bp.video_idea.title}")
                lines.append(f"\n**Topic:** {bp.video_idea.topic}")
                lines.append(f"**Angle:** {bp.video_idea.angle}")
                lines.append(f"**Difficulty:** {bp.video_idea.difficulty}")
                lines.append(f"**Est. Views:** {bp.video_idea.estimated_views}")

                # Titles
                lines.append(f"\n**Curiosity Gap Title:** {bp.curiosity_gap_headline}")
                lines.append(f"**SEO Title:** {bp.keyword_optimized_title}")
                if bp.alternative_titles:
                    lines.append("\n**Alternative Titles:**")
                    for t in bp.alternative_titles:
                        lines.append(f"- {t}")

                # Thumbnail
                lines.append(f"\n**Thumbnail:**")
                lines.append(f"- Emotion: {bp.thumbnail.emotion_trigger}")
                lines.append(f"- Focal Point: {bp.thumbnail.visual_focal_point}")
                lines.append(f"- Text Overlay: {bp.thumbnail.text_overlay}")
                lines.append(f"- Colors: {', '.join(bp.thumbnail.color_palette)}")

                # Script
                lines.append(f"\n**Script Structure:**")
                lines.append(f"- **Hook:** {bp.script_structure.hook[:200]}...")
                lines.append(f"- **Mid-video Loop:** {bp.script_structure.mid_video_curiosity_loop[:200]}...")

                lines.append("")
                lines.append("---")
                lines.append("")

        # ── Metadata ──
        if report.metadata:
            lines.append("## Analysis Metadata")
            lines.append("")
            for key, value in report.metadata.items():
                lines.append(f"- **{key}:** {value}")

        lines.append("\n---\n*Generated by Growth Strategist v1.0.0*")
        return "\n".join(lines)

    def save_all(
        self, report: NicheReport, base_name: str | None = None
    ) -> dict[str, Path]:
        """Save report in all configured formats."""
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        base = base_name or f"niche_report_{ts}"

        paths: dict[str, Path] = {}
        settings = get_settings()

        if "json" in settings.reports.format:
            paths["json"] = self.save_json(report, f"{base}.json")

        if "markdown" in settings.reports.format:
            paths["markdown"] = self.save_markdown(report, f"{base}.md")

        return paths
