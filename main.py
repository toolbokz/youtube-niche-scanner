#!/usr/bin/env python3
"""Growth Strategist — YouTube Niche Discovery Platform.

Usage:
    python main.py analyze "ai tools" "passive income" "health tips"
    python main.py analyze "crypto" "investing" --top-n 15 --videos 10
    python main.py serve
    python main.py cache-stats
    python main.py health
"""

from app.cli import cli

if __name__ == "__main__":
    cli()
