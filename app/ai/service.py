"""AI Service Layer — orchestrates Gemini calls with prompt templates and DB caching."""
from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timedelta
from typing import Any

from app.ai.client import get_ai_client
from app.ai.prompts.niche_analysis import niche_analysis_prompt, quick_niche_insight_prompt
from app.ai.prompts.strategy_generation import video_strategy_prompt, viral_opportunity_prompt
from app.ai.prompts.trend_interpretation import trend_forecast_prompt
from app.ai.prompts.thumbnail_analysis_ai import thumbnail_strategy_prompt
from app.core.logging import get_logger

logger = get_logger(__name__)

# Default cache TTL (hours)
_CACHE_TTL_HOURS = 24


# ── Cache helpers ──────────────────────────────────────────────────────────────

def _cache_key(analysis_type: str, niche: str, extra: str = "") -> str:
    """Deterministic cache key from analysis type + niche + optional extra."""
    raw = f"{analysis_type}:{niche}:{extra}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


async def _get_cached(analysis_type: str, niche: str, extra: str = "") -> dict[str, Any] | None:
    """Return cached AI insight if still fresh, else None."""
    try:
        from app.database.models import get_session, AIInsightRecord
        from sqlalchemy import select

        key = _cache_key(analysis_type, niche, extra)
        cutoff = datetime.utcnow() - timedelta(hours=_CACHE_TTL_HOURS)

        async for session in get_session():
            stmt = (
                select(AIInsightRecord)
                .where(
                    AIInsightRecord.cache_key == key,
                    AIInsightRecord.created_at >= cutoff,
                )
                .order_by(AIInsightRecord.created_at.desc())
                .limit(1)
            )
            result = await session.execute(stmt)
            row = result.scalar_one_or_none()
            if row:
                logger.debug("ai_cache_hit", type=analysis_type, niche=niche)
                return row.response  # type: ignore[return-value]
    except Exception as exc:
        logger.warning("ai_cache_read_error", error=str(exc))
    return None


async def _store_cache(
    analysis_type: str,
    niche: str,
    response: dict[str, Any],
    extra: str = "",
) -> None:
    """Persist an AI response in the cache table."""
    try:
        from app.database.models import get_session, AIInsightRecord

        key = _cache_key(analysis_type, niche, extra)

        async for session in get_session():
            record = AIInsightRecord(
                cache_key=key,
                niche=niche,
                analysis_type=analysis_type,
                response=response,
            )
            session.add(record)
            await session.commit()
            logger.debug("ai_cache_stored", type=analysis_type, niche=niche)
    except Exception as exc:
        logger.warning("ai_cache_write_error", error=str(exc))


# ── Public service methods ─────────────────────────────────────────────────────

async def analyze_niches(niches: list[dict[str, Any]]) -> dict[str, Any]:
    """Deep AI niche analysis (Gemini Pro).

    Parameters
    ----------
    niches : list[dict]
        Serialised NicheScore dicts (from top_niches in a report).

    Returns
    -------
    dict with keys: growth_potential list, content_strategy_insights list,
    audience_behavior_insights list, overall_recommendation str.
    """
    cache_niche = niches[0].get("niche", "mixed") if niches else "none"
    cached = await _get_cached("niche_analysis", cache_niche, str(len(niches)))
    if cached:
        return cached

    client = get_ai_client()
    if not client.available:
        return {"error": "Vertex AI not configured"}

    prompt = niche_analysis_prompt(niches)
    t0 = time.time()
    result = client.generate_json(prompt, use_pro=True)
    elapsed = round(time.time() - t0, 2)

    if result is None:
        return {"error": "AI generation failed"}

    result["_generation_time_s"] = elapsed
    await _store_cache("niche_analysis", cache_niche, result, str(len(niches)))
    logger.info("ai_niche_analysis_done", niches=len(niches), time_s=elapsed)
    return result


async def interpret_viral_opportunities(
    niche_name: str,
    anomalies: list[dict[str, Any]],
) -> dict[str, Any]:
    """Interpret viral anomaly data for a niche (Gemini Flash).

    Returns dict with common_themes, success_factors,
    suggested_video_topics, timing_insight.
    """
    cached = await _get_cached("viral_interpretation", niche_name)
    if cached:
        return cached

    client = get_ai_client()
    if not client.available:
        return {"error": "Vertex AI not configured"}

    prompt = viral_opportunity_prompt(niche_name, anomalies)
    t0 = time.time()
    result = client.generate_json(prompt, use_pro=False)  # Flash
    elapsed = round(time.time() - t0, 2)

    if result is None:
        return {"error": "AI generation failed"}

    result["_generation_time_s"] = elapsed
    await _store_cache("viral_interpretation", niche_name, result)
    logger.info("ai_viral_interpretation_done", niche=niche_name, time_s=elapsed)
    return result


async def generate_video_strategy(
    niche_name: str,
    keywords: list[str],
    trend_data: dict[str, Any] | None = None,
    competition_data: dict[str, Any] | None = None,
    count: int = 15,
) -> dict[str, Any]:
    """Generate AI-powered video strategy ideas (Gemini Flash).

    Returns dict with video_ideas list.
    """
    cached = await _get_cached("video_strategy", niche_name)
    if cached:
        return cached

    client = get_ai_client()
    if not client.available:
        return {"error": "Vertex AI not configured"}

    prompt = video_strategy_prompt(niche_name, keywords, trend_data, competition_data, count)
    t0 = time.time()
    result = client.generate_json(prompt, use_pro=False)
    elapsed = round(time.time() - t0, 2)

    if result is None:
        return {"error": "AI generation failed"}

    result["_generation_time_s"] = elapsed
    await _store_cache("video_strategy", niche_name, result)
    logger.info("ai_video_strategy_done", niche=niche_name, count=count, time_s=elapsed)
    return result


async def analyze_thumbnail_patterns(
    niche_name: str,
    pattern_data: dict[str, Any],
) -> dict[str, Any]:
    """AI-driven thumbnail style recommendations (Gemini Flash).

    Returns dict with color_strategy, text_overlay,
    emotion_style, layout_concepts, overall_recommendation.
    """
    cached = await _get_cached("thumbnail_strategy", niche_name)
    if cached:
        return cached

    client = get_ai_client()
    if not client.available:
        return {"error": "Vertex AI not configured"}

    prompt = thumbnail_strategy_prompt(niche_name, pattern_data)
    t0 = time.time()
    result = client.generate_json(prompt, use_pro=False)
    elapsed = round(time.time() - t0, 2)

    if result is None:
        return {"error": "AI generation failed"}

    result["_generation_time_s"] = elapsed
    await _store_cache("thumbnail_strategy", niche_name, result)
    logger.info("ai_thumbnail_analysis_done", niche=niche_name, time_s=elapsed)
    return result


async def forecast_trends(
    velocities: dict[str, dict[str, Any]],
    niches: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """AI trend forecast based on velocity data (Gemini Pro).

    Returns dict with trend_forecast list, emerging_subtopics list,
    overall_market_direction str.
    """
    cache_key_extra = ",".join(sorted(velocities.keys())[:5])
    cached = await _get_cached("trend_forecast", "global", cache_key_extra)
    if cached:
        return cached

    client = get_ai_client()
    if not client.available:
        return {"error": "Vertex AI not configured"}

    prompt = trend_forecast_prompt(velocities, niches)
    t0 = time.time()
    result = client.generate_json(prompt, use_pro=True)
    elapsed = round(time.time() - t0, 2)

    if result is None:
        return {"error": "AI generation failed"}

    result["_generation_time_s"] = elapsed
    await _store_cache("trend_forecast", "global", result, cache_key_extra)
    logger.info("ai_trend_forecast_done", topics=len(velocities), time_s=elapsed)
    return result


async def get_quick_niche_insight(niche_data: dict[str, Any]) -> dict[str, Any]:
    """Quick AI insight for the Discovery Map UI (Gemini Flash).

    Returns dict with quick_insight, recommended_video_topics,
    growth_opportunities, risk_factors.
    """
    niche_name = niche_data.get("niche", "unknown")
    cached = await _get_cached("quick_insight", niche_name)
    if cached:
        return cached

    client = get_ai_client()
    if not client.available:
        return {"error": "Vertex AI not configured"}

    prompt = quick_niche_insight_prompt(niche_data)
    t0 = time.time()
    result = client.generate_json(prompt, use_pro=False)  # Flash for speed
    elapsed = round(time.time() - t0, 2)

    if result is None:
        return {"error": "AI generation failed"}

    result["_generation_time_s"] = elapsed
    await _store_cache("quick_insight", niche_name, result)
    logger.debug("ai_quick_insight_done", niche=niche_name, time_s=elapsed)
    return result


async def run_full_ai_analysis(report_data: dict[str, Any]) -> dict[str, Any]:
    """Run all AI analyses on a completed report.

    This is the main entry point used by the pipeline and CLI.
    Only analyses top-ranked niches to control cost.

    Returns a dict keyed by analysis type containing all AI results.
    """
    results: dict[str, Any] = {}

    top_niches = report_data.get("top_niches", [])
    if not top_niches:
        return {"error": "No niches to analyse"}

    client = get_ai_client()
    if not client.available:
        return {"error": "Vertex AI not configured — set GOOGLE_APPLICATION_CREDENTIALS and GOOGLE_CLOUD_PROJECT"}

    # 1. Deep niche analysis (top 5 only → cost control)
    top5 = top_niches[:5]
    logger.info("ai_full_analysis_start", niches=len(top5))
    results["niche_analysis"] = await analyze_niches(
        [n if isinstance(n, dict) else n.model_dump(mode="json") for n in top5]
    )

    # 2. Viral opportunity interpretation (per niche, top 3)
    viral_opps = report_data.get("viral_opportunities", {})
    results["viral_interpretations"] = {}
    for niche_name in list(viral_opps.keys())[:3]:
        opps = viral_opps[niche_name]
        opp_dicts = [o if isinstance(o, dict) else o.model_dump(mode="json") for o in opps]
        results["viral_interpretations"][niche_name] = await interpret_viral_opportunities(
            niche_name, opp_dicts
        )

    # 3. Video strategy for top niche
    if top5:
        best = top5[0] if isinstance(top5[0], dict) else top5[0].model_dump(mode="json")
        results["video_strategy"] = await generate_video_strategy(
            best.get("niche", ""),
            best.get("keywords", []),
        )

    # 4. Thumbnail AI for top niche
    thumb_patterns = report_data.get("thumbnail_patterns", {})
    if thumb_patterns:
        first_niche = next(iter(thumb_patterns))
        tp = thumb_patterns[first_niche]
        tp_dict = tp if isinstance(tp, dict) else tp.model_dump(mode="json")
        results["thumbnail_strategy"] = await analyze_thumbnail_patterns(first_niche, tp_dict)

    # 5. Trend forecast
    velocities = report_data.get("topic_velocities", {})
    if velocities:
        vel_dicts = {
            k: (v if isinstance(v, dict) else v.model_dump(mode="json"))
            for k, v in velocities.items()
        }
        niche_dicts = [
            n if isinstance(n, dict) else n.model_dump(mode="json") for n in top5
        ]
        results["trend_forecast"] = await forecast_trends(vel_dicts, niche_dicts)

    logger.info("ai_full_analysis_complete", sections=list(results.keys()))
    return results
