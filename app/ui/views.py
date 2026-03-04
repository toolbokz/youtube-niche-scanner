"""Page-view builders for each sidebar navigation section.

Each function takes the current report data (or None) and returns
a list of Dash components to render in the main content area.
"""
from __future__ import annotations

from typing import Any

import plotly.graph_objects as go
from dash import html, dcc
import dash_bootstrap_components as dbc

from app.ui.styles import (
    BG_PRIMARY, BG_SECONDARY, BG_CARD, BORDER,
    TEXT_PRIMARY, TEXT_SECONDARY,
    ACCENT_GREEN, ACCENT_BLUE, ACCENT_PURPLE, ACCENT_ORANGE,
    ACCENT_RED, ACCENT_PINK, ACCENT_CYAN,
)

_CARD = {
    "backgroundColor": BG_CARD,
    "border": f"1px solid {BORDER}",
    "borderRadius": "8px",
    "padding": "20px",
    "marginBottom": "16px",
}


def _empty(msg: str = "Run an analysis first to see data here.") -> html.Div:
    return html.Div(msg, style={
        "color": TEXT_SECONDARY, "fontSize": "13px",
        "textAlign": "center", "padding": "60px 20px",
        "opacity": "0.6",
    })


# ══════════════════════════════════════════════════════════════════════════════
#  Dashboard
# ══════════════════════════════════════════════════════════════════════════════

def build_dashboard_view(data: dict[str, Any] | None) -> list:
    if not data or "error" in data:
        return [_empty()]

    niches = data.get("top_niches", [])
    meta = data.get("metadata", {})
    viral_count = sum(len(v) for v in data.get("viral_opportunities", {}).values())
    vel_count = len(data.get("topic_velocities", {}))
    thumb_count = len(data.get("thumbnail_patterns", {}))

    # KPI row
    kpis = dbc.Row([
        _kpi_card("Niches Analysed", str(len(niches)), ACCENT_GREEN),
        _kpi_card("Viral Opportunities", str(viral_count), ACCENT_PINK),
        _kpi_card("Trend Signals", str(vel_count), ACCENT_PURPLE),
        _kpi_card("Thumbnail Groups", str(thumb_count), ACCENT_ORANGE),
        _kpi_card("Keywords Processed", str(meta.get("total_keywords_analyzed", "—")), ACCENT_BLUE),
        _kpi_card("Pipeline Duration", f"{meta.get('pipeline_duration_seconds', 0):.1f}s", ACCENT_CYAN),
    ], className="g-3 mb-4")

    # Score distribution chart
    if niches:
        scores = [n.get("overall_score", 0) for n in niches]
        names = [n.get("niche", "?")[:25] for n in niches]
        colors = [ACCENT_GREEN if s >= 70 else ACCENT_BLUE if s >= 45 else ACCENT_ORANGE for s in scores]

        fig = go.Figure(go.Bar(
            x=scores, y=names, orientation="h",
            marker_color=colors, marker_line_width=0,
        ))
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color=TEXT_SECONDARY, size=10),
            margin=dict(l=160, r=20, t=30, b=20),
            height=max(250, len(niches) * 32),
            xaxis=dict(title="Overall Score", gridcolor="rgba(255,255,255,0.06)", range=[0, 100]),
            yaxis=dict(gridcolor="rgba(255,255,255,0.04)", autorange="reversed"),
            title=dict(text="Niche Score Distribution", font=dict(size=13, color=TEXT_PRIMARY)),
        )
        score_chart = html.Div(
            dcc.Graph(figure=fig, config={"displayModeBar": False}),
            style=_CARD,
        )
    else:
        score_chart = html.Div()

    # Top 3 niches summary cards
    top_cards = []
    for i, n in enumerate(niches[:3], 1):
        medal = ["🥇", "🥈", "🥉"][i - 1]
        top_cards.append(dbc.Col(html.Div([
            html.Div(f"{medal}  #{i}", style={"fontSize": "12px", "color": TEXT_SECONDARY, "marginBottom": "4px"}),
            html.Div(n.get("niche", "?"), style={
                "fontSize": "16px", "fontWeight": "700", "color": TEXT_PRIMARY, "marginBottom": "8px",
            }),
            html.Div(f"Score: {n.get('overall_score', 0):.0f}/100", style={
                "fontSize": "24px", "fontWeight": "800",
                "color": ACCENT_GREEN if n.get("overall_score", 0) >= 70 else ACCENT_BLUE,
            }),
            html.Div([
                _mini_stat("Demand", n.get("demand_score", 0)),
                _mini_stat("Trend", n.get("trend_momentum", 0)),
                _mini_stat("Virality", n.get("virality_score", 0)),
                _mini_stat("CTR", n.get("ctr_potential", 0)),
            ], style={"marginTop": "12px"}),
        ], style=_CARD), md=4))

    top_row = dbc.Row(top_cards, className="mb-4") if top_cards else html.Div()

    return [
        html.H5("📊  Dashboard", style={"fontWeight": "700", "color": TEXT_PRIMARY, "marginBottom": "20px"}),
        kpis,
        top_row,
        score_chart,
    ]


# ══════════════════════════════════════════════════════════════════════════════
#  Niche Analysis
# ══════════════════════════════════════════════════════════════════════════════

def build_niche_analysis_view(data: dict[str, Any] | None) -> list:
    if not data or "error" in data:
        return [_empty()]

    niches = data.get("top_niches", [])
    if not niches:
        return [_empty("No niches found in the report.")]

    # Full ranking table
    table_header = html.Thead(html.Tr([
        html.Th("#"), html.Th("Niche"), html.Th("Score"),
        html.Th("Demand"), html.Th("Competition"), html.Th("Trend"),
        html.Th("Virality"), html.Th("CTR"), html.Th("Viral Opp"),
        html.Th("Velocity"),
    ], style={"fontSize": "11px", "color": TEXT_SECONDARY}))

    rows = []
    for n in niches:
        score = n.get("overall_score", 0)
        sc = ACCENT_GREEN if score >= 70 else ACCENT_BLUE if score >= 45 else ACCENT_ORANGE
        rows.append(html.Tr([
            html.Td(n.get("rank", ""), style={"fontWeight": "700", "color": ACCENT_CYAN}),
            html.Td(n.get("niche", "?"), style={"fontWeight": "600", "color": TEXT_PRIMARY}),
            html.Td(f"{score:.0f}", style={"fontWeight": "700", "color": sc}),
            html.Td(f"{n.get('demand_score', 0):.0f}"),
            html.Td(f"{n.get('competition_score', 0):.0f}"),
            html.Td(f"{n.get('trend_momentum', 0):.0f}"),
            html.Td(f"{n.get('virality_score', 0):.0f}"),
            html.Td(f"{n.get('ctr_potential', 0):.0f}"),
            html.Td(f"{n.get('viral_opportunity_score', 0):.0f}"),
            html.Td(f"{n.get('topic_velocity_score', 0):.0f}"),
        ], style={"fontSize": "12px", "color": TEXT_SECONDARY}))

    table = dbc.Table(
        [table_header, html.Tbody(rows)],
        bordered=False, hover=True, responsive=True, size="sm",
        style={"backgroundColor": "transparent"},
        className="table-dark",
    )

    # Keyword breakdown per niche
    kw_sections = []
    for n in niches[:10]:
        kws = n.get("keywords", [])
        if kws:
            chips = [
                html.Span(kw, style={
                    "display": "inline-block", "padding": "2px 8px", "margin": "2px",
                    "borderRadius": "12px", "fontSize": "10px",
                    "background": BG_SECONDARY, "color": TEXT_SECONDARY,
                    "border": f"1px solid {BORDER}",
                }) for kw in kws[:12]
            ]
            kw_sections.append(html.Div([
                html.Div(n.get("niche", "?"), style={
                    "fontSize": "12px", "fontWeight": "600", "color": TEXT_PRIMARY,
                    "marginBottom": "4px", "marginTop": "12px",
                }),
                html.Div(chips),
            ]))

    kw_card = html.Div([
        html.H6("Keywords per Niche", style={"color": TEXT_PRIMARY, "fontSize": "13px", "fontWeight": "700"}),
        *kw_sections,
    ], style=_CARD) if kw_sections else html.Div()

    return [
        html.H5("🔍  Niche Analysis", style={"fontWeight": "700", "color": TEXT_PRIMARY, "marginBottom": "20px"}),
        html.Div(table, style=_CARD),
        kw_card,
    ]


# ══════════════════════════════════════════════════════════════════════════════
#  Video Strategy
# ══════════════════════════════════════════════════════════════════════════════

def build_video_strategy_view(data: dict[str, Any] | None) -> list:
    if not data or "error" in data:
        return [_empty()]

    blueprints = data.get("video_blueprints", {})
    concepts = data.get("channel_concepts", [])

    if not blueprints and not concepts:
        return [_empty("No video strategy data available.")]

    sections: list = [
        html.H5("🎬  Video Strategy", style={"fontWeight": "700", "color": TEXT_PRIMARY, "marginBottom": "20px"}),
    ]

    # Channel concepts
    if concepts:
        concept_cards = []
        for c in concepts:
            names = ", ".join(c.get("channel_name_ideas", [])[:3])
            concept_cards.append(html.Div([
                html.Div([
                    html.Span(c.get("niche", "?"), style={
                        "fontSize": "14px", "fontWeight": "700", "color": TEXT_PRIMARY,
                    }),
                    html.Span(f"  RPM ${c.get('estimated_rpm', 0):.2f}", style={
                        "fontSize": "11px", "color": ACCENT_GREEN, "marginLeft": "12px",
                    }),
                ]),
                html.Div(c.get("positioning", ""), style={
                    "fontSize": "12px", "color": TEXT_SECONDARY, "margin": "6px 0",
                }),
                html.Div(f"Names: {names}", style={"fontSize": "11px", "color": TEXT_SECONDARY}),
                html.Div(
                    f"Cadence: {c.get('posting_cadence', '—')} · "
                    f"Monetisation: ~{c.get('time_to_monetization_months', '—')} months",
                    style={"fontSize": "11px", "color": TEXT_SECONDARY, "marginTop": "4px"},
                ),
            ], style=_CARD))
        sections.append(html.H6("📺  Channel Concepts", style={
            "color": TEXT_PRIMARY, "fontWeight": "600", "marginBottom": "12px",
        }))
        sections.extend(concept_cards)

    # Blueprints
    if blueprints:
        sections.append(html.H6("🎯  Video Blueprints", style={
            "color": TEXT_PRIMARY, "fontWeight": "600", "margin": "24px 0 12px",
        }))
        for niche_name, bps in blueprints.items():
            sections.append(html.Div(niche_name, style={
                "fontSize": "13px", "fontWeight": "700", "color": ACCENT_GREEN,
                "margin": "16px 0 8px", "borderBottom": f"1px solid {BORDER}",
                "paddingBottom": "4px",
            }))
            for i, bp in enumerate(bps[:5], 1):
                idea = bp.get("video_idea", {})
                sections.append(html.Div([
                    html.Div(f"{i}. {idea.get('title', 'Untitled')}", style={
                        "fontSize": "12px", "fontWeight": "600", "color": TEXT_PRIMARY,
                    }),
                    html.Div([
                        html.Span(f"Angle: {idea.get('angle', '—')}", style={"marginRight": "16px"}),
                        html.Span(f"Difficulty: {idea.get('difficulty', '—')}", style={"marginRight": "16px"}),
                        html.Span(f"Est: {idea.get('estimated_views', '—')}"),
                    ], style={"fontSize": "11px", "color": TEXT_SECONDARY, "marginTop": "2px"}),
                    html.Div(f"SEO Title: {bp.get('keyword_optimized_title', '')}", style={
                        "fontSize": "11px", "color": TEXT_SECONDARY, "fontStyle": "italic", "marginTop": "2px",
                    }),
                ], style={
                    "padding": "10px 16px", "marginBottom": "6px",
                    "backgroundColor": BG_SECONDARY, "borderRadius": "6px",
                    "border": f"1px solid {BORDER}",
                }))

    return sections


# ══════════════════════════════════════════════════════════════════════════════
#  Reports view
# ══════════════════════════════════════════════════════════════════════════════

def build_reports_view(data: dict[str, Any] | None) -> list:
    if not data or "error" in data:
        return [_empty()]

    sections: list = [
        html.H5("📋  Reports", style={"fontWeight": "700", "color": TEXT_PRIMARY, "marginBottom": "20px"}),
    ]

    # Viral opportunities
    viral_opps = data.get("viral_opportunities", {})
    if viral_opps:
        sections.append(html.H6("🔥 Viral Opportunities", style={
            "color": ACCENT_PINK, "fontWeight": "700", "marginBottom": "12px",
        }))
        for niche_name, opps in viral_opps.items():
            if not opps:
                continue
            sections.append(html.Div(f"{niche_name} — {len(opps)} anomalies", style={
                "fontSize": "13px", "fontWeight": "600", "color": TEXT_PRIMARY,
                "margin": "12px 0 6px",
            }))
            rows = []
            for opp in sorted(opps, key=lambda o: o.get("opportunity_score", 0), reverse=True)[:8]:
                rows.append(html.Tr([
                    html.Td(opp.get("channel_name", ""), style={"maxWidth": "120px", "overflow": "hidden", "textOverflow": "ellipsis"}),
                    html.Td(f"{opp.get('channel_subscribers', 0):,}"),
                    html.Td(opp.get("video_title", "")[:45], style={"maxWidth": "200px"}),
                    html.Td(f"{opp.get('video_views', 0):,}"),
                    html.Td(f"{opp.get('views_to_sub_ratio', 0):.0f}×"),
                    html.Td(f"{opp.get('opportunity_score', 0):.0f}", style={"color": ACCENT_PINK, "fontWeight": "600"}),
                ], style={"fontSize": "11px", "color": TEXT_SECONDARY}))
            tbl = dbc.Table(
                [html.Thead(html.Tr([
                    html.Th("Channel"), html.Th("Subs"), html.Th("Video"),
                    html.Th("Views"), html.Th("Ratio"), html.Th("Score"),
                ], style={"fontSize": "10px", "color": TEXT_SECONDARY})), html.Tbody(rows)],
                bordered=False, hover=True, responsive=True, size="sm",
                className="table-dark", style={"backgroundColor": "transparent"},
            )
            sections.append(html.Div(tbl, style={**_CARD, "padding": "12px"}))

    # Topic velocity
    velocities = data.get("topic_velocities", {})
    if velocities:
        sections.append(html.H6("📈 Topic Velocity", style={
            "color": ACCENT_PURPLE, "fontWeight": "700", "margin": "24px 0 12px",
        }))
        for niche_name, vel in velocities.items():
            v = vel if isinstance(vel, dict) else {}
            gr = v.get("growth_rate", 0)
            acc = v.get("acceleration", 0)
            vs = v.get("velocity_score", 0)
            trend = "⬆ Accelerating" if acc > 0.2 else "⬇ Decelerating" if acc < -0.2 else "➡ Steady"
            sections.append(html.Div([
                html.Span(niche_name, style={"fontWeight": "600", "color": TEXT_PRIMARY, "fontSize": "12px"}),
                html.Span(f"  {trend}", style={"fontSize": "11px", "color": TEXT_SECONDARY, "marginLeft": "8px"}),
                html.Div(
                    f"Growth: {gr:.2f}× · Acceleration: {acc:+.2f} · Score: {vs:.0f}/100",
                    style={"fontSize": "11px", "color": TEXT_SECONDARY, "marginTop": "2px"},
                ),
            ], style={**_CARD, "padding": "12px"}))

    # Thumbnail patterns
    thumb_patterns = data.get("thumbnail_patterns", {})
    if thumb_patterns:
        sections.append(html.H6("🎨 Thumbnail Patterns", style={
            "color": ACCENT_ORANGE, "fontWeight": "700", "margin": "24px 0 12px",
        }))
        for niche_name, tp in thumb_patterns.items():
            t = tp if isinstance(tp, dict) else {}
            insight = t.get("insight", "")
            recs = t.get("recommendations", [])
            parts = [
                html.Div(niche_name, style={"fontWeight": "600", "color": TEXT_PRIMARY, "fontSize": "12px"}),
                html.Div(f"{t.get('total_analyzed', 0)} thumbnails analysed", style={
                    "fontSize": "11px", "color": TEXT_SECONDARY,
                }),
            ]
            if insight:
                parts.append(html.Div(insight, style={
                    "fontSize": "11px", "color": TEXT_SECONDARY, "fontStyle": "italic", "marginTop": "4px",
                }))
            for r in recs[:4]:
                parts.append(html.Div(f"• {r}", style={"fontSize": "11px", "color": TEXT_SECONDARY, "paddingLeft": "8px"}))
            sections.append(html.Div(parts, style={**_CARD, "padding": "12px"}))

    # AI insights
    ai = data.get("ai_insights", {})
    if ai and "error" not in ai:
        sections.append(html.H6("🧠 AI Insights", style={
            "color": ACCENT_CYAN, "fontWeight": "700", "margin": "24px 0 12px",
        }))
        na = ai.get("niche_analysis", {})
        if isinstance(na, dict):
            rec = na.get("overall_recommendation", "")
            if rec:
                sections.append(html.Div(rec, style={
                    "fontSize": "12px", "color": TEXT_SECONDARY, "lineHeight": "1.6",
                    **_CARD, "padding": "16px",
                }))

    if not viral_opps and not velocities and not thumb_patterns:
        sections.append(_empty("No detailed report data available yet."))

    return sections


# ══════════════════════════════════════════════════════════════════════════════
#  System Status
# ══════════════════════════════════════════════════════════════════════════════

def build_system_status_view(data: dict[str, Any] | None, health: dict[str, Any] | None = None) -> list:
    meta = data.get("metadata", {}) if data else {}

    items = [
        ("Backend", health.get("status", "unknown") if health else "checking…",
         ACCENT_GREEN if health and health.get("status") in ("ok", "healthy") else ACCENT_RED),
        ("Version", health.get("version", "—") if health else "—", TEXT_SECONDARY),
        ("Pipeline Duration", f"{meta.get('pipeline_duration_seconds', '—')}s", TEXT_SECONDARY),
        ("Total Keywords", str(meta.get("total_keywords_analyzed", "—")), TEXT_SECONDARY),
        ("Total Clusters", str(meta.get("total_clusters", "—")), TEXT_SECONDARY),
        ("Viral Opps Found", str(meta.get("viral_opportunities_found", "—")), TEXT_SECONDARY),
        ("Velocity Niches", str(meta.get("niches_with_velocity_data", "—")), TEXT_SECONDARY),
        ("Thumbnail Scans", str(meta.get("niches_with_thumbnail_analysis", "—")), TEXT_SECONDARY),
        ("AI Enhanced", "Yes" if meta.get("ai_enhanced") else "No", ACCENT_GREEN if meta.get("ai_enhanced") else TEXT_SECONDARY),
        ("Discovery Mode", "Yes" if meta.get("discovery_mode") else "No", TEXT_SECONDARY),
    ]

    rows = [
        html.Tr([
            html.Td(label, style={"fontSize": "12px", "color": TEXT_SECONDARY}),
            html.Td(value, style={"fontSize": "12px", "fontWeight": "600", "color": color}),
        ]) for label, value, color in items
    ]

    table = dbc.Table(
        html.Tbody(rows),
        bordered=False, hover=True, responsive=True, size="sm",
        className="table-dark", style={"backgroundColor": "transparent"},
    )

    return [
        html.H5("⚙️  System Status", style={"fontWeight": "700", "color": TEXT_PRIMARY, "marginBottom": "20px"}),
        html.Div(table, style=_CARD),
    ]


# ── helpers ───────────────────────────────────────────────────────────────────

def _kpi_card(label: str, value: str, color: str) -> dbc.Col:
    return dbc.Col(html.Div([
        html.Div(value, style={
            "fontSize": "22px", "fontWeight": "800", "color": color, "lineHeight": "1.1",
        }),
        html.Div(label, style={
            "fontSize": "10px", "color": TEXT_SECONDARY, "marginTop": "2px",
        }),
    ], style={
        "textAlign": "center", "padding": "16px",
        "borderRadius": "8px", "backgroundColor": BG_CARD,
        "border": f"1px solid {BORDER}",
    }), xs=6, md=4, lg=2)


def _mini_stat(label: str, value: float) -> html.Div:
    return html.Div([
        html.Span(f"{label}: ", style={"color": TEXT_SECONDARY, "fontSize": "10px"}),
        html.Span(f"{value:.0f}", style={"color": TEXT_PRIMARY, "fontSize": "10px", "fontWeight": "600"}),
    ], style={"marginBottom": "2px"})
