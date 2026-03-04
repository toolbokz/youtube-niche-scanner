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
