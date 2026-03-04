"""Graph construction engine — builds topic network from pipeline results.

Converts niche discovery data into a NetworkX graph, then into
dash-cytoscape elements for interactive network visualization.
"""
from __future__ import annotations

import math
from collections import Counter
from typing import Any

import networkx as nx


# ── Node type constants ───────────────────────────────────────────────────────

NODE_NICHE = "niche"
NODE_KEYWORD = "keyword"
NODE_VIRAL = "viral"
NODE_TREND = "trend"

# Color palette (dark-theme friendly)
_PALETTE = {
    "high_opportunity": "#00e676",   # green
    "medium_opportunity": "#29b6f6", # blue
    "low_opportunity": "#ffa726",    # orange
    "high_competition": "#ef5350",   # red
    "trend_rising": "#7c4dff",       # purple
    "viral_glow": "#ff1744",         # hot red
    "keyword": "#546e7a",            # muted grey-blue
    "edge_default": "#37474f",       # dark steel
    "edge_strong": "#00bcd4",        # cyan
}


def _opportunity_color(score: float) -> str:
    """Map an overall score (0-100) to a node color hex."""
    if score >= 70:
        return _PALETTE["high_opportunity"]
    if score >= 45:
        return _PALETTE["medium_opportunity"]
    return _PALETTE["low_opportunity"]


def _competition_color(comp: float) -> str:
    """Overlay color for high competition."""
    if comp >= 70:
        return _PALETTE["high_competition"]
    return ""


def _node_size(score: float, base: int = 30, scale: int = 70) -> int:
    """Scale node diameter by a 0-100 score."""
    return base + int((score / 100) * scale)


# ══════════════════════════════════════════════════════════════════════════════
#  Public API
# ══════════════════════════════════════════════════════════════════════════════


def build_graph(data: dict[str, Any]) -> nx.Graph:
    """Build a NetworkX graph from an AnalyzeResponse dict.

    Nodes:
        - niche clusters   (from top_niches)
        - keywords          (from niche.keywords)
        - viral opportunity (from viral_opportunities)
        - trend signals     (from topic_velocities)

    Edges:
        - niche ↔ keyword  (membership)
        - niche ↔ niche    (shared keywords)
        - niche ↔ viral    (opportunity link)
        - niche ↔ trend    (velocity link)
    """
    G = nx.Graph()

    niches: list[dict] = data.get("top_niches", [])
    viral: dict[str, list[dict]] = data.get("viral_opportunities", {})
    velocities: dict[str, dict] = data.get("topic_velocities", {})

    # ── 1. Niche nodes ────────────────────────────────────────────────
    niche_kw_map: dict[str, list[str]] = {}

    for n in niches:
        nid = f"niche:{n['niche']}"
        G.add_node(
            nid,
            label=n["niche"],
            node_type=NODE_NICHE,
            score=n.get("overall_score", 0),
            demand=n.get("demand_score", 0),
            competition=n.get("competition_score", 0),
            trend=n.get("trend_momentum", 0),
            virality=n.get("virality_score", 0),
            ctr=n.get("ctr_potential", 0),
            faceless=n.get("faceless_viability", 0),
            viral_opp=n.get("viral_opportunity_score", 0),
            velocity=n.get("topic_velocity_score", 0),
            rank=n.get("rank", 0),
            keywords=n.get("keywords", []),
        )
        niche_kw_map[nid] = n.get("keywords", [])

    # ── 2. Keyword nodes + edges ──────────────────────────────────────
    kw_owners: dict[str, list[str]] = {}  # keyword → list of niche ids
    for nid, kws in niche_kw_map.items():
        for kw in kws[:12]:  # cap to avoid clutter
            kid = f"kw:{kw}"
            kw_owners.setdefault(kw, []).append(nid)
            if not G.has_node(kid):
                G.add_node(kid, label=kw, node_type=NODE_KEYWORD)
            G.add_edge(nid, kid, edge_type="membership")

    # ── 3. Inter-niche edges (shared keywords) ────────────────────────
    for kw, owners in kw_owners.items():
        if len(owners) > 1:
            for i in range(len(owners)):
                for j in range(i + 1, len(owners)):
                    if G.has_edge(owners[i], owners[j]):
                        G[owners[i]][owners[j]]["weight"] = (
                            G[owners[i]][owners[j]].get("weight", 1) + 1
                        )
                    else:
                        G.add_edge(
                            owners[i], owners[j],
                            edge_type="shared_keywords", weight=1,
                        )

    # ── 4. Viral opportunity nodes ────────────────────────────────────
    for niche_name, opps in viral.items():
        nid = f"niche:{niche_name}"
        if not G.has_node(nid):
            continue
        for opp in opps[:5]:  # top 5 per niche
            vid = f"viral:{opp.get('video_id', opp.get('video_title', ''))}"
            G.add_node(
                vid,
                label=opp.get("channel_name", ""),
                node_type=NODE_VIRAL,
                score=opp.get("opportunity_score", 0),
                views=opp.get("video_views", 0),
                subs=opp.get("channel_subscribers", 0),
                ratio=opp.get("views_to_sub_ratio", 0),
                title=opp.get("video_title", ""),
            )
            G.add_edge(nid, vid, edge_type="viral_opportunity")

    # ── 5. Trend/velocity nodes ───────────────────────────────────────
    for niche_name, vel in velocities.items():
        nid = f"niche:{niche_name}"
        if not G.has_node(nid):
            continue
        tid = f"trend:{niche_name}"
        G.add_node(
            tid,
            label=f"↗ {niche_name}",
            node_type=NODE_TREND,
            score=vel.get("velocity_score", 0),
            growth=vel.get("growth_rate", 0),
            acceleration=vel.get("acceleration", 0),
        )
        G.add_edge(nid, tid, edge_type="trend_velocity")

    return G


# ══════════════════════════════════════════════════════════════════════════════
#  Cytoscape element conversion
# ══════════════════════════════════════════════════════════════════════════════


def graph_to_cytoscape(
    G: nx.Graph,
    show_keywords: bool = True,
    show_viral: bool = True,
    show_trends: bool = True,
) -> list[dict[str, Any]]:
    """Convert a NetworkX graph to a list of cytoscape elements.

    Applies visual mappings: size, color, classes.
    """
    elements: list[dict[str, Any]] = []

    # ── Nodes ─────────────────────────────────────────────────────────
    for node_id, attrs in G.nodes(data=True):
        ntype = attrs.get("node_type", "")

        # Filtering toggles
        if ntype == NODE_KEYWORD and not show_keywords:
            continue
        if ntype == NODE_VIRAL and not show_viral:
            continue
        if ntype == NODE_TREND and not show_trends:
            continue

        score = attrs.get("score", 0)

        # Build CSS-friendly classes string
        classes = ntype
        if ntype == NODE_NICHE:
            if score >= 70:
                classes += " high-opp"
            elif score >= 45:
                classes += " med-opp"
            else:
                classes += " low-opp"
            comp = attrs.get("competition", 0)
            if comp >= 70:
                classes += " high-comp"
        if ntype == NODE_VIRAL:
            classes += " viral-glow"
        if ntype == NODE_TREND:
            classes += " trend-pulse"

        el: dict[str, Any] = {
            "data": {
                "id": node_id,
                "label": attrs.get("label", node_id),
                "node_type": ntype,
                "score": score,
                **{k: v for k, v in attrs.items()
                   if k not in ("label", "node_type", "score")},
            },
            "classes": classes,
        }
        elements.append(el)

    # ── Edges ─────────────────────────────────────────────────────────
    node_ids = {e["data"]["id"] for e in elements if "id" in e["data"]}
    for u, v, attrs in G.edges(data=True):
        # Skip edges whose endpoints were filtered out
        if u not in node_ids or v not in node_ids:
            continue

        etype = attrs.get("edge_type", "default")
        classes = etype
        if etype == "shared_keywords":
            classes += " shared"
        elif etype == "viral_opportunity":
            classes += " viral-edge"

        elements.append({
            "data": {
                "source": u,
                "target": v,
                "weight": attrs.get("weight", 1),
                "edge_type": etype,
            },
            "classes": classes,
        })

    return elements


# ══════════════════════════════════════════════════════════════════════════════
#  Layout helpers
# ══════════════════════════════════════════════════════════════════════════════


def suggested_layout(node_count: int) -> dict[str, Any]:
    """Pick an appropriate Cytoscape layout for the node count."""
    if node_count < 30:
        return {"name": "cose", "animate": True, "animationDuration": 800,
                "nodeRepulsion": 8000, "idealEdgeLength": 120}
    if node_count < 150:
        return {"name": "cose", "animate": True, "animationDuration": 600,
                "nodeRepulsion": 12000, "idealEdgeLength": 100,
                "numIter": 200}
    # Large graphs — fast force-directed
    return {"name": "cose", "animate": False, "nodeRepulsion": 16000,
            "idealEdgeLength": 80, "numIter": 100}
