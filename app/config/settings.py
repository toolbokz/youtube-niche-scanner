"""Application configuration management.

Configuration priority (highest → lowest):
    1. Environment variables (GS_* prefix)
    2. .env file (auto-loaded via python-dotenv)
    3. YAML config file (config.yaml)
    4. Built-in defaults
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover – graceful fallback
    def load_dotenv(*_a: Any, **_kw: Any) -> None:  # type: ignore[misc]
        pass


# ── Config Models ──────────────────────────────────────────────────────────────

class CacheConfig(BaseModel):
    enabled: bool = True
    directory: str = "data/cache"
    ttl_hours: int = 24
    max_size_mb: int = 500


class DatabaseConfig(BaseModel):
    url: str = "sqlite:///data/db/growth_strategist.db"
    echo: bool = False
    pool_size: int = 5


class ApiConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 4
    cors_origins: list[str] = Field(default_factory=lambda: ["*"])


class ConnectorConfig(BaseModel):
    enabled: bool = True
    rate_limit_per_second: float = 1.0
    timeout_seconds: int = 15
    max_retries: int = 3
    cache_ttl_hours: int = 12
    api_key: str = ""


class ConnectorsConfig(BaseModel):
    youtube_autocomplete: ConnectorConfig = ConnectorConfig(
        rate_limit_per_second=2, timeout_seconds=10, cache_ttl_hours=12
    )
    youtube_search: ConnectorConfig = ConnectorConfig(
        rate_limit_per_second=1, timeout_seconds=15, cache_ttl_hours=6
    )
    google_trends: ConnectorConfig = ConnectorConfig(
        rate_limit_per_second=1, timeout_seconds=20, cache_ttl_hours=12
    )
    reddit: ConnectorConfig = ConnectorConfig(
        rate_limit_per_second=1, timeout_seconds=15, cache_ttl_hours=6
    )
    youtube_data_api: ConnectorConfig = ConnectorConfig(
        enabled=False, rate_limit_per_second=5, timeout_seconds=10, cache_ttl_hours=24
    )


class AnalysisConfig(BaseModel):
    max_keywords_per_batch: int = 500
    top_niches_count: int = 20
    videos_per_niche: int = 10
    competition_sample_size: int = 20


class RankingWeights(BaseModel):
    demand: float = 0.25
    competition: float = 0.20
    trend_momentum: float = 0.15
    virality: float = 0.15
    ctr_potential: float = 0.10
    viral_opportunity: float = 0.10
    topic_velocity: float = 0.05


class RankingConfig(BaseModel):
    weights: RankingWeights = RankingWeights()


class ReportsConfig(BaseModel):
    output_directory: str = "data/reports"
    format: list[str] = Field(default_factory=lambda: ["json", "markdown"])


class VertexAIConfig(BaseModel):
    """Google Vertex AI / Gemini configuration."""
    enabled: bool = False
    project: str = ""
    region: str = "us-central1"
    client_id: str = ""
    cache_ttl_hours: int = 24


class AppConfig(BaseModel):
    name: str = "Growth Strategist"
    version: str = "1.0.0"
    environment: str = "development"
    debug: bool = False
    log_level: str = "INFO"


class Settings(BaseModel):
    """Root application settings."""

    app: AppConfig = AppConfig()
    database: DatabaseConfig = DatabaseConfig()
    cache: CacheConfig = CacheConfig()
    api: ApiConfig = ApiConfig()
    connectors: ConnectorsConfig = ConnectorsConfig()
    analysis: AnalysisConfig = AnalysisConfig()
    ranking: RankingConfig = RankingConfig()
    reports: ReportsConfig = ReportsConfig()
    vertex_ai: VertexAIConfig = VertexAIConfig()

    @property
    def is_production(self) -> bool:
        return self.app.environment == "production"


# ── Env-var → nested-config mapping ───────────────────────────────────────────
# Each entry: (ENV_VAR_NAME, (nested, dict, path), cast_type)

_ENV_MAP: list[tuple[str, tuple[str, ...], type]] = [
    # App
    ("GS_ENVIRONMENT",                   ("app", "environment"),                               str),
    ("GS_DEBUG",                         ("app", "debug"),                                     bool),
    ("GS_LOG_LEVEL",                     ("app", "log_level"),                                 str),
    # Database
    ("GS_DATABASE_URL",                  ("database", "url"),                                  str),
    ("GS_DATABASE_ECHO",                 ("database", "echo"),                                 bool),
    ("GS_DATABASE_POOL_SIZE",            ("database", "pool_size"),                            int),
    # API
    ("GS_API_HOST",                      ("api", "host"),                                      str),
    ("GS_API_PORT",                      ("api", "port"),                                      int),
    ("GS_API_WORKERS",                   ("api", "workers"),                                   int),
    ("GS_API_CORS_ORIGINS",             ("api", "cors_origins"),                              str),  # special: CSV
    # Cache
    ("GS_CACHE_ENABLED",                ("cache", "enabled"),                                  bool),
    ("GS_CACHE_DIRECTORY",              ("cache", "directory"),                                str),
    ("GS_CACHE_TTL_HOURS",             ("cache", "ttl_hours"),                                int),
    ("GS_CACHE_MAX_SIZE_MB",           ("cache", "max_size_mb"),                              int),
    # YouTube Data API connector
    ("GS_YOUTUBE_DATA_API_ENABLED",     ("connectors", "youtube_data_api", "enabled"),         bool),
    ("GS_YOUTUBE_DATA_API_KEY",         ("connectors", "youtube_data_api", "api_key"),         str),
    # Connector rate limits – YouTube Autocomplete
    ("GS_YOUTUBE_AUTOCOMPLETE_RATE_LIMIT",       ("connectors", "youtube_autocomplete", "rate_limit_per_second"), float),
    ("GS_YOUTUBE_AUTOCOMPLETE_TIMEOUT",          ("connectors", "youtube_autocomplete", "timeout_seconds"),       int),
    ("GS_YOUTUBE_AUTOCOMPLETE_CACHE_TTL_HOURS",  ("connectors", "youtube_autocomplete", "cache_ttl_hours"),      int),
    # Connector rate limits – YouTube Search
    ("GS_YOUTUBE_SEARCH_RATE_LIMIT",             ("connectors", "youtube_search", "rate_limit_per_second"),       float),
    ("GS_YOUTUBE_SEARCH_TIMEOUT",                ("connectors", "youtube_search", "timeout_seconds"),             int),
    ("GS_YOUTUBE_SEARCH_CACHE_TTL_HOURS",        ("connectors", "youtube_search", "cache_ttl_hours"),             int),
    # Connector rate limits – Google Trends
    ("GS_GOOGLE_TRENDS_RATE_LIMIT",              ("connectors", "google_trends", "rate_limit_per_second"),        float),
    ("GS_GOOGLE_TRENDS_TIMEOUT",                 ("connectors", "google_trends", "timeout_seconds"),              int),
    ("GS_GOOGLE_TRENDS_CACHE_TTL_HOURS",         ("connectors", "google_trends", "cache_ttl_hours"),              int),
    # Connector rate limits – Reddit
    ("GS_REDDIT_RATE_LIMIT",                     ("connectors", "reddit", "rate_limit_per_second"),               float),
    ("GS_REDDIT_TIMEOUT",                        ("connectors", "reddit", "timeout_seconds"),                     int),
    ("GS_REDDIT_CACHE_TTL_HOURS",                ("connectors", "reddit", "cache_ttl_hours"),                     int),
    # Connector rate limits – YouTube Data API
    ("GS_YOUTUBE_DATA_API_RATE_LIMIT",           ("connectors", "youtube_data_api", "rate_limit_per_second"),     float),
    ("GS_YOUTUBE_DATA_API_TIMEOUT",              ("connectors", "youtube_data_api", "timeout_seconds"),           int),
    ("GS_YOUTUBE_DATA_API_CACHE_TTL_HOURS",      ("connectors", "youtube_data_api", "cache_ttl_hours"),           int),
    # Analysis
    ("GS_MAX_KEYWORDS_PER_BATCH",    ("analysis", "max_keywords_per_batch"),      int),
    ("GS_TOP_NICHES_COUNT",          ("analysis", "top_niches_count"),             int),
    ("GS_VIDEOS_PER_NICHE",          ("analysis", "videos_per_niche"),             int),
    ("GS_COMPETITION_SAMPLE_SIZE",   ("analysis", "competition_sample_size"),      int),
    # Ranking weights
    ("GS_WEIGHT_DEMAND",             ("ranking", "weights", "demand"),             float),
    ("GS_WEIGHT_COMPETITION",        ("ranking", "weights", "competition"),        float),
    ("GS_WEIGHT_TREND_MOMENTUM",     ("ranking", "weights", "trend_momentum"),     float),
    ("GS_WEIGHT_VIRALITY",           ("ranking", "weights", "virality"),           float),
    ("GS_WEIGHT_CTR_POTENTIAL",      ("ranking", "weights", "ctr_potential"),      float),
    ("GS_WEIGHT_VIRAL_OPPORTUNITY",  ("ranking", "weights", "viral_opportunity"),  float),
    ("GS_WEIGHT_TOPIC_VELOCITY",     ("ranking", "weights", "topic_velocity"),     float),
    # Reports
    ("GS_REPORTS_OUTPUT_DIRECTORY",  ("reports", "output_directory"),              str),
    ("GS_REPORTS_FORMAT",            ("reports", "format"),                        str),  # special: CSV
    # Vertex AI (Gemini)
    ("GS_VERTEX_AI_ENABLED",         ("vertex_ai", "enabled"),                    bool),
    ("GS_VERTEX_AI_PROJECT",         ("vertex_ai", "project"),                    str),
    ("GS_VERTEX_AI_REGION",          ("vertex_ai", "region"),                     str),
    ("GS_VERTEX_CLIENT_ID",          ("vertex_ai", "client_id"),                  str),
    ("GS_VERTEX_AI_CACHE_TTL_HOURS", ("vertex_ai", "cache_ttl_hours"),            int),
]


def _cast_env(value: str, cast: type) -> Any:
    """Cast a raw env-var string to the target type."""
    if cast is bool:
        return value.lower() in ("true", "1", "yes")
    return cast(value)


def _apply_env_overrides(cfg: dict[str, Any]) -> None:
    """Overlay GS_* environment variables onto the config dict."""
    for env_key, path, cast in _ENV_MAP:
        raw = os.environ.get(env_key)
        if raw is None:
            continue

        # CSV list fields
        if env_key in ("GS_API_CORS_ORIGINS", "GS_REPORTS_FORMAT"):
            typed_val: Any = [s.strip() for s in raw.split(",") if s.strip()]
        else:
            typed_val = _cast_env(raw, cast)

        # Walk into nested dict, creating intermediate dicts as needed
        d = cfg
        for key in path[:-1]:
            d = d.setdefault(key, {})
        d[path[-1]] = typed_val

    # GS_CONNECTOR_MAX_RETRIES → applies to *all* connectors
    max_retries = os.environ.get("GS_CONNECTOR_MAX_RETRIES")
    if max_retries is not None:
        connectors = cfg.setdefault("connectors", {})
        for name in ("youtube_autocomplete", "youtube_search", "google_trends",
                      "reddit", "youtube_data_api"):
            connectors.setdefault(name, {})["max_retries"] = int(max_retries)


# ── Public API ─────────────────────────────────────────────────────────────────

_settings: Settings | None = None


def load_settings(config_path: str | Path | None = None) -> Settings:
    """Load settings with priority: env vars > .env > YAML > defaults.

    Steps:
        1. Load .env into ``os.environ`` (existing vars are NOT overwritten).
        2. Determine YAML path from ``GS_CONFIG_PATH`` env var (default: config.yaml).
        3. Parse YAML into a dict.
        4. Overlay every ``GS_*`` env var found in ``os.environ`` onto that dict.
        5. Construct and cache a ``Settings`` model.
    """
    global _settings

    if _settings is not None:
        return _settings

    # 1. .env → os.environ (override=False keeps real env vars on top)
    env_path = Path(".env")
    if env_path.exists():
        load_dotenv(env_path, override=False)

    # 2. Config file path
    if config_path is None:
        config_path = os.environ.get("GS_CONFIG_PATH", "config.yaml")
    config_path = Path(config_path)

    # 3. YAML base
    if config_path.exists():
        with open(config_path, "r") as f:
            raw: dict[str, Any] = yaml.safe_load(f) or {}
    else:
        raw = {}

    # 4. Env-var overrides (highest priority)
    _apply_env_overrides(raw)

    # 5. Build settings
    _settings = Settings(**raw)
    return _settings


def get_settings() -> Settings:
    """Retrieve current settings (loads defaults if not initialized)."""
    global _settings
    if _settings is None:
        return load_settings()
    return _settings


def reset_settings() -> None:
    """Reset cached settings (useful for testing)."""
    global _settings
    _settings = None
