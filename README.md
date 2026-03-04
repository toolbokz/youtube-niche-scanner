# Growth Strategist

**YouTube Niche Discovery & Faceless Video Strategy Platform**

A production-grade Python system that discovers highly profitable YouTube niches and generates complete faceless video strategies. Built for local execution with minimal API cost.

---

## Features

- **Trend Discovery** — Detects rising topics using Google Trends, Reddit signals, YouTube autocomplete velocity, and upload frequency analysis
- **Keyword Expansion** — Expands seed keywords using YouTube autocomplete, Google autocomplete, Bing, and question-based expansion
- **Niche Clustering** — Groups keywords into semantic niches using TF-IDF vectorization and hierarchical clustering
- **Competition Analysis** — Evaluates niche saturation: avg views, subscriber counts, content density, production quality proxies
- **Virality Prediction** — Heuristic scoring for curiosity gap, emotional triggers, shock factor, novelty, and relatability
- **CTR Prediction** — Estimates click-through potential from power words, curiosity triggers, numbers, pattern interrupts
- **Faceless Viability** — Scores each niche for stock footage, B-roll voiceover, animated explainer, screen recording, slideshow, and data visualization formats
- **Niche Ranking** — Weighted scoring algorithm combining demand, competition, trend momentum, virality, CTR, and faceless viability
- **Video Strategy** — Generates channel concepts, audience personas, posting cadence, RPM estimates, and time-to-monetization projections
- **Video Blueprints** — Complete production plans including titles, thumbnails, script structures, production plans, and low-cost methods
- **SEO Descriptions** — Keyword-optimized descriptions with chapters, CTAs, and affiliate positioning
- **Monetization Strategy** — Affiliate products, sponsorship categories, digital products, lead magnets, and expansion roadmaps

---

## Architecture

```
app/
├── core/           # Models, cache, logging, pipeline orchestrator
├── config/         # YAML-based settings with Pydantic validation
├── database/       # SQLAlchemy async ORM (SQLite default)
├── connectors/     # Data collection: YouTube, Google Trends, Reddit
├── trend_discovery/       # Trend momentum scoring
├── keyword_expansion/     # Multi-source keyword expansion
├── niche_clustering/      # TF-IDF + hierarchical clustering
├── competition_analysis/  # Competition saturation scoring
├── virality_prediction/   # Viral potential heuristics
├── ctr_prediction/        # CTR potential scoring
├── ranking_engine/        # Weighted niche ranking (7-signal formula)
├── faceless_viability/    # Faceless format suitability
├── video_strategy/        # Channel concepts, video ideas, blueprints
├── thumbnail_strategy/    # Thumbnail concept generation
├── title_generation/      # CTR-optimized title formulas
├── description_generation/ # SEO description generation
├── monetization_engine/   # Monetization strategy generation
├── report_generation/     # JSON + Markdown report output
├── api/            # FastAPI endpoints
├── ui/             # Interactive Discovery Map (Plotly Dash)
│   ├── app.py          # Main Dash application, layout & callbacks
│   ├── api_client.py   # HTTP client for FastAPI backend
│   ├── graph_engine.py  # NetworkX → Cytoscape graph conversion
│   ├── styles.py        # Dark analytics theme & Cytoscape stylesheet
│   ├── panels.py        # Side-panel component builders (charts, details)
│   └── export.py        # JSON / Markdown / PNG export utilities
└── cli.py          # Click-based CLI interface
```

---

## Quick Start

### 1. Setup

```bash
# Clone and enter the directory
cd growth-strategist

# Run setup script (creates venv, installs deps)
bash scripts/setup.sh

# Or manually:
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Run Analysis

```bash
# Analyze niches from seed keywords
python main.py analyze "ai tools" "passive income" "health tips"

# With options
python main.py analyze "crypto" "investing" --top-n 15 --videos 10

# Verbose mode
python main.py -v analyze "python tutorial" "web development"
```

### 3. Start API Server

```bash
python main.py serve

# Access docs at http://localhost:8000/docs
```

### 4. Launch Interactive Discovery Map

```bash
# Start the backend first
python main.py serve

# In another terminal — launch the Dash UI
python -m app.ui.app

# Open http://localhost:8050
```

The Discovery Map provides:
- **Interactive network visualization** — Cytoscape.js topic graph with niche, keyword, viral, and trend nodes
- **Layer toggles** — Show/hide keywords, viral opportunities, and trend signals
- **Node analysis** — Click any node for deep-dive panels (radar charts, velocity sparklines, thumbnail donuts)
- **Discovery controls** — Seed keyword analysis, auto-discover, and deep-discover modes
- **Export** — Download reports as JSON, Markdown, or PNG screenshot

### 5. Other Commands

```bash
# Check system health
python main.py health

# View cache statistics
python main.py cache-stats

# Clear cached data
python main.py clear-cache
```

---

## Configuration

Edit `config.yaml` to customize:

```yaml
connectors:
  youtube_data_api:
    enabled: false          # Set to true + add API key for enriched data
    api_key: "YOUR_KEY"

analysis:
  max_keywords_per_batch: 500
  top_niches_count: 20
  videos_per_niche: 10

ranking:
  weights:
    demand: 0.30
    competition: 0.25
    trend_momentum: 0.15
    virality: 0.15
    ctr_potential: 0.10
    faceless_viability: 0.05
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/analyze` | Full pipeline analysis |
| `POST` | `/discover` | Automatic niche discovery (deep mode optional) |
| `GET` | `/niches?keywords=ai,crypto&top_n=10` | Quick niche discovery |
| `GET` | `/cache/stats` | Cache statistics |

### POST /analyze

```json
{
  "seed_keywords": ["ai tools", "passive income"],
  "top_n": 10,
  "videos_per_niche": 10
}
```

---

## Data Sources

| Source | Cost | Usage |
|--------|------|-------|
| YouTube Autocomplete | Free | Keyword expansion, demand proxy |
| YouTube Search Scraping | Free | Competition analysis |
| Google Trends (pytrends) | Free | Trend momentum |
| Reddit JSON API | Free | Trend signals, spike detection |
| Google Autocomplete | Free | Keyword expansion |
| Bing Autocomplete | Free | Keyword expansion |
| YouTube Data API v3 | Optional | Enriched video/channel data |

---

## Niche Ranking Formula

```
Niche Score =
  0.25 × Demand Score
+ 0.20 × (100 − Competition Score)
+ 0.15 × Trend Momentum
+ 0.15 × Virality Score
+ 0.10 × CTR Potential
+ 0.10 × Viral Opportunity Score
+ 0.05 × Topic Velocity Score
```

All scores normalized to 0–100.

---

## Output

Reports are saved to `data/reports/` in both JSON and Markdown format.

### JSON Structure

```json
{
  "generated_at": "2026-03-04T12:00:00",
  "seed_keywords": ["ai tools", "passive income"],
  "top_niches": [
    {
      "niche": "ai automation tools",
      "overall_score": 82.5,
      "rank": 1,
      "demand_score": 90.0,
      "competition_score": 35.0,
      "trend_momentum": 85.0,
      "virality_score": 72.0,
      "ctr_potential": 78.0,
      "faceless_viability": 88.0
    }
  ],
  "channel_concepts": [...],
  "video_blueprints": {
    "ai automation tools": [
      {
        "video_idea": {...},
        "title_formulas": [...],
        "thumbnail": {...},
        "script_structure": {...},
        "production_plan": {...},
        "seo_description": {...},
        "monetization": {...}
      }
    ]
  }
}
```

---

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=app --cov-report=html

# Run specific test module
pytest tests/test_engines.py -v
```

---

## Docker

```bash
# Build
docker build -t growth-strategist .

# Run CLI
docker run --rm growth-strategist python main.py analyze "ai tools"

# Run API server
docker run -p 8000:8000 growth-strategist
```

---

## Tech Stack

- **Python 3.11+** — Core language
- **FastAPI** — API layer
- **Plotly Dash** — Interactive Discovery Map UI
- **dash-cytoscape** — Network graph visualization (Cytoscape.js)
- **NetworkX** — Graph construction and analysis
- **Plotly** — Radar charts, bar charts, donuts
- **dash-bootstrap-components** — Dark theme layout
- **SQLAlchemy** — Async ORM with SQLite/PostgreSQL
- **httpx** — HTTP client (backend + UI API calls)
- **scikit-learn** — TF-IDF vectorization + clustering
- **Pydantic** — Data validation and settings
- **Click + Rich** — CLI interface
- **structlog** — Structured logging
- **pytrends** — Google Trends data
- **BeautifulSoup4** — HTML parsing

---

## License

MIT
