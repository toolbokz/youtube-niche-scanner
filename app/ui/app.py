"""Growth Strategist — Interactive Niche Discovery Map.

Run standalone:
    python -m app.ui.app          →  http://localhost:8050

Mounted inside FastAPI:
    python main.py serve          →  http://localhost:8000/map/
"""
from __future__ import annotations

import json
import time
from typing import Any

import dash
from dash import html, dcc, Input, Output, State, callback, no_update, ctx
import dash_bootstrap_components as dbc
import dash_cytoscape as cyto

from app.ui.api_client import APIClient
from app.ui.graph_engine import build_graph, graph_to_cytoscape, suggested_layout
from app.ui.styles import (
    BG_PRIMARY, BG_SECONDARY, BG_CARD, BORDER, TEXT_PRIMARY, TEXT_SECONDARY,
    ACCENT_GREEN, ACCENT_BLUE, ACCENT_PURPLE, ACCENT_ORANGE,
    ACCENT_PINK, ACCENT_CYAN, CYTOSCAPE_STYLESHEET,
)
from app.ui.panels import (
    build_niche_panel, build_viral_panel, build_trend_panel,
    build_keyword_panel,
)
from app.ui.export import export_json, export_markdown

# ══════════════════════════════════════════════════════════════════════════════
#  App initialisation
# ══════════════════════════════════════════════════════════════════════════════

# When imported by FastAPI routes, __name__ == "app.ui.app" → mounted mode.
# When run directly via `python -m app.ui.app`, __name__ == "__main__".
_MOUNTED = __name__ != "__main__"
_REQ_PREFIX = "/map/" if _MOUNTED else "/"

cyto.load_extra_layouts()

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.DARKLY],
    title="Growth Strategist · Discovery Map",
    update_title="Discovering…",
    suppress_callback_exceptions=True,
    routes_pathname_prefix="/",
    requests_pathname_prefix=_REQ_PREFIX,
)

api = APIClient()

# ══════════════════════════════════════════════════════════════════════════════
#  Style constants (inline)
# ══════════════════════════════════════════════════════════════════════════════

_SIDEBAR_W = "260px"
_PANEL_W = "380px"

FONT_STACK = "'Inter', 'Segoe UI', system-ui, -apple-system, sans-serif"

_page_style: dict[str, Any] = {
    "fontFamily": FONT_STACK,
    "backgroundColor": BG_PRIMARY,
    "color": TEXT_PRIMARY,
    "height": "100vh",
    "display": "flex",
    "overflow": "hidden",
}

_sidebar_style: dict[str, Any] = {
    "width": _SIDEBAR_W,
    "minWidth": _SIDEBAR_W,
    "height": "100vh",
    "backgroundColor": BG_SECONDARY,
    "borderRight": f"1px solid {BORDER}",
    "display": "flex",
    "flexDirection": "column",
    "padding": "0",
    "overflowY": "auto",
}

_main_style: dict[str, Any] = {
    "flex": "1",
    "display": "flex",
    "flexDirection": "column",
    "height": "100vh",
    "overflow": "hidden",
}

_graph_style: dict[str, Any] = {
    "flex": "1",
    "position": "relative",
}

_panel_style: dict[str, Any] = {
    "width": _PANEL_W,
    "minWidth": _PANEL_W,
    "height": "100vh",
    "backgroundColor": BG_CARD,
    "borderLeft": f"1px solid {BORDER}",
    "overflowY": "auto",
    "padding": "20px",
    "display": "none",  # hidden until a node is selected
}


# ══════════════════════════════════════════════════════════════════════════════
#  Layout helpers
# ══════════════════════════════════════════════════════════════════════════════


def _nav_item(icon: str, label: str, active: bool = False) -> html.Div:
    bg = "rgba(0,230,118,0.08)" if active else "transparent"
    border = f"3px solid {ACCENT_GREEN}" if active else "3px solid transparent"
    return html.Div(
        html.Div([
            html.Span(icon, style={"fontSize": "16px", "marginRight": "10px"}),
            html.Span(label, style={"fontSize": "13px"}),
        ], style={
            "display": "flex", "alignItems": "center",
            "padding": "10px 20px",
            "borderLeft": border,
            "backgroundColor": bg,
            "color": TEXT_PRIMARY if active else TEXT_SECONDARY,
            "cursor": "pointer",
            "transition": "all 0.2s",
        }),
    )


def _stat_pill(value: str, label: str, color: str = ACCENT_GREEN) -> html.Div:
    return html.Div([
        html.Span(value, style={
            "fontSize": "18px", "fontWeight": "700", "color": color,
        }),
        html.Div(label, style={
            "fontSize": "10px", "color": TEXT_SECONDARY, "marginTop": "-2px",
        }),
    ], style={
        "textAlign": "center", "padding": "8px 16px",
        "borderRadius": "8px", "backgroundColor": BG_SECONDARY,
        "border": f"1px solid {BORDER}",
    })


# ══════════════════════════════════════════════════════════════════════════════
#  Sidebar
# ══════════════════════════════════════════════════════════════════════════════

sidebar = html.Div([
    # Logo / brand
    html.Div([
        html.Div("◈", style={
            "fontSize": "28px", "color": ACCENT_GREEN,
            "fontWeight": "800", "lineHeight": "1",
        }),
        html.Div("Growth Strategist", style={
            "fontSize": "15px", "fontWeight": "700",
            "color": TEXT_PRIMARY, "marginTop": "2px",
        }),
        html.Div("Niche Intelligence Platform", style={
            "fontSize": "10px", "color": TEXT_SECONDARY, "marginTop": "1px",
        }),
    ], style={
        "padding": "24px 20px 20px",
        "borderBottom": f"1px solid {BORDER}",
    }),

    # Navigation
    html.Div([
        _nav_item("🗺️", "Discovery Map", active=True),
        _nav_item("📊", "Dashboard"),
        _nav_item("🔍", "Niche Analysis"),
        _nav_item("🎬", "Video Strategy"),
        _nav_item("📋", "Reports"),
        _nav_item("⚙️", "System Status"),
    ], style={"marginTop": "8px"}),

    html.Hr(style={"borderColor": BORDER, "margin": "12px 20px"}),

    # ── Discovery controls ────────────────────────────────────────────
    html.Div([
        html.Label("Seed Keywords", style={
            "fontSize": "11px", "color": TEXT_SECONDARY, "marginBottom": "6px",
            "display": "block",
        }),
        dbc.Textarea(
            id="seed-input",
            placeholder="e.g. ai tools, passive income, health tips",
            style={
                "backgroundColor": BG_PRIMARY, "border": f"1px solid {BORDER}",
                "color": TEXT_PRIMARY, "fontSize": "12px",
                "borderRadius": "6px", "resize": "vertical",
                "minHeight": "60px",
            },
            value="",
        ),

        html.Label("Top N Niches", style={
            "fontSize": "11px", "color": TEXT_SECONDARY,
            "marginTop": "12px", "marginBottom": "4px", "display": "block",
        }),
        dcc.Slider(
            id="topn-slider",
            min=3, max=30, step=1, value=10,
            marks={3: "3", 10: "10", 20: "20", 30: "30"},
            tooltip={"placement": "bottom"},
        ),

        html.Label("Videos per Niche", style={
            "fontSize": "11px", "color": TEXT_SECONDARY,
            "marginTop": "10px", "marginBottom": "4px", "display": "block",
        }),
        dcc.Slider(
            id="vpn-slider",
            min=3, max=20, step=1, value=10,
            marks={3: "3", 10: "10", 20: "20"},
            tooltip={"placement": "bottom"},
        ),

        # Action buttons
        html.Div([
            dbc.Button(
                [html.Span("▶ "), "Run Analysis"],
                id="btn-analyze",
                color="success",
                size="sm",
                className="w-100 mb-2",
                style={"fontWeight": "600", "fontSize": "12px"},
            ),
            dbc.Button(
                [html.Span("🔍 "), "Auto-Discover"],
                id="btn-discover",
                outline=True,
                color="info",
                size="sm",
                className="w-100 mb-2",
                style={"fontSize": "12px"},
            ),
            dbc.Button(
                [html.Span("🧠 "), "Deep Discover"],
                id="btn-deep-discover",
                outline=True,
                color="warning",
                size="sm",
                className="w-100 mb-2",
                style={"fontSize": "12px"},
            ),
            dbc.Button(
                [html.Span("🗑 "), "Clear Map"],
                id="btn-clear",
                outline=True,
                color="secondary",
                size="sm",
                className="w-100",
                style={"fontSize": "12px"},
            ),
        ], style={"marginTop": "16px"}),
    ], style={"padding": "0 20px"}),

    # Spacer
    html.Div(style={"flex": "1"}),

    # Backend status
    html.Div(id="backend-status", style={
        "padding": "12px 20px",
        "borderTop": f"1px solid {BORDER}",
        "fontSize": "10px",
        "color": TEXT_SECONDARY,
    }),
], style=_sidebar_style)


# ══════════════════════════════════════════════════════════════════════════════
#  Header bar
# ══════════════════════════════════════════════════════════════════════════════

header = html.Div([
    html.Div([
        html.Span("Niche Discovery Map", style={
            "fontSize": "16px", "fontWeight": "700", "color": TEXT_PRIMARY,
        }),
        html.Span(id="status-text", style={
            "fontSize": "11px", "color": TEXT_SECONDARY, "marginLeft": "16px",
        }),
    ]),

    # Layer toggle switches
    html.Div([
        dbc.Checklist(
            id="layer-toggles",
            options=[
                {"label": " Keywords", "value": "keywords"},
                {"label": " Viral", "value": "viral"},
                {"label": " Trends", "value": "trends"},
            ],
            value=["keywords", "viral", "trends"],
            inline=True,
            switch=True,
            style={"fontSize": "11px", "color": TEXT_SECONDARY},
        ),
        dbc.ButtonGroup([
            dbc.Button("JSON", id="btn-export-json", outline=True, color="secondary", size="sm",
                        style={"fontSize": "10px", "padding": "2px 8px"}),
            dbc.Button("MD", id="btn-export-md", outline=True, color="secondary", size="sm",
                        style={"fontSize": "10px", "padding": "2px 8px"}),
            dbc.Button("PNG", id="btn-export-png", outline=True, color="secondary", size="sm",
                        style={"fontSize": "10px", "padding": "2px 8px"}),
        ], style={"marginLeft": "16px"}),
    ], style={"display": "flex", "alignItems": "center"}),
], style={
    "display": "flex", "justifyContent": "space-between", "alignItems": "center",
    "padding": "10px 20px",
    "backgroundColor": BG_SECONDARY,
    "borderBottom": f"1px solid {BORDER}",
    "minHeight": "48px",
})


# ══════════════════════════════════════════════════════════════════════════════
#  Stats bar (below header, populated after discovery)
# ══════════════════════════════════════════════════════════════════════════════

stats_bar = html.Div(
    id="stats-bar",
    style={
        "display": "none",
        "gap": "12px", "padding": "10px 20px",
        "backgroundColor": BG_PRIMARY,
        "borderBottom": f"1px solid {BORDER}",
        "overflowX": "auto",
    },
)


# ══════════════════════════════════════════════════════════════════════════════
#  Cytoscape graph workspace
# ══════════════════════════════════════════════════════════════════════════════

graph_workspace = html.Div([
    cyto.Cytoscape(
        id="graph",
        elements=[],
        layout={"name": "cose", "animate": True, "animationDuration": 800},
        stylesheet=CYTOSCAPE_STYLESHEET,
        style={"width": "100%", "height": "100%", "backgroundColor": BG_PRIMARY},
        responsive=True,
        minZoom=0.15,
        maxZoom=4.0,
        autoRefreshLayout=True,
    ),
    # Empty-state overlay
    html.Div(
        id="empty-overlay",
        children=[
            html.Div("◈", style={
                "fontSize": "56px", "color": ACCENT_GREEN, "opacity": "0.3",
                "marginBottom": "12px",
            }),
            html.Div("No Data Yet", style={
                "fontSize": "20px", "fontWeight": "700", "color": TEXT_SECONDARY,
                "opacity": "0.5", "marginBottom": "8px",
            }),
            html.Div(
                "Enter seed keywords and click Run Analysis, "
                "or use Auto-Discover to explore trending niches.",
                style={
                    "fontSize": "12px", "color": TEXT_SECONDARY,
                    "opacity": "0.4", "maxWidth": "320px", "textAlign": "center",
                },
            ),
        ],
        style={
            "position": "absolute", "inset": "0",
            "display": "flex", "flexDirection": "column",
            "alignItems": "center", "justifyContent": "center",
            "pointerEvents": "none",
        },
    ),
], style=_graph_style)


# ══════════════════════════════════════════════════════════════════════════════
#  Right-side analysis panel
# ══════════════════════════════════════════════════════════════════════════════

analysis_panel = html.Div(
    id="analysis-panel",
    children=[
        html.Div("Select a node", style={
            "color": TEXT_SECONDARY, "fontSize": "12px", "padding": "40px 0",
            "textAlign": "center",
        }),
    ],
    style=_panel_style,
)


# ══════════════════════════════════════════════════════════════════════════════
#  Loading overlay
# ══════════════════════════════════════════════════════════════════════════════

loading_overlay = html.Div(
    id="loading-overlay",
    children=[
        dbc.Spinner(color="success", type="grow", size="lg"),
        html.Div(id="loading-text", children="Running analysis…", style={
            "color": TEXT_PRIMARY, "fontSize": "14px", "marginTop": "16px",
            "fontWeight": "500",
        }),
    ],
    style={
        "position": "fixed", "inset": "0",
        "display": "none",
        "flexDirection": "column",
        "alignItems": "center", "justifyContent": "center",
        "backgroundColor": "rgba(13,17,23,0.85)",
        "zIndex": "9999",
    },
)


# ══════════════════════════════════════════════════════════════════════════════
#  Stores
# ══════════════════════════════════════════════════════════════════════════════

stores = html.Div([
    dcc.Store(id="store-report", data=None),         # raw pipeline response
    dcc.Store(id="store-graph-data", data=None),      # graph elements cache
    dcc.Store(id="store-png-trigger", data=0),         # PNG export trigger
    dcc.Download(id="download-json"),
    dcc.Download(id="download-md"),
    dcc.Interval(id="health-interval", interval=30_000, n_intervals=0),
])


# ══════════════════════════════════════════════════════════════════════════════
#  Page layout
# ══════════════════════════════════════════════════════════════════════════════

app.layout = html.Div([
    sidebar,
    html.Div([
        header,
        stats_bar,
        graph_workspace,
    ], style=_main_style),
    analysis_panel,
    loading_overlay,
    stores,
], style=_page_style)


# ══════════════════════════════════════════════════════════════════════════════
#  Callbacks
# ══════════════════════════════════════════════════════════════════════════════


# ── 1. Run Analysis ──────────────────────────────────────────────────────────

@callback(
    Output("store-report", "data"),
    Output("loading-overlay", "style"),
    Output("loading-text", "children"),
    Input("btn-analyze", "n_clicks"),
    Input("btn-discover", "n_clicks"),
    Input("btn-deep-discover", "n_clicks"),
    State("seed-input", "value"),
    State("topn-slider", "value"),
    State("vpn-slider", "value"),
    prevent_initial_call=True,
)
def run_pipeline(
    n_analyze: int | None,
    n_discover: int | None,
    n_deep: int | None,
    seeds_text: str,
    top_n: int,
    vpn: int,
):
    """Fire off an analyze or discover run via the backend."""
    triggered = ctx.triggered_id
    if not triggered:
        return no_update, no_update, no_update

    # Show loading overlay
    overlay_show = {
        "position": "fixed", "inset": "0",
        "display": "flex", "flexDirection": "column",
        "alignItems": "center", "justifyContent": "center",
        "backgroundColor": "rgba(13,17,23,0.85)", "zIndex": "9999",
    }

    try:
        if triggered == "btn-analyze":
            seeds = [s.strip() for s in (seeds_text or "").split(",") if s.strip()]
            if not seeds:
                return no_update, no_update, no_update
            result = api.analyze(seeds, top_n=top_n, videos_per_niche=vpn)
        elif triggered == "btn-discover":
            result = api.discover(deep=False, top_n=top_n, videos_per_niche=vpn)
        elif triggered == "btn-deep-discover":
            result = api.discover(deep=True, top_n=top_n, videos_per_niche=vpn)
        else:
            return no_update, no_update, no_update
    except Exception as exc:
        return (
            {"error": str(exc)},
            {**overlay_show, "display": "none"},
            "",
        )

    # Hide loading overlay
    overlay_hide = {**overlay_show, "display": "none"}
    return result, overlay_hide, ""


# ── 2. Build graph from report data ─────────────────────────────────────────

@callback(
    Output("graph", "elements"),
    Output("graph", "layout"),
    Output("store-graph-data", "data"),
    Output("empty-overlay", "style"),
    Output("status-text", "children"),
    Output("stats-bar", "children"),
    Output("stats-bar", "style"),
    Input("store-report", "data"),
    Input("layer-toggles", "value"),
    Input("btn-clear", "n_clicks"),
    prevent_initial_call=True,
)
def update_graph(
    report_data: dict | None,
    layers: list[str],
    n_clear: int | None,
):
    """Rebuild the cytoscape graph whenever report data or layer toggles change."""
    triggered = ctx.triggered_id

    # Clear map
    if triggered == "btn-clear":
        empty_style = {
            "position": "absolute", "inset": "0",
            "display": "flex", "flexDirection": "column",
            "alignItems": "center", "justifyContent": "center",
            "pointerEvents": "none",
        }
        stats_hidden = {
            "display": "none", "gap": "12px", "padding": "10px 20px",
            "backgroundColor": BG_PRIMARY, "borderBottom": f"1px solid {BORDER}",
        }
        return [], {"name": "preset"}, None, empty_style, "", [], stats_hidden

    if not report_data or "error" in report_data:
        err_msg = report_data.get("error", "") if report_data else ""
        return no_update, no_update, no_update, no_update, f"Error: {err_msg}", no_update, no_update

    # Build graph
    show_kw = "keywords" in (layers or [])
    show_viral = "viral" in (layers or [])
    show_trends = "trends" in (layers or [])

    G = build_graph(report_data)
    elements = graph_to_cytoscape(G, show_keywords=show_kw, show_viral=show_viral, show_trends=show_trends)
    layout = suggested_layout(len(elements))

    # Hide empty overlay
    hidden = {
        "position": "absolute", "inset": "0",
        "display": "none", "pointerEvents": "none",
    }

    # Status text
    niches = report_data.get("top_niches", [])
    n_nodes = sum(1 for e in elements if "source" not in e["data"])
    n_edges = sum(1 for e in elements if "source" in e["data"])
    status = f"{len(niches)} niches · {n_nodes} nodes · {n_edges} edges"

    # Stats bar pills
    top = niches[0] if niches else {}
    best_score = f"{top.get('overall_score', 0):.0f}" if top else "—"
    best_name = top.get("niche", "—") if top else "—"
    viral_count = sum(len(v) for v in report_data.get("viral_opportunities", {}).values())

    pills = [
        _stat_pill(str(len(niches)), "Niches", ACCENT_GREEN),
        _stat_pill(best_score, f"Top: {best_name[:20]}", ACCENT_BLUE),
        _stat_pill(str(viral_count), "Viral Opps", ACCENT_PINK),
        _stat_pill(str(len(report_data.get("topic_velocities", {}))), "Trend Signals", ACCENT_PURPLE),
        _stat_pill(str(n_nodes), "Graph Nodes", ACCENT_CYAN),
    ]
    stats_visible = {
        "display": "flex", "gap": "12px", "padding": "10px 20px",
        "backgroundColor": BG_PRIMARY, "borderBottom": f"1px solid {BORDER}",
        "overflowX": "auto",
    }

    return elements, layout, report_data, hidden, status, pills, stats_visible


# ── 3. Node tap → side panel ────────────────────────────────────────────────

@callback(
    Output("analysis-panel", "children"),
    Output("analysis-panel", "style"),
    Input("graph", "tapNodeData"),
    State("store-report", "data"),
    prevent_initial_call=True,
)
def on_node_tap(tap_data: dict | None, report_data: dict | None):
    """Display analysis panel when a node is tapped."""
    if not tap_data:
        return no_update, no_update

    node_type = tap_data.get("node_type", "")

    visible_style = {**_panel_style, "display": "block"}

    # Close button
    close_btn = html.Div(
        "✕",
        id="btn-close-panel",
        style={
            "position": "absolute", "top": "12px", "right": "16px",
            "cursor": "pointer", "fontSize": "18px", "color": TEXT_SECONDARY,
            "zIndex": "10",
        },
    )

    panel_wrapper_style = {"position": "relative"}

    if node_type == "niche" and report_data:
        children = build_niche_panel(tap_data, report_data)
    elif node_type == "viral":
        children = build_viral_panel(tap_data)
    elif node_type == "trend":
        children = build_trend_panel(tap_data)
    elif node_type == "keyword":
        children = build_keyword_panel(tap_data)
    else:
        children = [html.Div("Unknown node type", style={"color": TEXT_SECONDARY})]

    content = html.Div([close_btn, *children], style=panel_wrapper_style)
    return content, visible_style


# ── 4. Close panel ──────────────────────────────────────────────────────────

@callback(
    Output("analysis-panel", "style", allow_duplicate=True),
    Input("btn-close-panel", "n_clicks"),
    prevent_initial_call=True,
)
def close_panel(_: int | None):
    return _panel_style  # display: none


# ── 5. Export JSON ──────────────────────────────────────────────────────────

@callback(
    Output("download-json", "data"),
    Input("btn-export-json", "n_clicks"),
    State("store-report", "data"),
    prevent_initial_call=True,
)
def export_json_cb(_: int | None, report_data: dict | None):
    if not report_data:
        return no_update
    return dict(
        content=export_json(report_data),
        filename="growth-strategist-report.json",
        type="text/json",
    )


# ── 6. Export Markdown ──────────────────────────────────────────────────────

@callback(
    Output("download-md", "data"),
    Input("btn-export-md", "n_clicks"),
    State("store-report", "data"),
    prevent_initial_call=True,
)
def export_md_cb(_: int | None, report_data: dict | None):
    if not report_data:
        return no_update
    return dict(
        content=export_markdown(report_data),
        filename="growth-strategist-report.md",
        type="text/markdown",
    )


# ── 7. Export PNG (client-side via Cytoscape generateImage) ─────────────────

app.clientside_callback(
    """
    function(n_clicks) {
        if (!n_clicks) return window.dash_clientside.no_update;
        // Find the cytoscape instance and trigger PNG export
        var cy_el = document.getElementById('graph');
        if (cy_el && cy_el._cyreg && cy_el._cyreg.cy) {
            var cy = cy_el._cyreg.cy;
            var png = cy.png({full: true, scale: 2, bg: '#0d1117'});
            var a = document.createElement('a');
            a.href = png;
            a.download = 'growth-strategist-map.png';
            a.click();
        }
        return window.dash_clientside.no_update;
    }
    """,
    Output("store-png-trigger", "data"),
    Input("btn-export-png", "n_clicks"),
    prevent_initial_call=True,
)


# ── 8. Backend health check ────────────────────────────────────────────────

@callback(
    Output("backend-status", "children"),
    Input("health-interval", "n_intervals"),
)
def check_health(_: int):
    """Periodic health check of the FastAPI backend."""
    result = api.health()
    if result.get("status") in ("ok", "healthy"):
        version = result.get("version", "?")
        return html.Span([
            html.Span("● ", style={"color": ACCENT_GREEN}),
            f"Backend online · v{version}",
        ])
    return html.Span([
        html.Span("● ", style={"color": ACCENT_RED}),
        "Backend offline",
    ])


# ── 9. Show loading overlay on button clicks ───────────────────────────────

app.clientside_callback(
    """
    function(n1, n2, n3) {
        return {
            "position": "fixed", "inset": "0",
            "display": "flex", "flexDirection": "column",
            "alignItems": "center", "justifyContent": "center",
            "backgroundColor": "rgba(13,17,23,0.85)", "zIndex": "9999"
        };
    }
    """,
    Output("loading-overlay", "style", allow_duplicate=True),
    Input("btn-analyze", "n_clicks"),
    Input("btn-discover", "n_clicks"),
    Input("btn-deep-discover", "n_clicks"),
    prevent_initial_call=True,
)


# ══════════════════════════════════════════════════════════════════════════════
#  Entry point
# ══════════════════════════════════════════════════════════════════════════════

server = app.server  # for gunicorn/production

if __name__ == "__main__":
    app.run(debug=True, port=8050)
