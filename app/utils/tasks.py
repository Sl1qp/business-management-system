from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.task import Task, TaskComment
from app.models.user import User


async def get_task_by_id(db: AsyncSession, task_id: int):
    result = await db.execute(select(Task).filter(Task.id == task_id))
    return result.scalar_one_or_none()


async def get_task_comments(db: AsyncSession, task_id: int):
    result = await db.execute(
        select(TaskComment, User)
        .join(User, TaskComment.author_id == User.id)
        .filter(TaskComment.task_id == task_id)
        .order_by(TaskComment.created_at)
    )
    return result.all()
