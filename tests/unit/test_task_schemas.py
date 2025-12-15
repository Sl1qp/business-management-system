from datetime import datetime, timedelta, timezone

from app.schemas.task import TaskCreate, TaskUpdate, TaskStatus


class TestTaskStatusEnum:
    """Тесты enum статусов задач"""

    def test_task_status_values(self):
        """Тест значений статусов задач"""
        assert TaskStatus.OPEN.value == "OPEN"
        assert TaskStatus.IN_PROGRESS.value == "IN_PROGRESS"
        assert TaskStatus.COMPLETED.value == "COMPLETED"


class TestTaskCreateSchema:
    """Тесты схемы создания задачи"""

    def test_valid_task_create(self):
        """Тест создания задачи с валидными данными"""
        deadline = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=7)
        data = {
            "title": "Test Task",
            "description": "Test Description",
            "status": "OPEN",
            "deadline": deadline,
            "team_id": 1
        }
        task = TaskCreate(**data)
        assert task.title == "Test Task"
        assert task.description == "Test Description"
        assert task.status == TaskStatus.OPEN
        assert task.team_id == 1

    def test_task_create_minimal(self):
        """Тест создания задачи с минимальными данными"""
        data = {
            "title": "Task",
            "team_id": 1
        }
        task = TaskCreate(**data)
        assert task.title == "Task"
        assert task.description is None
        assert task.status == TaskStatus.OPEN
        assert task.deadline is None
        assert task.assignee_id is None
        assert task.team_id == 1


class TestTaskUpdateSchema:
    """Тесты схемы обновления задачи"""

    def test_task_update_partial(self):
        """Тест частичного обновления задачи"""
        data = {"title": "Updated Title"}
        task_update = TaskUpdate(**data)
        assert task_update.title == "Updated Title"
        assert task_update.description is None
        assert task_update.status is None
