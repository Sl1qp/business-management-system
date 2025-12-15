from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.evaluation import Evaluation
from app.models.task import Task
from app.schemas.evaluation import EvaluationStats
from app.utils.teams import is_team_manager_or_admin


async def get_evaluation_by_id(db: AsyncSession, evaluation_id: int):
    result = await db.execute(
        select(Evaluation).filter(Evaluation.id == evaluation_id)
    )
    return result.scalar_one_or_none()


async def get_user_evaluations(db: AsyncSession, user_id: int, limit: int = 100):
    result = await db.execute(
        select(Evaluation)
        .filter(Evaluation.user_id == user_id)
        .order_by(Evaluation.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


async def get_task_evaluation(db: AsyncSession, task_id: int):
    result = await db.execute(
        select(Evaluation).filter(Evaluation.task_id == task_id)
    )
    return result.scalar_one_or_none()


async def get_average_rating(db: AsyncSession, user_id: int, days: int = 30) -> EvaluationStats:
    end_date = datetime.now(timezone.utc).replace(tzinfo=None)
    start_date = end_date - timedelta(days=days)

    result = await db.execute(
        select(
            func.avg(Evaluation.rating).label('average_rating'),
            func.count(Evaluation.id).label('total_evaluations')
        )
        .filter(
            Evaluation.user_id == user_id,
            Evaluation.created_at >= start_date,
            Evaluation.created_at <= end_date
        )
    )

    stats = result.first()

    return EvaluationStats(
        user_id=user_id,
        average_rating=float(stats.average_rating) if stats.average_rating else 0.0,
        total_evaluations=stats.total_evaluations,
        period_start=start_date,
        period_end=end_date
    )


async def can_evaluate_task(db: AsyncSession, task_id: int, evaluator_id: int):
    result = await db.execute(
        select(Task).filter(Task.id == task_id)
    )
    task = result.scalar_one_or_none()

    if not task:
        return False

    return await is_team_manager_or_admin(db, evaluator_id, task.team_id)
