from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.task import Task, TaskComment


async def get_task_by_id(db: AsyncSession, task_id: int):
    result = await db.execute(select(Task).filter(Task.id == task_id))
    return result.scalar_one_or_none()


async def get_task_comments(db: AsyncSession, task_id: int):
    result = await db.execute(
        select(TaskComment)
        .join(TaskComment.author)
        .filter(TaskComment.task_id == task_id)
        .order_by(TaskComment.created_at.asc())
    )
    return result.scalars().all()
