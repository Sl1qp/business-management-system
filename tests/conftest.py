import asyncio
import secrets
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.core.database import get_async_session
from app.main import app
from app.models.task import Task, TaskStatus
from app.models.team import Team, UserTeam
from app.models.user import User

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Создаем event loop для тестовой сессии"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def engine():
    """Создает движок БД для каждого теста"""

    engine = create_async_engine(
        SQLALCHEMY_DATABASE_URL,
        echo=False,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False}
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(engine) -> AsyncGenerator[AsyncSession, None]:
    """Создает сессию БД для каждого теста"""
    async_session = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@pytest_asyncio.fixture
async def async_client(db_session):
    """Создает асинхронный тестовый клиент FastAPI"""

    async def override_get_async_session():
        yield db_session

    app.dependency_overrides[get_async_session] = override_get_async_session

    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
def mock_db_session():
    """Мок сессии БД для unit-тестов"""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.refresh = AsyncMock()
    session.delete = AsyncMock()
    session.scalar_one_or_none = MagicMock()
    return session


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession):
    """Создает тестового пользователя в БД"""
    user = User(
        email="user@example.com",
        hashed_password="$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # "password"
        first_name="Test",
        last_name="User",
        role="user",
        is_active=True,
        is_superuser=False,
        is_verified=False
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_manager(db_session: AsyncSession):
    """Создает тестового менеджера в БД"""

    manager = User(
        email="manager@example.com",
        hashed_password="$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",
        first_name="Manager",
        last_name="User",
        role="manager",
        is_active=True,
        is_superuser=False,
        is_verified=False
    )
    db_session.add(manager)
    await db_session.commit()
    await db_session.refresh(manager)
    return manager


@pytest_asyncio.fixture
async def test_team(db_session: AsyncSession, test_manager):
    """Создает тестовую команду в БД"""

    team = Team(
        name="Test Team",
        description="Test team description",
        invite_code=secrets.token_urlsafe(12)
    )
    db_session.add(team)
    await db_session.flush()

    user_team = UserTeam(
        user_id=test_manager.id,
        team_id=team.id,
        role="admin"
    )
    db_session.add(user_team)

    await db_session.commit()
    await db_session.refresh(team)
    return team


@pytest_asyncio.fixture
async def test_task(db_session: AsyncSession, test_team, test_manager, test_user):
    """Создает тестовую задачу в БД"""

    task = Task(
        title="Test Task",
        description="Test task description",
        status=TaskStatus.OPEN,
        deadline=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=7),
        creator_id=test_manager.id,
        assignee_id=test_user.id,
        team_id=test_team.id
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)
    return task
