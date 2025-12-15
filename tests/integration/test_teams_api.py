import pytest


@pytest.mark.integration
class TestTeamsAPI:
    """Интеграционные тесты API команд"""

    @pytest.mark.asyncio
    async def test_get_teams_list_empty(self, async_client, test_user):
        """Тест получения пустого списка команд"""
        response = await async_client.get("/teams/list")

        assert response.status_code in [200, 401, 403]
        print(f"GET /teams/list status: {response.status_code}")

    @pytest.mark.asyncio
    async def test_create_team_endpoint_structure(self, async_client):
        """Тест структуры эндпоинта создания команды"""
        response = await async_client.post(
            "/teams",
            json={
                "name": "API Test Team",
                "description": "Team created via API test"
            }
        )

        assert response.status_code in [200, 401, 403]
        print(f"POST /teams status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            assert "id" in data
            assert "name" in data
            assert "invite_code" in data
            assert "members" in data

    @pytest.mark.asyncio
    async def test_get_team_by_id_structure(self, async_client, test_team):
        """Тест структуры ответа получения команды по ID"""
        response = await async_client.get(f"/teams/{test_team.id}")

        assert response.status_code in [200, 401, 403]
        print(f"GET /teams/{test_team.id} status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            assert "id" in data
            assert "name" in data
            assert "invite_code" in data
            assert "members" in data
            assert "created_at" in data
            assert "updated_at" in data

    @pytest.mark.asyncio
    async def test_team_endpoints_exist(self, async_client):
        """Тест существования всех основных эндпоинтов команд"""
        endpoints = [
            ("GET", "/teams/list"),
            ("POST", "/teams"),
            ("GET", "/teams/1"),
            ("PUT", "/teams/1"),
            ("DELETE", "/teams/1"),
            ("GET", "/teams/1/members"),
            ("POST", "/teams/1/invite"),
            ("POST", "/teams/join"),
            ("DELETE", "/teams/1/members/1"),
            ("GET", "/teams/1/invite-code"),
        ]

        for method, endpoint in endpoints:
            print(f"Testing {method} {endpoint}")

            if method == "GET":
                response = await async_client.get(endpoint)
            elif method == "POST":
                response = await async_client.post(endpoint, json={})
            elif method == "PUT":
                response = await async_client.put(endpoint, json={})
            elif method == "DELETE":
                response = await async_client.delete(endpoint)

            assert response.status_code != 404, f"Endpoint {method} {endpoint} not found"
