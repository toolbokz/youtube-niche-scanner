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
        compilation_strategies: list[dict[str, Any]] | None = None,
        ai_insights: dict[str, Any] | None = None,
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
            compilation_strategies=compilation_strategies or [],
            ai_insights=ai_insights or {},
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
                            f"| {sg.text_prevalence:.0f}% | {sg.face_prevalence:.0f}% "
                            f"| {sg.avg_contrast:.1f} |"
                        )

                if tp.recommendations:
                    lines.append("\n**Recommendations:**")
                    for rec in tp.recommendations:
                        lines.append(f"- {rec}")
                lines.append("")
            lines.append("")

        # ── AI-Powered Insights ──
        if report.ai_insights and "error" not in report.ai_insights:
            lines.append("## 🧠 AI-Powered Insights (Gemini)")
            lines.append("")

            # Niche analysis
            na = report.ai_insights.get("niche_analysis", {})
            if na and "error" not in na:
                lines.append("### AI Niche Analysis")
                rec = na.get("overall_recommendation", "")
                if rec:
                    lines.append(f"\n{rec}\n")

                growth = na.get("growth_potential", [])
                if growth:
                    lines.append("**Growth Potential:**\n")
                    for item in growth[:5]:
                        if isinstance(item, dict):
                            lines.append(f"- **{item.get('niche', '?')}**: {item.get('assessment', '')}")
                        else:
                            lines.append(f"- {item}")
                    lines.append("")

                strategy = na.get("content_strategy_insights", [])
                if strategy:
                    lines.append("**Content Strategy Insights:**\n")
                    for item in strategy[:5]:
                        if isinstance(item, dict):
                            lines.append(f"- **{item.get('niche', '?')}**: {item.get('strategy', '')}")
                        else:
                            lines.append(f"- {item}")
                    lines.append("")

            # Trend forecast
            tf = report.ai_insights.get("trend_forecast", {})
            if tf and "error" not in tf:
                lines.append("### AI Trend Forecast")
                direction = tf.get("overall_market_direction", "")
                if direction:
                    lines.append(f"\n**Market Direction:** {direction}\n")

                forecasts = tf.get("trend_forecast", [])
                if forecasts:
                    for fc in forecasts[:5]:
                        if isinstance(fc, dict):
                            lines.append(
                                f"- **{fc.get('topic', '?')}** — "
                                f"Explosion likelihood: {fc.get('explosion_likelihood', '?')}, "
                                f"Peak: {fc.get('predicted_peak_timeframe', '?')}. "
                                f"{fc.get('reasoning', '')}"
                            )
                    lines.append("")

                subtopics = tf.get("emerging_subtopics", [])
                if subtopics:
                    lines.append("**Emerging Subtopics:**")
                    for st in subtopics[:8]:
                        lines.append(f"- {st}")
                    lines.append("")

            # Video strategy
            vs = report.ai_insights.get("video_strategy", {})
            if vs and "error" not in vs:
                ideas = vs.get("video_ideas", [])
                if ideas:
                    lines.append("### AI Video Strategy Ideas")
                    lines.append("")
                    for i, idea in enumerate(ideas[:10], 1):
                        if isinstance(idea, dict):
                            lines.append(f"**{i}. {idea.get('title', 'Untitled')}**")
                            lines.append(f"   Concept: {idea.get('concept', '')}")
                            lines.append(f"   Audience Hook: {idea.get('audience_hook', '')}")
                            lines.append("")
                    lines.append("")

            # Thumbnail strategy
            ts = report.ai_insights.get("thumbnail_strategy", {})
            if ts and "error" not in ts:
                lines.append("### AI Thumbnail Strategy")
                overall = ts.get("overall_recommendation", "")
                if overall:
                    lines.append(f"\n{overall}\n")

                color_strat = ts.get("color_strategy", {})
                if isinstance(color_strat, dict) and color_strat:
                    lines.append(
                        f"**Colors:** {', '.join(color_strat.get('primary_colors', []))} "
                        f"+ accent {color_strat.get('accent_color', '?')}"
                    )
                    lines.append(f"**Approach:** {color_strat.get('background_approach', '')}")
                    lines.append("")

                text_strat = ts.get("text_overlay", {})
                if isinstance(text_strat, dict) and text_strat:
                    lines.append(
                        f"**Text Overlay:** {'Recommended' if text_strat.get('recommended') else 'Optional'} "
                        f"— max {text_strat.get('max_words', '?')} words, "
                        f"{text_strat.get('font_style', '')} at {text_strat.get('placement', '')}"
                    )
                    lines.append("")

            # Viral interpretations
            vi = report.ai_insights.get("viral_interpretations", {})
            if vi:
                lines.append("### AI Viral Opportunity Interpretation")
                lines.append("")
                for niche_name_vi, interp in vi.items():
                    if isinstance(interp, dict) and "error" not in interp:
                        lines.append(f"**{niche_name_vi}:**")
                        themes = interp.get("common_themes", [])
                        if themes:
                            lines.append(f"- Themes: {', '.join(str(t) for t in themes[:5])}")
                        factors = interp.get("success_factors", [])
                        if factors:
                            lines.append(f"- Success factors: {', '.join(str(f) for f in factors[:5])}")
                        timing = interp.get("timing_insight", "")
                        if timing:
                            lines.append(f"- Timing: {timing}")
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

        # ── Compilation Strategies ──
        if hasattr(report, "compilation_strategies") and report.compilation_strategies:
            lines.append("## Compilation Video Strategies")
            lines.append("")

            for comp in report.compilation_strategies:
                lines.append(f"### {comp.get('niche', 'Unknown')} Compilation")
                lines.append(f"\n**Compilation Score:** {comp.get('compilation_score', 0)}/100")
                lines.append(f"**Source Videos Found:** {comp.get('total_source_videos_found', 0)}")

                concept = comp.get("final_video_concept", {})
                if concept:
                    lines.append(f"\n**Suggested Title:** {concept.get('title', 'N/A')}")
                    lines.append(f"**Duration:** ~{concept.get('estimated_duration_minutes', 0)} min")
                    lines.append(f"**Target Audience:** {concept.get('target_audience', 'N/A')}")
                    if concept.get("description"):
                        lines.append(f"\n**Description:**\n> {concept['description'][:300]}")

                sources = comp.get("source_videos", [])
                if sources:
                    lines.append("\n**Top Source Videos:**\n")
                    lines.append("| # | Title | Views | Engagement |")
                    lines.append("|---|-------|-------|------------|")
                    for i, sv in enumerate(sources[:10], 1):
                        title = sv.get("title", "")[:50]
                        views = f"{sv.get('view_count', 0):,}"
                        eng = f"{sv.get('engagement_score', 0)}/100"
                        lines.append(f"| {i} | {title} | {views} | {eng} |")

                structure = comp.get("video_structure", [])
                if structure:
                    lines.append(f"\n**Timeline ({len(structure)} clips):**\n")
                    for item in structure[:12]:
                        seg = item.get("segment")
                        seg_title = seg.get("source_video_title", "")[:30] if seg else "—"
                        lines.append(
                            f"- **{item.get('position', 0)}.** "
                            f"[{item.get('segment_type', '')}] "
                            f"{seg_title} ({item.get('duration_seconds', 0)}s)"
                        )

                editing = comp.get("editing_guidance", {})
                if editing:
                    lines.append(f"\n**Editing:** {editing.get('transition_style', '')}")
                    lines.append(f"**Music:** {editing.get('background_music_style', '')}")
                    lines.append(f"**Pacing:** {editing.get('pacing_notes', '')}")

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
