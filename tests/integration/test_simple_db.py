import pytest
from sqlalchemy import text

from app.models.team import Team
from app.models.user import User


@pytest.mark.integration
@pytest.mark.asyncio
async def test_database_connection(db_session):
    """Простой тест подключения к БД"""
    result = await db_session.execute(text("SELECT 1"))
    assert result.scalar() == 1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_simple_models(db_session):
    """Тест создания простых моделей"""

    user = User(
        email="test@example.com",
        hashed_password="hashed_password"
    )
    db_session.add(user)

    team = Team(
        name="Test Team",
        invite_code="test123"
    )
    db_session.add(team)

    await db_session.commit()

    assert user.id is not None
    assert team.id is not None
    assert user.email == "test@example.com"
    assert team.name == "Test Team"
