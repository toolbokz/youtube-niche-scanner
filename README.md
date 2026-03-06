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
- **AI-First Creative Generation** — All content engines (titles, descriptions, thumbnails, scripts, video ideas, channel concepts, monetization copy) use Gemini Flash as the primary generation path with deterministic template fallbacks

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
├── ai/             # Vertex AI client, service layer, prompt templates
│   └── prompts/    # Structured Gemini prompt templates (10 files)
├── api/            # FastAPI endpoints
└── cli.py          # Click-based CLI interface

frontend/               # React + Next.js dashboard
├── src/
│   ├── app/            # Next.js App Router pages
│   ├── components/     # UI components, charts, layout
│   ├── hooks/          # TanStack Query hooks
│   ├── services/       # API client
│   ├── store/          # Zustand state management
│   ├── lib/            # Utilities
│   └── types/          # TypeScript type definitions
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

### 4. Launch Frontend Dashboard

```bash
# Make sure the backend is running first (step 3)

# In another terminal:
cd frontend
npm install
npm run dev

# Open http://localhost:3000
```

The dashboard provides:
- **Dashboard overview** — Key metrics, top niches, viral opportunities, trending topics
- **Niche Discovery** — Sortable table with search/filters, seed keyword analysis, auto & deep discovery modes
- **Niche Detail** — Radar charts, velocity graphs, competition insights, viral opportunity tables
- **Video Strategy** — Channel concepts, audience personas, video ideas with expandable blueprints
- **Thumbnail Insights** — Color analysis, face frequency, text usage, contrast patterns
- **Report Explorer** — Browse, search, view, and download saved reports (JSON + Markdown)
- **System** — Backend health, cache stats, configuration
- **Dark/Light theme** — Persistent theme toggle

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
| `GET` | `/ai/niche-insights?top_n=5` | AI-powered niche deep-dive |
| `GET` | `/ai/video-strategy?niche=...&count=15` | AI video strategy for a niche |
| `GET` | `/ai/trend-forecast` | AI trend forecast from velocity data |
| `GET` | `/reports` | List saved reports |
| `GET` | `/reports/{filename}` | Get a single report |
| `GET` | `/reports/{filename}/download?format=json` | Download report |
| `POST` | `/analyze/async` | Fire-and-forget pipeline (returns task_id) |
| `GET` | `/tasks/{task_id}` | Poll background task status |
| `GET` | `/dashboard-data` | Batch endpoint: health + cache + latest report |

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

## AI-First Creative Generation

All content generation engines follow an **AI-first + template fallback** architecture:

1. **AI path** — Engine calls `get_ai_client()` → builds a structured prompt → calls `client.generate_json()` via Gemini Flash → validates response keys → returns AI-generated content
2. **Fallback path** — If AI is unavailable, returns an error, or produces invalid output, the engine falls back to deterministic template-based generation (the original logic)

This ensures zero-downtime operation regardless of Vertex AI availability.

### Prompt Templates

| Template | File | Output |
|----------|------|--------|
| Title Generation | `app/ai/prompts/title_generation.py` | Curiosity-gap headline, SEO title, alternatives, formulas |
| Description Generation | `app/ai/prompts/description_generation.py` | Intro paragraph, keyword block, chapters, CTA, affiliate positioning |
| Thumbnail Concepts | `app/ai/prompts/thumbnail_generation.py` | Emotion trigger, contrast strategy, color palette, layout concept |
| Video Strategy | `app/ai/prompts/video_strategy_generation.py` | Video ideas with titles/angles, channel names/positioning/persona |
| Script Structure | `app/ai/prompts/script_generation.py` | Hook, retention interrupt, story arc, curiosity loop, payoff, CTA |

### Engines Using AI-First Pattern

| Engine | AI Prompt | Fallback |
|--------|-----------|----------|
| `TitleGenerationEngine` | `title_generation_prompt()` | 25 static title formulas |
| `DescriptionGenerationEngine` | `description_generation_prompt()` | Static intro/chapters/CTA templates |
| `ThumbnailStrategyGenerator` | `thumbnail_concept_prompt()` | 6-emotion visual mapping |
| `VideoStrategyEngine` | `video_ideas_prompt()`, `channel_concept_prompt()` | 15 angle templates, 5 name patterns |
| `BlueprintAssembler` | `script_structure_prompt()` | 6 static script section templates |
| `MonetizationEngine` | Inline Gemini prompt | 5 product + 4 lead magnet templates |

### Deterministic Engines (Not AI-ified)

Ranking, CTR prediction, virality scoring, competition analysis, faceless viability, topic velocity, niche clustering, trend discovery, compilation engine, and video factory timeline/assembler remain deterministic.

---

## Testing

```bash
# Run all tests (315 tests)
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

### Backend
- **Python 3.12+** — Core language
- **FastAPI** — API layer with GZip, orjson, CORS, Server-Timing
- **SQLAlchemy** — Async ORM with SQLite (aiosqlite) / PostgreSQL (asyncpg)
- **Pydantic v2** — Data validation and settings
- **httpx** — Async HTTP client
- **scikit-learn** — TF-IDF vectorization + hierarchical clustering
- **structlog** — Structured logging
- **orjson** — ~5× faster JSON serialisation
- **Redis** — Optional cache tier (LRU → Redis → disk)
- **Vertex AI / Gemini** — AI-powered analysis (Pro + Flash)
- **Pillow** — Thumbnail image analysis
- **pytrends** — Google Trends data
- **BeautifulSoup4** — HTML parsing
- **Click + Rich** — CLI interface

### Frontend
- **Next.js 14** — App Router with Server Components
- **React 18** — UI framework
- **TypeScript** — Type-safe frontend
- **TailwindCSS v3** — Utility-first styling
- **Recharts** — Charts (area, radar, pie/donut)
- **TanStack Query v5** — Server state management
- **Zustand v5** — Client state management

---

## License

MIT
