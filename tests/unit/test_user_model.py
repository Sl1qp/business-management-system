import secrets
from datetime import datetime

import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.team import Team, UserTeam
from app.models.user import User


class TestUserModel:
    """Тесты модели пользователя"""

    @pytest.mark.asyncio
    async def test_create_user(self, db_session):
        """Тест создания пользователя"""

        user = User(
            email="test@example.com",
            hashed_password="hashed_password",
            first_name="John",
            last_name="Doe",
            role="user",
            is_active=True,
            is_superuser=False,
            is_verified=False
        )

        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        assert user.id is not None
        assert user.email == "test@example.com"
        assert user.first_name == "John"
        assert user.last_name == "Doe"
        assert user.role == "user"

        assert user.created_at is not None
        assert isinstance(user.created_at, datetime)
        assert user.updated_at is not None
        assert isinstance(user.updated_at, datetime)

    @pytest.mark.asyncio
    async def test_user_relationships(self, db_session):
        """Тест связей пользователя"""
        user = User(
            email="user@example.com",
            hashed_password="hashed_password",
            is_active=True,
            is_superuser=False,
            is_verified=False
        )
        db_session.add(user)
        await db_session.flush()

        team = Team(
            name="Test Team",
            invite_code=secrets.token_urlsafe(12)
        )
        db_session.add(team)
        await db_session.flush()

        user_team = UserTeam(
            user_id=user.id,
            team_id=team.id,
            role="member"
        )
        db_session.add(user_team)
        await db_session.commit()

        result = await db_session.execute(
            select(User)
            .where(User.id == user.id)
            .options(selectinload(User.teams))
        )
        user_with_teams = result.scalar_one()

        assert len(user_with_teams.teams) == 1
        assert user_with_teams.teams[0].team_id == team.id
        assert user_with_teams.teams[0].role == "member"

    @pytest.mark.asyncio
    async def test_user_role_default(self, db_session):
        """Тест значения роли по умолчанию"""

        user = User(
            email="test@example.com",
            hashed_password="hashed_password",
            is_active=True,
            is_superuser=False,
            is_verified=False
        )

        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        assert user.role == "user"
