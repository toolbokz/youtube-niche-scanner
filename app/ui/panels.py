"""Side-panel component builders for niche analysis detail views."""
from __future__ import annotations

from typing import Any

import plotly.graph_objects as go
from dash import html, dcc
import dash_bootstrap_components as dbc

from app.ui.styles import (
    BG_CARD, BG_SECONDARY, BORDER, TEXT_PRIMARY, TEXT_SECONDARY,
    ACCENT_GREEN, ACCENT_BLUE, ACCENT_RED, ACCENT_ORANGE,
    ACCENT_PURPLE, ACCENT_PINK, ACCENT_CYAN,
)


# ══════════════════════════════════════════════════════════════════════════════
#  Score breakdown radar
# ══════════════════════════════════════════════════════════════════════════════


def score_radar(node_data: dict[str, Any]) -> go.Figure:
    """Build a radar chart for the niche score breakdown."""
    categories = [
        "Demand", "Competition\n(opportunity)", "Trend",
        "Virality", "CTR", "Viral Opp.", "Velocity",
    ]
    values = [
        node_data.get("demand", 0),
        100 - node_data.get("competition", 50),
        node_data.get("trend", 0),
        node_data.get("virality", 0),
        node_data.get("ctr", 0),
        node_data.get("viral_opp", 0),
        node_data.get("velocity", 0),
    ]
    values.append(values[0])  # close the polygon
    categories.append(categories[0])

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=values,
        theta=categories,
        fill="toself",
        fillcolor="rgba(0,230,118,0.15)",
        line=dict(color=ACCENT_GREEN, width=2),
        marker=dict(size=5, color=ACCENT_GREEN),
    ))

    fig.update_layout(
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(
                visible=True, range=[0, 100], showticklabels=False,
                gridcolor="rgba(255,255,255,0.08)",
            ),
            angularaxis=dict(
                gridcolor="rgba(255,255,255,0.08)",
                linecolor="rgba(255,255,255,0.08)",
            ),
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT_PRIMARY, size=10),
        margin=dict(l=50, r=50, t=20, b=20),
        height=280,
        showlegend=False,
    )
    return fig


# ══════════════════════════════════════════════════════════════════════════════
#  Velocity spark chart
# ══════════════════════════════════════════════════════════════════════════════


def velocity_chart(vel_data: dict[str, Any]) -> go.Figure:
    """Weekly upload volume bar chart."""
    weeks = vel_data.get("weekly_volumes", [])
    labels = [w.get("week_label", "") for w in weeks]
    counts = [w.get("upload_count", 0) for w in weeks]

    colors = [ACCENT_PURPLE] * len(counts)
    if counts:
        colors[-1] = ACCENT_GREEN  # highlight most recent

    fig = go.Figure(go.Bar(
        x=labels, y=counts,
        marker_color=colors,
        marker_line_width=0,
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT_SECONDARY, size=9),
        margin=dict(l=30, r=10, t=10, b=40),
        height=160,
        xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
        yaxis=dict(gridcolor="rgba(255,255,255,0.05)", title="Uploads"),
        bargap=0.3,
    )
    return fig


# ══════════════════════════════════════════════════════════════════════════════
#  Thumbnail pattern donut
# ══════════════════════════════════════════════════════════════════════════════


def thumbnail_donut(thumb_data: dict[str, Any]) -> go.Figure:
    """Donut chart of thumbnail style group distribution."""
    groups = thumb_data.get("style_groups", [])
    labels = [g.get("style_label", "?") for g in groups]
    sizes = [g.get("count", 0) for g in groups]
    palette = [ACCENT_BLUE, ACCENT_GREEN, ACCENT_ORANGE, ACCENT_PURPLE, ACCENT_PINK]

    fig = go.Figure(go.Pie(
        labels=labels, values=sizes,
        hole=0.55,
        marker=dict(colors=palette[: len(labels)], line=dict(color=BG_CARD, width=2)),
        textfont=dict(size=10, color=TEXT_PRIMARY),
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT_PRIMARY, size=10),
        margin=dict(l=10, r=10, t=10, b=10),
        height=200,
        showlegend=True,
        legend=dict(font=dict(size=9, color=TEXT_SECONDARY)),
    )
    return fig


# ══════════════════════════════════════════════════════════════════════════════
#  Panel builders
# ══════════════════════════════════════════════════════════════════════════════


def _score_badge(value: float, label: str, color: str) -> dbc.Col:
    """Small score badge."""
    return dbc.Col(
        html.Div([
            html.Div(f"{value:.0f}", style={
                "fontSize": "20px", "fontWeight": "700", "color": color,
            }),
            html.Div(label, style={
                "fontSize": "10px", "color": TEXT_SECONDARY, "marginTop": "-2px",
            }),
        ], style={"textAlign": "center"}),
        width=3,
    )


def build_niche_panel(
    node_data: dict[str, Any],
    report_data: dict[str, Any],
) -> list:
    """Build the full side-panel content for a selected niche node."""
    niche_name = node_data.get("label", "Unknown")
    score = node_data.get("score", 0)
    rank = node_data.get("rank", 0)

    # Score header
    header = html.Div([
        html.Div([
            html.Span(f"#{rank}", style={
                "fontSize": "14px", "color": TEXT_SECONDARY, "marginRight": "8px",
            }),
            html.Span(niche_name, style={
                "fontSize": "18px", "fontWeight": "700", "color": TEXT_PRIMARY,
            }),
        ]),
        html.Div(f"{score:.0f}", style={
            "fontSize": "36px", "fontWeight": "800",
            "color": ACCENT_GREEN if score >= 70 else ACCENT_BLUE if score >= 45 else ACCENT_ORANGE,
            "lineHeight": "1",
        }),
        html.Div("Overall Score", style={"fontSize": "11px", "color": TEXT_SECONDARY}),
    ], style={"marginBottom": "16px"})

    # Score badges row
    badges = dbc.Row([
        _score_badge(node_data.get("demand", 0), "Demand", ACCENT_GREEN),
        _score_badge(100 - node_data.get("competition", 50), "Opp.", ACCENT_CYAN),
        _score_badge(node_data.get("trend", 0), "Trend", ACCENT_PURPLE),
        _score_badge(node_data.get("virality", 0), "Viral", ACCENT_PINK),
    ], className="g-1 mb-3")

    # Radar chart
    radar = dcc.Graph(
        figure=score_radar(node_data),
        config={"displayModeBar": False},
        style={"marginBottom": "12px"},
    )

    children = [header, badges, radar]

    # ── Keywords ──────────────────────────────────────────────────────
    keywords = node_data.get("keywords", [])
    if keywords:
        kw_chips = html.Div([
            html.Span(kw, style={
                "display": "inline-block", "padding": "2px 8px",
                "margin": "2px", "borderRadius": "12px",
                "fontSize": "10px", "background": "#263238",
                "color": TEXT_SECONDARY,
            })
            for kw in keywords[:15]
        ])
        children.append(_section("Keywords", kw_chips))

    # ── Viral Opportunities ───────────────────────────────────────────
    virals = report_data.get("viral_opportunities", {}).get(niche_name, [])
    if virals:
        rows = []
        for v in virals[:5]:
            rows.append(html.Div([
                html.Div(v.get("video_title", "")[:55], style={
                    "fontSize": "11px", "color": TEXT_PRIMARY, "fontWeight": "500",
                }),
                html.Div(
                    f"{v.get('channel_name', '')} · "
                    f"{v.get('channel_subscribers', 0):,} subs · "
                    f"{v.get('video_views', 0):,} views · "
                    f"{v.get('views_to_sub_ratio', 0):.0f}× ratio",
                    style={"fontSize": "10px", "color": TEXT_SECONDARY},
                ),
            ], style={"padding": "6px 0", "borderBottom": f"1px solid {BORDER}"}))
        children.append(_section("🔥 Viral Opportunities", html.Div(rows)))

    # ── Topic Velocity ────────────────────────────────────────────────
    vel = report_data.get("topic_velocities", {}).get(niche_name)
    if vel:
        gr = vel.get("growth_rate", 0)
        acc = vel.get("acceleration", 0)
        vs = vel.get("velocity_score", 0)
        trend_lbl = "⬆ Accelerating" if acc > 0.2 else "⬇ Decelerating" if acc < -0.2 else "➡ Steady"
        vel_header = html.Div([
            html.Span(f"Velocity {vs:.0f}/100", style={
                "fontWeight": "600", "color": ACCENT_PURPLE, "fontSize": "13px",
            }),
            html.Span(f"  {trend_lbl}", style={
                "fontSize": "11px", "color": TEXT_SECONDARY, "marginLeft": "8px",
            }),
        ])
        chart = dcc.Graph(
            figure=velocity_chart(vel),
            config={"displayModeBar": False},
        )
        children.append(_section("📈 Topic Velocity", html.Div([vel_header, chart])))

    # ── Thumbnail Patterns ────────────────────────────────────────────
    thumb = report_data.get("thumbnail_patterns", {}).get(niche_name)
    if thumb:
        insight = thumb.get("insight", "")
        recs = thumb.get("recommendations", [])
        parts = []
        if insight:
            parts.append(html.P(insight, style={
                "fontSize": "11px", "color": TEXT_SECONDARY, "fontStyle": "italic",
            }))
        if thumb.get("style_groups"):
            parts.append(dcc.Graph(
                figure=thumbnail_donut(thumb),
                config={"displayModeBar": False},
            ))
        for r in recs[:4]:
            parts.append(html.Div(f"• {r}", style={
                "fontSize": "11px", "color": TEXT_SECONDARY, "paddingLeft": "8px",
            }))
        children.append(_section("🎨 Thumbnail Patterns", html.Div(parts)))

    # ── Video Blueprints ──────────────────────────────────────────────
    blueprints = report_data.get("video_blueprints", {}).get(niche_name, [])
    if blueprints:
        bp_items = []
        for i, bp in enumerate(blueprints[:5], 1):
            idea = bp.get("video_idea", {})
            bp_items.append(html.Div([
                html.Div(f"{i}. {idea.get('title', 'Untitled')}", style={
                    "fontSize": "12px", "fontWeight": "600", "color": TEXT_PRIMARY,
                }),
                html.Div(
                    f"Angle: {idea.get('angle', '—')} · "
                    f"Est: {idea.get('estimated_views', '—')} · "
                    f"Difficulty: {idea.get('difficulty', '—')}",
                    style={"fontSize": "10px", "color": TEXT_SECONDARY},
                ),
            ], style={"padding": "6px 0", "borderBottom": f"1px solid {BORDER}"}))
        children.append(_section("🎬 Video Ideas", html.Div(bp_items)))

    # ── Channel Concept ───────────────────────────────────────────────
    concepts = report_data.get("channel_concepts", [])
    concept = next((c for c in concepts if c.get("niche") == niche_name), None)
    if concept:
        children.append(_section("📺 Channel Concept", html.Div([
            html.Div(concept.get("positioning", ""), style={
                "fontSize": "11px", "color": TEXT_PRIMARY, "marginBottom": "6px",
            }),
            html.Div(
                f"RPM: ${concept.get('estimated_rpm', 0):.2f} · "
                f"Cadence: {concept.get('posting_cadence', '—')} · "
                f"Monetization: ~{concept.get('time_to_monetization_months', '—')} months",
                style={"fontSize": "10px", "color": TEXT_SECONDARY},
            ),
        ])))

    return children


def build_viral_panel(node_data: dict[str, Any]) -> list:
    """Panel for a viral-opportunity node."""
    return [
        html.Div([
            html.Div("🔥 Viral Anomaly", style={
                "fontSize": "14px", "fontWeight": "700", "color": ACCENT_PINK,
                "marginBottom": "8px",
            }),
            _kv("Video", node_data.get("title", "")),
            _kv("Channel", node_data.get("label", "")),
            _kv("Subscribers", f"{node_data.get('subs', 0):,}"),
            _kv("Views", f"{node_data.get('views', 0):,}"),
            _kv("Views/Sub Ratio", f"{node_data.get('ratio', 0):.1f}×"),
            _kv("Score", f"{node_data.get('score', 0):.0f}/100"),
        ]),
    ]


def build_trend_panel(node_data: dict[str, Any]) -> list:
    """Panel for a trend/velocity node."""
    return [
        html.Div([
            html.Div("📈 Trend Velocity", style={
                "fontSize": "14px", "fontWeight": "700", "color": ACCENT_PURPLE,
                "marginBottom": "8px",
            }),
            _kv("Growth Rate", f"{node_data.get('growth', 0):.2f}×"),
            _kv("Acceleration", f"{node_data.get('acceleration', 0):+.2f}"),
            _kv("Velocity Score", f"{node_data.get('score', 0):.0f}/100"),
        ]),
    ]


def build_keyword_panel(node_data: dict[str, Any]) -> list:
    """Panel for a keyword node."""
    return [
        html.Div([
            html.Div("🔑 Keyword", style={
                "fontSize": "14px", "fontWeight": "700", "color": ACCENT_CYAN,
                "marginBottom": "8px",
            }),
            html.Div(node_data.get("label", ""), style={
                "fontSize": "16px", "color": TEXT_PRIMARY, "fontWeight": "600",
            }),
        ]),
    ]


# ── helpers ───────────────────────────────────────────────────────────────────


def _section(title: str, content) -> html.Div:
    return html.Div([
        html.Div(title, style={
            "fontSize": "13px", "fontWeight": "700", "color": TEXT_PRIMARY,
            "marginBottom": "6px", "marginTop": "16px",
            "borderBottom": f"1px solid {BORDER}", "paddingBottom": "4px",
        }),
        content,
    ])


def _kv(key: str, value: str) -> html.Div:
    return html.Div([
        html.Span(f"{key}: ", style={"color": TEXT_SECONDARY, "fontSize": "11px"}),
        html.Span(value, style={"color": TEXT_PRIMARY, "fontSize": "11px", "fontWeight": "500"}),
    ], style={"marginBottom": "4px"})
