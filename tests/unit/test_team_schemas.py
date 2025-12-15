import pytest

from app.schemas.team import TeamCreate, TeamUpdate, InviteUserRequest, JoinTeamRequest


class TestTeamCreateSchema:
    """Тесты схемы создания команды"""

    def test_valid_team_create(self):
        """Тест создания команды с валидными данными"""
        data = {
            "name": "Test Team",
            "description": "Test Description"
        }
        team = TeamCreate(**data)
        assert team.name == "Test Team"
        assert team.description == "Test Description"

    def test_team_create_minimal(self):
        """Тест создания команды с минимальными данными"""
        data = {"name": "Team Name"}
        team = TeamCreate(**data)
        assert team.name == "Team Name"
        assert team.description is None


class TestTeamUpdateSchema:
    """Тесты схемы обновления команды"""

    def test_team_update_partial(self):
        """Тест частичного обновления команды"""
        data = {"name": "Updated Name"}
        team_update = TeamUpdate(**data)
        assert team_update.name == "Updated Name"
        assert team_update.description is None

    def test_team_update_all_fields(self):
        """Тест обновления всех полей команды"""
        data = {
            "name": "Updated Name",
            "description": "Updated Description"
        }
        team_update = TeamUpdate(**data)
        assert team_update.name == "Updated Name"
        assert team_update.description == "Updated Description"


class TestInviteUserRequestSchema:
    """Тесты схемы приглашения пользователя"""

    def test_valid_invite(self):
        """Тест валидного приглашения"""
        data = {
            "email": "user@example.com",
            "role": "member"
        }
        invite = InviteUserRequest(**data)
        assert invite.email == "user@example.com"
        assert invite.role == "member"

    @pytest.mark.parametrize("role", ["member", "manager", "admin"])
    def test_valid_roles(self, role):
        """Тест всех валидных ролей"""
        data = {"email": "user@example.com", "role": role}
        invite = InviteUserRequest(**data)
        assert invite.role == role

    def test_default_role(self):
        """Тест значения роли по умолчанию"""
        data = {"email": "user@example.com"}
        invite = InviteUserRequest(**data)
        assert invite.role == "member"

    def test_invalid_role_fails(self):
        """Тест: невалидная роль должна вызывать ошибку"""
        data = {"email": "user@example.com", "role": "invalid"}
        with pytest.raises(ValueError, match="Role must be one of"):
            InviteUserRequest(**data)


class TestJoinTeamRequestSchema:
    """Тесты схемы присоединения к команде"""

    def test_valid_join_request(self):
        """Тест валидного запроса на присоединение"""
        data = {"invite_code": "abc123-def456"}
        join_request = JoinTeamRequest(**data)
        assert join_request.invite_code == "abc123-def456"
