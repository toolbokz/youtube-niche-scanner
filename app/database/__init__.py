"""Database package."""
from app.database.models import (
    Base,
    KeywordRecord,
    NicheRecord,
    VideoIdeaRecord,
    SearchResultRecord,
    TrendRecord,
    AnalysisRun,
    AIInsightRecord,
    VideoFactoryJobRecord,
    init_db,
    get_session,
    close_db,
)

__all__ = [
    "Base",
    "KeywordRecord",
    "NicheRecord",
    "VideoIdeaRecord",
    "SearchResultRecord",
    "TrendRecord",
    "AnalysisRun",
    "AIInsightRecord",
    "VideoFactoryJobRecord",
    "init_db",
    "get_session",
    "close_db",
]
