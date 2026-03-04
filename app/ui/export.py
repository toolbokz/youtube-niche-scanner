"""Export utilities — JSON, Markdown and PNG export of discovery sessions."""
from __future__ import annotations

import io
import json
from datetime import datetime
from typing import Any


def export_json(report_data: dict[str, Any]) -> str:
    """Serialise the current discovery data as pretty-printed JSON."""
    return json.dumps(report_data, indent=2, default=str)


def export_markdown(report_data: dict[str, Any]) -> str:
    """Render a lightweight Markdown summary of the discovery session."""
    lines: list[str] = []
    lines.append("# Growth Strategist — Discovery Session")
    lines.append(f"\n**Generated:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")

    seeds = report_data.get("seed_keywords", [])
    if seeds:
        lines.append(f"**Seeds:** {', '.join(seeds)}")
    lines.append("")

    niches = report_data.get("top_niches", [])
    if niches:
        lines.append("## Top Niches\n")
        lines.append(
            "| Rank | Niche | Score | Demand | Comp. | Trend | Virality | CTR "
            "| Viral Opp. | Velocity |"
        )
        lines.append(
            "|------|-------|-------|--------|-------|-------|----------|-----"
            "|------------|----------|"
        )
        for n in niches:
            lines.append(
                f"| {n.get('rank','-')} | {n.get('niche','')} "
                f"| **{n.get('overall_score',0):.0f}** "
                f"| {n.get('demand_score',0):.0f} "
                f"| {n.get('competition_score',0):.0f} "
                f"| {n.get('trend_momentum',0):.0f} "
                f"| {n.get('virality_score',0):.0f} "
                f"| {n.get('ctr_potential',0):.0f} "
                f"| {n.get('viral_opportunity_score',0):.0f} "
                f"| {n.get('topic_velocity_score',0):.0f} |"
            )
        lines.append("")

    viral = report_data.get("viral_opportunities", {})
    if viral:
        lines.append("## Viral Opportunities\n")
        for niche_name, opps in viral.items():
            lines.append(f"### {niche_name}\n")
            for o in opps[:5]:
                lines.append(
                    f"- **{o.get('channel_name','')}** "
                    f"({o.get('channel_subscribers',0):,} subs) — "
                    f"*{o.get('video_title','')[:60]}* — "
                    f"{o.get('video_views',0):,} views "
                    f"({o.get('views_to_sub_ratio',0):.0f}× ratio)"
                )
            lines.append("")

    meta = report_data.get("metadata", {})
    if meta:
        lines.append("## Metadata\n")
        for k, v in meta.items():
            lines.append(f"- **{k}:** {v}")

    lines.append("\n---\n*Exported by Growth Strategist Discovery Map*")
    return "\n".join(lines)
