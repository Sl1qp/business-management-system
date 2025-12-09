import pytest
from unittest.mock import MagicMock
from app.utils.teams import generate_invite_code
from app.utils.teams import get_team_by_id
from app.models.team import Team
from app.utils.teams import get_user_team_role

class TestTeamUtils:
    """Тесты утилит команд"""

    @pytest.mark.asyncio
    async def test_generate_invite_code(self):
        """Тест генерации кода приглашения"""
        code = generate_invite_code()

        assert code is not None
        assert isinstance(code, str)
        assert len(code) > 0

    @pytest.mark.asyncio
    async def test_get_team_by_id_found(self, mock_db_session):
        """Тест получения команды по ID"""

        mock_team = Team(
            id=1,
            name="Test Team",
            invite_code="test123"
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_team
        mock_db_session.execute.return_value = mock_result

        result = await get_team_by_id(mock_db_session, 1)

        assert result == mock_team
        assert result.id == 1
        assert result.name == "Test Team"

        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_team_by_id_not_found(self, mock_db_session):
        """Тест получения команды по ID (не найдена)"""

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        result = await get_team_by_id(mock_db_session, 999)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_user_team_role_found(self, mock_db_session):
        """Тест получения роли пользователя в команде (найдено)"""

        mock_result = MagicMock()

        class MockUserTeam:
            role = "admin"

        mock_result.scalar_one_or_none.return_value = MockUserTeam()
        mock_db_session.execute.return_value = mock_result

        result = await get_user_team_role(mock_db_session, 1, 1)

        assert result == "admin"

    @pytest.mark.asyncio
    async def test_get_user_team_role_not_found(self, mock_db_session):
        """Тест получения роли пользователя в команде"""

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        result = await get_user_team_role(mock_db_session, 1, 1)

        assert result is None