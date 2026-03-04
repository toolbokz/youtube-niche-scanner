"""Cytoscape stylesheet definitions for the discovery map.

Defines visual mappings for node types, states, and edge types
using a dark analytics theme.
"""
from __future__ import annotations

# ── Base dark-theme palette ───────────────────────────────────────────────────

BG_PRIMARY = "#0d1117"
BG_SECONDARY = "#161b22"
BG_CARD = "#1c2128"
BORDER = "#30363d"
TEXT_PRIMARY = "#e6edf3"
TEXT_SECONDARY = "#8b949e"
ACCENT_GREEN = "#00e676"
ACCENT_BLUE = "#29b6f6"
ACCENT_PURPLE = "#7c4dff"
ACCENT_ORANGE = "#ffa726"
ACCENT_RED = "#ef5350"
ACCENT_CYAN = "#00bcd4"
ACCENT_PINK = "#ff1744"

# ── Cytoscape stylesheet ─────────────────────────────────────────────────────

CYTOSCAPE_STYLESHEET: list[dict] = [
    # ── Default node ──────────────────────────────────────────────────
    {
        "selector": "node",
        "style": {
            "label": "data(label)",
            "font-size": "10px",
            "font-family": "'Inter', 'Segoe UI', sans-serif",
            "color": TEXT_PRIMARY,
            "text-valign": "bottom",
            "text-halign": "center",
            "text-margin-y": 8,
            "text-max-width": "100px",
            "text-wrap": "ellipsis",
            "background-color": "#546e7a",
            "border-width": 1,
            "border-color": BORDER,
            "width": 24,
            "height": 24,
            "transition-property": "background-color, width, height, border-color",
            "transition-duration": "0.3s",
        },
    },

    # ── Niche nodes ───────────────────────────────────────────────────
    {
        "selector": "node.niche",
        "style": {
            "shape": "ellipse",
            "font-size": "12px",
            "font-weight": "600",
            "width": "mapData(score, 0, 100, 36, 110)",
            "height": "mapData(score, 0, 100, 36, 110)",
            "background-color": ACCENT_BLUE,
            "border-width": 2,
            "border-color": "#1e88e5",
            "text-valign": "bottom",
        },
    },
    {
        "selector": "node.niche.high-opp",
        "style": {
            "background-color": ACCENT_GREEN,
            "border-color": "#00c853",
            "shadow-blur": 12,
            "shadow-color": ACCENT_GREEN,
            "shadow-opacity": 0.4,
        },
    },
    {
        "selector": "node.niche.med-opp",
        "style": {
            "background-color": ACCENT_BLUE,
            "border-color": "#0288d1",
        },
    },
    {
        "selector": "node.niche.low-opp",
        "style": {
            "background-color": ACCENT_ORANGE,
            "border-color": "#ef6c00",
        },
    },
    {
        "selector": "node.niche.high-comp",
        "style": {
            "border-color": ACCENT_RED,
            "border-width": 3,
        },
    },

    # ── Keyword nodes ─────────────────────────────────────────────────
    {
        "selector": "node.keyword",
        "style": {
            "shape": "round-rectangle",
            "width": 18,
            "height": 18,
            "font-size": "8px",
            "background-color": "#37474f",
            "border-width": 0,
            "opacity": 0.7,
            "text-valign": "bottom",
        },
    },

    # ── Viral opportunity nodes ───────────────────────────────────────
    {
        "selector": "node.viral-glow",
        "style": {
            "shape": "diamond",
            "width": "mapData(score, 0, 100, 20, 60)",
            "height": "mapData(score, 0, 100, 20, 60)",
            "background-color": ACCENT_PINK,
            "border-color": "#ff5252",
            "border-width": 2,
            "shadow-blur": 18,
            "shadow-color": ACCENT_PINK,
            "shadow-opacity": 0.6,
            "font-size": "9px",
        },
    },

    # ── Trend nodes ───────────────────────────────────────────────────
    {
        "selector": "node.trend-pulse",
        "style": {
            "shape": "triangle",
            "width": "mapData(score, 0, 100, 18, 55)",
            "height": "mapData(score, 0, 100, 18, 55)",
            "background-color": ACCENT_PURPLE,
            "border-color": "#651fff",
            "border-width": 1,
            "font-size": "9px",
        },
    },

    # ── Selected node ─────────────────────────────────────────────────
    {
        "selector": "node:selected",
        "style": {
            "border-width": 4,
            "border-color": "#ffffff",
            "shadow-blur": 20,
            "shadow-color": "#ffffff",
            "shadow-opacity": 0.5,
        },
    },

    # ── Default edge ──────────────────────────────────────────────────
    {
        "selector": "edge",
        "style": {
            "width": 1,
            "line-color": "#263238",
            "curve-style": "bezier",
            "opacity": 0.35,
            "transition-property": "opacity, line-color",
            "transition-duration": "0.3s",
        },
    },

    # ── Membership edges (niche→keyword) ──────────────────────────────
    {
        "selector": "edge.membership",
        "style": {
            "line-color": "#37474f",
            "width": 1,
            "opacity": 0.2,
        },
    },

    # ── Shared keyword edges (niche↔niche) ────────────────────────────
    {
        "selector": "edge.shared",
        "style": {
            "line-color": ACCENT_CYAN,
            "width": "mapData(weight, 1, 10, 1, 4)",
            "opacity": 0.45,
            "line-style": "solid",
        },
    },

    # ── Viral opportunity edges ───────────────────────────────────────
    {
        "selector": "edge.viral-edge",
        "style": {
            "line-color": ACCENT_PINK,
            "width": 1.5,
            "opacity": 0.5,
            "line-style": "dashed",
        },
    },

    # ── Trend velocity edges ──────────────────────────────────────────
    {
        "selector": "edge.trend_velocity",
        "style": {
            "line-color": ACCENT_PURPLE,
            "width": 1.5,
            "opacity": 0.5,
        },
    },

    # ── Hover effects (applied via callback tap highlighting) ─────────
    {
        "selector": "node:active",
        "style": {
            "overlay-opacity": 0.15,
            "overlay-color": "#ffffff",
        },
    },
    {
        "selector": "edge:active",
        "style": {
            "opacity": 0.8,
        },
    },
]
