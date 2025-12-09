import pytest
from sqlalchemy.orm import selectinload
from app.models.user import User
from app.models.team import Team, UserTeam
import secrets
from app.models.task import Task, TaskStatus
from sqlalchemy import select


@pytest.mark.integration
@pytest.mark.db
class TestDatabaseOperations:
    """Интеграционные тесты операций с БД"""

    @pytest.mark.asyncio
    async def test_create_and_retrieve_user(self, db_session):
        """Тест создания и получения пользователя из БД"""

        user = User(
            email="integration@example.com",
            hashed_password="hashed_password",
            first_name="Integration",
            last_name="Test",
            role="user",
            is_active=True,
            is_superuser=False,
            is_verified=False
        )

        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        query = select(User).where(User.email == "integration@example.com")
        result = await db_session.execute(query)
        retrieved_user = result.scalar_one()

        assert retrieved_user.email == "integration@example.com"
        assert retrieved_user.first_name == "Integration"
        assert retrieved_user.last_name == "Test"
        assert retrieved_user.role == "user"

    @pytest.mark.asyncio
    async def test_create_team_with_members(self, db_session):
        """Тест создания команды с участниками"""

        user1 = User(
            email="user1@example.com",
            hashed_password="hashed_password",
            is_active=True,
            is_superuser=False,
            is_verified=False
        )
        user2 = User(
            email="user2@example.com",
            hashed_password="hashed_password",
            is_active=True,
            is_superuser=False,
            is_verified=False
        )
        db_session.add_all([user1, user2])
        await db_session.flush()

        team = Team(
            name="Integration Team",
            invite_code=secrets.token_urlsafe(12)
        )
        db_session.add(team)
        await db_session.flush()

        user_team1 = UserTeam(
            user_id=user1.id,
            team_id=team.id,
            role="admin"
        )
        user_team2 = UserTeam(
            user_id=user2.id,
            team_id=team.id,
            role="member"
        )
        db_session.add_all([user_team1, user_team2])
        await db_session.commit()

        result = await db_session.execute(
            select(Team)
            .where(Team.id == team.id)
            .options(selectinload(Team.members))
        )
        team_with_members = result.scalar_one()

        assert len(team_with_members.members) == 2

        roles = [member.role for member in team_with_members.members]
        assert "admin" in roles
        assert "member" in roles

    @pytest.mark.asyncio
    async def test_cascade_delete_team_members(self, db_session):
        """Тест каскадного удаления участников при удалении команды"""

        user = User(
            email="cascade@example.com",
            hashed_password="hashed_password",
            is_active=True,
            is_superuser=False,
            is_verified=False
        )
        team = Team(
            name="Cascade Team",
            invite_code=secrets.token_urlsafe(12)
        )
        db_session.add_all([user, team])
        await db_session.flush()

        user_team = UserTeam(
            user_id=user.id,
            team_id=team.id,
            role="member"
        )
        db_session.add(user_team)
        await db_session.commit()

        await db_session.delete(team)
        await db_session.commit()

        query = select(UserTeam).where(UserTeam.team_id == team.id)
        result = await db_session.execute(query)
        remaining_links = result.scalars().all()

        assert len(remaining_links) == 0

    @pytest.mark.asyncio
    async def test_task_status_enum_in_db(self, db_session):
        """Тест сохранения enum статусов задач в БД"""

        task_open = Task(
            title="Open Task",
            status=TaskStatus.OPEN,
            creator_id=1,
            team_id=1
        )
        task_in_progress = Task(
            title="In Progress Task",
            status=TaskStatus.IN_PROGRESS,
            creator_id=1,
            team_id=1
        )
        task_completed = Task(
            title="Completed Task",
            status=TaskStatus.COMPLETED,
            creator_id=1,
            team_id=1
        )

        db_session.add_all([task_open, task_in_progress, task_completed])
        await db_session.commit()

        query = select(Task).order_by(Task.id)
        result = await db_session.execute(query)
        tasks = result.scalars().all()

        assert len(tasks) == 3
        assert tasks[0].status == TaskStatus.OPEN
        assert tasks[1].status == TaskStatus.IN_PROGRESS
        assert tasks[2].status == TaskStatus.COMPLETED

        assert tasks[0].status.value == "OPEN"
        assert tasks[1].status.value == "IN_PROGRESS"
        assert tasks[2].status.value == "COMPLETED"