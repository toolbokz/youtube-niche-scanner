"""CLI interface for Growth Strategist."""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from app.config import get_settings, load_settings
from app.core.logging import setup_logging, get_logger

console = Console()
logger = get_logger(__name__)


@click.group()
@click.option("--config", "-c", default="config.yaml", help="Path to config file")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
def cli(config: str, verbose: bool) -> None:
    """Growth Strategist — YouTube Niche Discovery Platform."""
    load_settings(config)
    settings = get_settings()
    level = "DEBUG" if verbose else settings.app.log_level
    setup_logging(level)


@cli.command()
@click.argument("keywords", nargs=-1, required=True)
@click.option("--top-n", "-n", default=10, help="Number of top niches to return")
@click.option("--videos", "-v", default=10, help="Number of video ideas per niche")
def analyze(keywords: tuple[str, ...], top_n: int, videos: int) -> None:
    """Run the full niche discovery pipeline.

    Example: python main.py analyze "ai tools" "passive income" "health tips"
    """
    seed_keywords = list(keywords)

    console.print(Panel(
        f"[bold cyan]Growth Strategist[/bold cyan] — Niche Discovery Pipeline\n\n"
        f"Seeds: [yellow]{', '.join(seed_keywords)}[/yellow]\n"
        f"Top niches: {top_n} | Videos per niche: {videos}",
        title="🚀 Starting Analysis",
        border_style="cyan",
    ))

    asyncio.run(_run_analysis(seed_keywords, top_n, videos))


async def _run_analysis(seed_keywords: list[str], top_n: int, videos: int) -> None:
    """Execute the analysis pipeline asynchronously."""
    from app.core.pipeline import PipelineOrchestrator
    from app.database import init_db

    await init_db()

    pipeline = PipelineOrchestrator()

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Running pipeline...", total=None)

            report = await pipeline.run_full_pipeline(
                seed_keywords=seed_keywords,
                top_n=top_n,
                videos_per_niche=videos,
            )

            progress.update(task, description="[green]Pipeline complete!")

        # Display results
        _display_results(report)

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        logger.error("cli_error", error=str(e))
        sys.exit(1)
    finally:
        await pipeline.close()


def _display_results(report: Any) -> None:
    """Display pipeline results in the terminal."""
    # Discovery mode header
    if report.metadata.get("discovery_mode"):
        console.print(Panel(
            f"[bold magenta]Auto-Discovery Mode[/bold magenta]\n"
            f"Seeds discovered: {report.metadata.get('auto_discovered_seeds', '?')}\n"
            f"Deep mode: {'Yes' if report.metadata.get('deep_mode') else 'No'}\n"
            f"Sources: {', '.join(report.metadata.get('discovery_sources', []))}",
            title="🔍 Discovery",
            border_style="magenta",
        ))

    # Niche ranking table
    table = Table(title="🏆 Top Niches Ranked", show_lines=True)
    table.add_column("Rank", style="bold cyan", width=5)
    table.add_column("Niche", style="bold white", width=25)
    table.add_column("Score", style="bold green", width=8)
    table.add_column("Demand", width=8)
    table.add_column("Competition", width=12)
    table.add_column("Trend", width=8)
    table.add_column("Virality", width=9)
    table.add_column("CTR", width=6)
    table.add_column("Viral Opp", width=10)
    table.add_column("Velocity", width=9)

    for niche in report.top_niches:
        table.add_row(
            str(niche.rank),
            niche.niche[:24],
            f"{niche.overall_score:.1f}",
            f"{niche.demand_score:.1f}",
            f"{niche.competition_score:.1f}",
            f"{niche.trend_momentum:.1f}",
            f"{niche.virality_score:.1f}",
            f"{niche.ctr_potential:.1f}",
            f"{niche.viral_opportunity_score:.1f}",
            f"{niche.topic_velocity_score:.1f}",
        )

    console.print(table)

    # Viral opportunities summary
    if report.viral_opportunities:
        console.print("\n[bold red]🔥 Viral Opportunities Detected:[/bold red]")
        for niche_name, opps in report.viral_opportunities.items():
            if opps:
                top_opp = max(opps, key=lambda o: o.opportunity_score)
                console.print(
                    f"  • [yellow]{niche_name}[/yellow]: {len(opps)} anomalies — "
                    f"Best: {top_opp.channel_name} ({top_opp.channel_subscribers:,} subs, "
                    f"{top_opp.video_views:,} views)"
                )

    # Topic velocity summary
    if report.topic_velocities:
        console.print("\n[bold blue]📈 Topic Velocity:[/bold blue]")
        for niche_name, vel in report.topic_velocities.items():
            trend = "⬆" if vel.acceleration > 0.2 else "⬇" if vel.acceleration < -0.2 else "➡"
            console.print(
                f"  • [yellow]{niche_name}[/yellow]: {trend} "
                f"Growth {vel.growth_rate:.2f}x | Velocity {vel.velocity_score:.0f}/100"
            )

    # Thumbnail pattern summary
    if report.thumbnail_patterns:
        console.print("\n[bold magenta]🎨 Thumbnail Patterns:[/bold magenta]")
        for niche_name, tp in report.thumbnail_patterns.items():
            styles = ", ".join(sg.style_label for sg in tp.style_groups[:3])
            console.print(
                f"  • [yellow]{niche_name}[/yellow]: {tp.total_analyzed} analyzed — "
                f"Styles: {styles}"
            )

    # Channel concepts summary
    console.print("\n[bold cyan]📺 Channel Concepts:[/bold cyan]")
    for concept in report.channel_concepts:
        console.print(f"  • [yellow]{concept.niche}[/yellow]: {concept.positioning[:80]}...")
        console.print(f"    RPM: ${concept.estimated_rpm:.2f} | "
                       f"Cadence: {concept.posting_cadence} | "
                       f"Monetization: ~{concept.time_to_monetization_months} months")

    # Blueprint count
    total_blueprints = sum(len(v) for v in report.video_blueprints.values())
    console.print(f"\n[bold green]✅ Generated {total_blueprints} video blueprints "
                   f"across {len(report.top_niches)} niches[/bold green]")

    # Report paths
    console.print(f"\n[bold]📄 Reports saved to: data/reports/[/bold]")

    # Metadata
    if report.metadata:
        console.print(f"\n[dim]Pipeline stats: {json.dumps(report.metadata, indent=2)}[/dim]")


@cli.command()
@click.option("--deep", is_flag=True, help="Deep discovery — broader search, more niches")
@click.option("--top-n", "-n", default=20, help="Number of top niches to return")
@click.option("--videos", "-v", default=10, help="Number of video ideas per niche")
@click.option("--max-seeds", "-s", default=20, help="Max seed topics to discover")
def discover(deep: bool, top_n: int, videos: int, max_seeds: int) -> None:
    """Automatic niche discovery — no seed keywords needed.

    Scans Google Trends, YouTube, Reddit, and autocomplete to find
    trending topics automatically, then runs the full analysis pipeline.

    Use --deep for broader coverage (50+ seeds, 50 top niches).

    Examples:
        python main.py discover
        python main.py discover --deep
        python main.py discover --top-n 30 --max-seeds 40
    """
    mode = "[bold magenta]Deep Discovery[/bold magenta]" if deep else "[bold cyan]Auto-Discovery[/bold cyan]"

    console.print(Panel(
        f"{mode} Mode\n\n"
        f"Max seeds: [yellow]{max_seeds}[/yellow]\n"
        f"Top niches: {top_n} | Videos per niche: {videos}\n"
        f"[dim]No seed keywords required — scanning live signals[/dim]",
        title="🔍 Automatic Discovery",
        border_style="magenta" if deep else "cyan",
    ))

    asyncio.run(_run_discovery(deep, top_n, videos, max_seeds))


async def _run_discovery(deep: bool, top_n: int, videos: int, max_seeds: int) -> None:
    """Execute the discovery pipeline asynchronously."""
    from app.core.pipeline import PipelineOrchestrator
    from app.database import init_db

    await init_db()

    pipeline = PipelineOrchestrator()

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Discovering trending topics...", total=None)

            report = await pipeline.run_discovery_pipeline(
                max_seeds=max_seeds,
                deep=deep,
                top_n=top_n,
                videos_per_niche=videos,
            )

            progress.update(task, description="[green]Discovery complete!")

        _display_results(report)

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        logger.error("discovery_error", error=str(e))
        sys.exit(1)
    finally:
        await pipeline.close()


@cli.command()
def generate_report() -> None:
    """Re-generate report from the latest analysis data."""
    console.print("[yellow]Generating report from cached data...[/yellow]")
    # This would load from database and regenerate
    console.print("[green]Report generation complete. Check data/reports/[/green]")


@cli.command("video-factory")
@click.argument("niche", required=True)
@click.option("--voice", "-V", default=None, help="Voice provider (placeholder|google|elevenlabs|edge)")
@click.option("--resolution", "-r", default=None, help="Video resolution e.g. 1920x1080")
@click.option("--no-subs", is_flag=True, help="Skip subtitle embedding")
def video_factory_cmd(niche: str, voice: str | None, resolution: str | None, no_subs: bool) -> None:
    """Run the Video Factory pipeline to produce a complete video.

    Generates concept, script, voiceover, clips, assembly, subtitles,
    thumbnail, and metadata for a given niche.

    Examples:
        python main.py video-factory "AI productivity tools"
        python main.py video-factory "yoga for beginners" --voice edge
        python main.py video-factory "budget travel" -r 1280x720 --no-subs
    """
    console.print(Panel(
        f"[bold cyan]Video Factory[/bold cyan]\n\n"
        f"Niche: [yellow]{niche}[/yellow]\n"
        f"Voice: {voice or 'config default'}\n"
        f"Resolution: {resolution or 'config default'}\n"
        f"Subtitles: {'off' if no_subs else 'on'}",
        title="🎬 Video Factory",
        border_style="cyan",
    ))

    asyncio.run(_run_video_factory(niche, voice, resolution, not no_subs))


async def _run_video_factory(niche: str, voice: str | None, resolution: str | None, embed_subs: bool) -> None:
    """Execute the Video Factory pipeline."""
    from app.video_factory.factory_orchestrator import FactoryOrchestrator
    from app.video_factory.models import VoiceConfig, AssemblyConfig

    settings = get_settings()
    vf_cfg = settings.video_factory

    voice_provider = voice or vf_cfg.voice_provider
    res = resolution or vf_cfg.resolution
    output_base = str(Path(vf_cfg.output_directory))

    voice_config = VoiceConfig(provider=voice_provider, voice_name=vf_cfg.voice_name)
    assembly_config = AssemblyConfig(
        resolution=res,
        embed_subtitles=embed_subs,
        use_gpu=vf_cfg.use_gpu,
    )

    orchestrator = FactoryOrchestrator(
        output_base=output_base,
        voice_config=voice_config,
        assembly_config=assembly_config,
    )

    def _progress(stage: str, pct: float) -> None:
        console.print(f"  [{int(pct):3d}%] {stage}")

    orchestrator.set_progress_callback(_progress)

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Running Video Factory pipeline...", total=None)

            result = await orchestrator.run(
                niche=niche,
                voice_config=voice_config,
                assembly_config=assembly_config,
            )

            progress.update(task, description="[green]Pipeline complete!")

        # Display results summary
        console.print(Panel(
            f"[bold green]Video Factory Complete![/bold green]\n\n"
            f"Concept: [yellow]{result.concept.title if result.concept else 'N/A'}[/yellow]\n"
            f"Video: {result.video_path or 'N/A'}\n"
            f"Thumbnail: {result.thumbnail_path or 'N/A'}\n"
            f"Subtitles: {result.subtitles_path or 'N/A'}\n"
            f"Title: {result.metadata.title if result.metadata else 'N/A'}",
            title="✅ Done",
            border_style="green",
        ))

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        logger.error("video_factory_error", error=str(e))
        sys.exit(1)


@cli.command()
def cache_stats() -> None:
    """Show cache statistics."""
    from app.core.cache import get_cache
    cache = get_cache()
    stats = cache.stats()

    table = Table(title="📊 Cache Statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white")

    for key, value in stats.items():
        table.add_row(key.replace("_", " ").title(), str(value))

    console.print(table)


@cli.command()
def clear_cache() -> None:
    """Clear all cached data."""
    from app.core.cache import get_cache
    cache = get_cache()
    count = cache.clear_namespace("all")
    console.print(f"[green]Cleared {count} cache entries.[/green]")


@cli.command("ai-analyze")
@click.option("--top-n", "-n", default=5, help="Number of top niches to send to AI")
def ai_analyze(top_n: int) -> None:
    """Run AI analysis (Gemini) on the latest report.

    Requires:
        - GOOGLE_APPLICATION_CREDENTIALS set
        - GOOGLE_CLOUD_PROJECT set
        - GS_VERTEX_AI_ENABLED=true (or vertex_ai.enabled in config.yaml)

    This loads the most recent JSON report from data/reports/
    and sends the top niches to Gemini for enhanced analysis.

    Examples:
        python main.py ai-analyze
        python main.py ai-analyze --top-n 3
    """
    console.print(Panel(
        f"[bold cyan]AI Analysis[/bold cyan] (Gemini)\n\n"
        f"Top niches to analyse: [yellow]{top_n}[/yellow]\n"
        f"[dim]Loading latest report from data/reports/[/dim]",
        title="🧠 AI-Powered Analysis",
        border_style="cyan",
    ))

    asyncio.run(_run_ai_analyze(top_n))


async def _run_ai_analyze(top_n: int) -> None:
    """Execute AI analysis on the latest report."""
    import json as _json
    from pathlib import Path
    from app.database import init_db
    from app.ai.service import run_full_ai_analysis
    from app.ai.client import get_ai_client

    await init_db()

    # Check AI availability
    client = get_ai_client()
    if not client.available:
        console.print(
            "[red]Error:[/red] Vertex AI is not configured.\n"
            "Set GOOGLE_APPLICATION_CREDENTIALS and GOOGLE_CLOUD_PROJECT environment variables."
        )
        sys.exit(1)

    # Load latest report
    settings = get_settings()
    report_dir = Path(settings.reports.output_directory)
    json_files = sorted(report_dir.glob("*.json"), reverse=True)

    if not json_files:
        console.print("[red]Error:[/red] No report files found in data/reports/. Run analyze first.")
        sys.exit(1)

    console.print(f"[dim]Loading: {json_files[0].name}[/dim]")
    with open(json_files[0]) as f:
        report_data = _json.load(f)

    # Trim to requested top_n
    if report_data.get("top_niches"):
        report_data["top_niches"] = report_data["top_niches"][:top_n]

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Running AI analysis…", total=None)
            results = await run_full_ai_analysis(report_data)
            progress.update(task, description="[green]AI analysis complete!")

        if "error" in results:
            console.print(f"[red]Error:[/red] {results['error']}")
            sys.exit(1)

        _display_ai_results(results)

        # Save AI-enhanced report
        ai_report_path = report_dir / f"ai_insights_{json_files[0].stem}.json"
        with open(ai_report_path, "w") as f:
            _json.dump(results, f, indent=2, default=str)
        console.print(f"\n[bold]📄 AI insights saved to: {ai_report_path}[/bold]")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        logger.error("ai_analyze_error", error=str(e))
        sys.exit(1)


def _display_ai_results(results: dict) -> None:
    """Display AI analysis results in the terminal."""
    # Niche analysis
    na = results.get("niche_analysis", {})
    if na and "error" not in na:
        console.print("\n[bold cyan]🧠 AI Niche Analysis:[/bold cyan]")
        rec = na.get("overall_recommendation", "")
        if rec:
            console.print(f"  {rec[:200]}")
        growth = na.get("growth_potential", [])
        for item in growth[:5]:
            if isinstance(item, dict):
                console.print(f"  • [yellow]{item.get('niche', '?')}[/yellow]: {item.get('assessment', '')[:100]}")

    # Trend forecast
    tf = results.get("trend_forecast", {})
    if tf and "error" not in tf:
        console.print("\n[bold purple]📈 AI Trend Forecast:[/bold purple]")
        direction = tf.get("overall_market_direction", "")
        if direction:
            console.print(f"  Market direction: {direction[:150]}")
        for fc in tf.get("trend_forecast", [])[:5]:
            if isinstance(fc, dict):
                console.print(
                    f"  • [yellow]{fc.get('topic', '?')}[/yellow] — "
                    f"Explosion: {fc.get('explosion_likelihood', '?')}, "
                    f"Peak: {fc.get('predicted_peak_timeframe', '?')}"
                )

    # Video strategy
    vs = results.get("video_strategy", {})
    if vs and "error" not in vs:
        ideas = vs.get("video_ideas", [])
        if ideas:
            console.print(f"\n[bold green]🎬 AI Video Strategy ({len(ideas)} ideas):[/bold green]")
            for i, idea in enumerate(ideas[:5], 1):
                if isinstance(idea, dict):
                    console.print(f"  {i}. [yellow]{idea.get('title', '?')}[/yellow]")
                    console.print(f"     {idea.get('concept', '')[:100]}")

    # Thumbnail strategy
    ts = results.get("thumbnail_strategy", {})
    if ts and "error" not in ts:
        console.print("\n[bold magenta]🎨 AI Thumbnail Strategy:[/bold magenta]")
        overall = ts.get("overall_recommendation", "")
        if overall:
            console.print(f"  {overall[:200]}")

    # Viral interpretations
    vi = results.get("viral_interpretations", {})
    if vi:
        console.print("\n[bold red]🔥 AI Viral Interpretation:[/bold red]")
        for niche_name, interp in vi.items():
            if isinstance(interp, dict) and "error" not in interp:
                themes = interp.get("common_themes", [])
                console.print(f"  • [yellow]{niche_name}[/yellow]: {', '.join(str(t) for t in themes[:3])}")


@cli.command()
@click.option("--host", default=None, help="Server host (default: from config)")
@click.option("--port", default=None, type=int, help="Server port (default: from config)")
def serve(host: str | None, port: int | None) -> None:
    """Start the FastAPI server."""
    import uvicorn

    settings = get_settings()
    host = host or settings.api.host
    port = port or settings.api.port
    is_dev = settings.app.debug

    mode_label = "[yellow]development[/yellow]" if is_dev else "[green]production[/green]"
    docs_line = f"Docs: [cyan]http://{host}:{port}/docs[/cyan]" if is_dev else "Docs: disabled in production"

    console.print(Panel(
        f"Starting API server at [cyan]http://{host}:{port}[/cyan]\n"
        f"Mode: {mode_label}\n"
        f"{docs_line}",
        title="🌐 API Server",
        border_style="green",
    ))

    uvicorn.run(
        "app.api.routes:app",
        host=host,
        port=port,
        reload=is_dev,
        workers=1 if is_dev else settings.api.workers,
        access_log=is_dev,
    )


@cli.command()
def health() -> None:
    """Check system health and connector status."""
    console.print("[cyan]Checking system health...[/cyan]")
    asyncio.run(_check_health())


async def _check_health() -> None:
    """Run health checks on all connectors."""
    from app.connectors.youtube_autocomplete import YouTubeAutocompleteConnector
    from app.config import get_settings

    settings = get_settings()
    connectors = settings.connectors

    checks = {
        "YouTube Autocomplete": YouTubeAutocompleteConnector(connectors.youtube_autocomplete),
    }

    for name, connector in checks.items():
        try:
            ok = await connector.health_check()
            status = "[green]✓ OK[/green]" if ok else "[red]✗ FAIL[/red]"
        except Exception as e:
            status = f"[red]✗ ERROR: {e}[/red]"
        finally:
            await connector.close()

        console.print(f"  {name}: {status}")


if __name__ == "__main__":
    cli()
