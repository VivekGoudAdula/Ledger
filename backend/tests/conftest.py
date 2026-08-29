"""Pytest Test Configuration & Shared Fixtures.

Provides in-memory async SQLite engine, test DB session, and AsyncClient for API testing.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.storage.database import Base, get_db_session
from app.main import app


TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def test_engine():
    """Create in-memory async SQLite engine for testing."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def test_session_factory(test_engine):
    """Provide session factory bound to in-memory test engine."""
    return async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


@pytest_asyncio.fixture
async def db_session(test_session_factory):
    """Provide AsyncSession bound to in-memory test engine."""
    async with test_session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def async_client(test_session_factory):
    """Provide httpx AsyncClient for FastAPI endpoint integration testing."""
    async def _override_get_db_session():
        async with test_session_factory() as session:
            yield session
            await session.commit()

    app.dependency_overrides[get_db_session] = _override_get_db_session
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
        
    app.dependency_overrides.clear()
