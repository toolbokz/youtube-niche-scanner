"""Tests for database models and initialization."""
from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

import pytest

from app.database.models import (
    Base,
    KeywordRecord,
    NicheRecord,
    AnalysisRun,
    init_db,
    get_session,
    close_db,
)


@pytest.fixture
async def db_session():
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        await init_db(f"sqlite:///{db_path}")
        async for session in get_session():
            yield session
        await close_db()


@pytest.mark.asyncio
async def test_init_db() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        await init_db(f"sqlite:///{db_path}")
        assert db_path.exists()
        await close_db()


@pytest.mark.asyncio
async def test_keyword_record(db_session) -> None:
    session = db_session
    record = KeywordRecord(keyword="python tutorial", source="seed")
    session.add(record)
    await session.commit()
    await session.refresh(record)
    assert record.id is not None
    assert record.keyword == "python tutorial"


@pytest.mark.asyncio
async def test_niche_record(db_session) -> None:
    session = db_session
    record = NicheRecord(
        name="python programming",
        keywords=["python", "programming"],
        overall_score=75.0,
    )
    session.add(record)
    await session.commit()
    await session.refresh(record)
    assert record.id is not None
    assert record.overall_score == 75.0
