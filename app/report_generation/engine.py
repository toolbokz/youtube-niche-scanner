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
    ThumbnailPatternResult,
    TopicVelocityResult,
    VideoBlueprint,
    ViralOpportunity,
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
        viral_opportunities: dict[str, list[ViralOpportunity]] | None = None,
        topic_velocities: dict[str, TopicVelocityResult] | None = None,
        thumbnail_patterns: dict[str, ThumbnailPatternResult] | None = None,
    ) -> NicheReport:
        """Build the complete report model."""
        report = NicheReport(
            seed_keywords=seed_keywords,
            top_niches=top_niches,
            channel_concepts=channel_concepts,
            video_blueprints=video_blueprints,
            viral_opportunities=viral_opportunities or {},
            topic_velocities=topic_velocities or {},
            thumbnail_patterns=thumbnail_patterns or {},
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
        lines.append(
            "| Rank | Niche | Score | Demand | Competition | Trend "
            "| Virality | CTR | Viral Opp. | Velocity |"
        )
        lines.append(
            "|------|-------|-------|--------|-------------|-------"
            "|----------|-----|------------|----------|"
        )

        for n in report.top_niches:
            lines.append(
                f"| {n.rank} | {n.niche} | **{n.overall_score}** | "
                f"{n.demand_score} | {n.competition_score} | {n.trend_momentum} | "
                f"{n.virality_score} | {n.ctr_potential} | "
                f"{n.viral_opportunity_score} | {n.topic_velocity_score} |"
            )
        lines.append("")

        # ── Why Niches Ranked Highly ──
        if report.top_niches:
            lines.append("## Why These Niches Ranked Highly")
            lines.append("")
            for n in report.top_niches[:5]:
                lines.append(f"### #{n.rank} — {n.niche} (Score: {n.overall_score})")
                strengths: list[str] = []
                if n.demand_score >= 70:
                    strengths.append(f"Strong demand ({n.demand_score})")
                if n.competition_score >= 60:
                    strengths.append(f"Favorable competition gap ({n.competition_score})")
                if n.trend_momentum >= 60:
                    strengths.append(f"High trend momentum ({n.trend_momentum})")
                if n.virality_score >= 60:
                    strengths.append(f"Viral potential ({n.virality_score})")
                if n.viral_opportunity_score >= 50:
                    strengths.append(
                        f"Small-channel viral success ({n.viral_opportunity_score})"
                    )
                if n.topic_velocity_score >= 50:
                    strengths.append(
                        f"Accelerating content uploads ({n.topic_velocity_score})"
                    )
                if n.ctr_potential >= 60:
                    strengths.append(f"High CTR potential ({n.ctr_potential})")
                if strengths:
                    lines.append("\n**Key Strengths:**")
                    for s in strengths:
                        lines.append(f"- {s}")
                else:
                    lines.append("\nBalanced scores across all metrics.")
                lines.append("")

        # ── Viral Opportunities ──
        if report.viral_opportunities:
            lines.append("## Viral Opportunity Detector")
            lines.append("")
            lines.append(
                "Small channels (<50K subscribers) achieving outsized viewership, "
                "indicating exploitable content gaps."
            )
            lines.append("")

            for niche_name, opps in report.viral_opportunities.items():
                if not opps:
                    continue
                lines.append(f"### {niche_name}")
                lines.append(f"\n**{len(opps)} viral anomalies detected**\n")
                lines.append(
                    "| Channel | Subscribers | Video | Views "
                    "| Views/Sub Ratio | Age (days) | Score |"
                )
                lines.append(
                    "|---------|------------|-------|-------"
                    "|----------------|------------|-------|"
                )
                for opp in sorted(opps, key=lambda o: o.opportunity_score, reverse=True)[:10]:
                    lines.append(
                        f"| {opp.channel_name} | {opp.channel_subscribers:,} "
                        f"| {opp.video_title[:50]} | {opp.video_views:,} "
                        f"| {opp.views_to_sub_ratio:.1f}x "
                        f"| {opp.video_age_days} | {opp.opportunity_score:.0f} |"
                    )
                lines.append("")
            lines.append("")

        # ── Topic Velocity ──
        if report.topic_velocities:
            lines.append("## Topic Velocity Analysis")
            lines.append("")
            lines.append(
                "Measures how fast content upload volume is growing — "
                "rising velocity signals an emerging opportunity window."
            )
            lines.append("")

            for niche_name, vel in report.topic_velocities.items():
                lines.append(f"### {niche_name}")
                trend_label = (
                    "Accelerating" if vel.acceleration > 0.2
                    else "Decelerating" if vel.acceleration < -0.2
                    else "Steady"
                )
                lines.append(
                    f"\n- **Growth Rate:** {vel.growth_rate:.2f}x "
                    f"(newest week vs oldest)"
                )
                lines.append(f"- **Acceleration:** {vel.acceleration:+.2f}")
                lines.append(f"- **Trend:** {trend_label}")
                lines.append(f"- **Velocity Score:** {vel.velocity_score:.0f}/100")

                if vel.weekly_volumes:
                    lines.append("\n**Weekly Upload Volume:**")
                    lines.append("")
                    lines.append("| Week | Uploads |")
                    lines.append("|------|---------|")
                    for wv in vel.weekly_volumes:
                        bar = "█" * min(wv.upload_count, 50)
                        lines.append(f"| {wv.week_label} | {wv.upload_count} {bar} |")
                lines.append("")
            lines.append("")

        # ── Thumbnail Patterns ──
        if report.thumbnail_patterns:
            lines.append("## Thumbnail Pattern Analysis")
            lines.append("")
            lines.append(
                "Visual analysis of top-performing thumbnails to identify "
                "winning design patterns."
            )
            lines.append("")

            for niche_name, tp in report.thumbnail_patterns.items():
                lines.append(f"### {niche_name}")
                lines.append(f"\n*{tp.total_analyzed} thumbnails analyzed*")

                if tp.insight:
                    lines.append(f"\n**Insight:** {tp.insight}")

                if tp.style_groups:
                    lines.append("\n**Dominant Styles:**\n")
                    lines.append(
                        "| Style | Count | Avg Views | Colors "
                        "| Text % | Face % | Contrast |"
                    )
                    lines.append(
                        "|-------|-------|-----------|--------"
                        "|--------|--------|----------|"
                    )
                    for sg in tp.style_groups:
                        colors = ", ".join(sg.dominant_colors[:3]) if sg.dominant_colors else "—"
                        lines.append(
                            f"| {sg.style_label} | {sg.count} "
                            f"| {sg.avg_views:,.0f} | {colors} "
                            f"| {sg.text_prevalence:.0%} | {sg.face_prevalence:.0%} "
                            f"| {sg.avg_contrast:.1f} |"
                        )

                if tp.recommendations:
                    lines.append("\n**Recommendations:**")
                    for rec in tp.recommendations:
                        lines.append(f"- {rec}")
                lines.append("")
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
