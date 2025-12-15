from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import current_active_user
from app.core.database import get_async_session
from app.core.templates import templates
from app.models.evaluation import Evaluation as EvaluationModel
from app.models.task import Task
from app.models.user import User
from app.schemas.evaluation import (
    EvaluationUpdate,
    Evaluation,
    EvaluationWithDetails,
    EvaluationStats,
    EvaluationCreateRequest
)

router = APIRouter(prefix="/evaluations", tags=["evaluations"])


async def get_evaluation_model(
        evaluation_id: int,
        session: AsyncSession = Depends(get_async_session)
) -> EvaluationModel:
    result = await session.execute(
        select(EvaluationModel).where(EvaluationModel.id == evaluation_id)
    )
    evaluation = result.scalar_one_or_none()

    if not evaluation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evaluation not found"
        )

    return evaluation


async def require_evaluation_owner(
        evaluation: EvaluationModel = Depends(get_evaluation_model),
        user: User = Depends(current_active_user)
) -> EvaluationModel:
    if evaluation.evaluator_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own evaluations"
        )

    return evaluation


async def require_evaluation_owner_or_superuser(
        evaluation: EvaluationModel = Depends(get_evaluation_model),
        user: User = Depends(current_active_user)
) -> EvaluationModel:
    if evaluation.evaluator_id != user.id and not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own evaluations"
        )

    return evaluation


async def require_own_evaluations_or_superuser(
        target_user_id: int,
        user: User = Depends(current_active_user)
) -> int:
    if target_user_id != user.id and not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own evaluations"
        )

    return target_user_id


async def validate_task_exists(
        task_id: int,
        session: AsyncSession = Depends(get_async_session)
) -> Task:
    task_result = await session.execute(select(Task).where(Task.id == task_id))
    task = task_result.scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    return task


async def validate_user_exists(
        user_id: int,
        session: AsyncSession = Depends(get_async_session)
) -> User:
    user_result = await session.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return user


async def enrich_evaluation_with_details(
        evaluation: EvaluationModel,
        session: AsyncSession
) -> EvaluationWithDetails:
    task_result = await session.execute(select(Task.title).where(Task.id == evaluation.task_id))
    task_title = task_result.scalar() or "Неизвестная задача"

    user_result = await session.execute(
        select(User.first_name, User.last_name).where(User.id == evaluation.user_id)
    )
    user = user_result.first()
    user_name = f"{user.first_name} {user.last_name}" if user else "Неизвестный пользователь"

    evaluator_result = await session.execute(
        select(User.first_name, User.last_name).where(User.id == evaluation.evaluator_id)
    )
    evaluator = evaluator_result.first()
    evaluator_name = f"{evaluator.first_name} {evaluator.last_name}" if evaluator else "Неизвестный оценщик"

    return EvaluationWithDetails(
        id=evaluation.id,
        rating=evaluation.rating,
        comment=evaluation.comment,
        task_id=evaluation.task_id,
        user_id=evaluation.user_id,
        evaluator_id=evaluation.evaluator_id,
        created_at=evaluation.created_at,
        task_title=task_title,
        user_name=user_name,
        evaluator_name=evaluator_name
    )


async def validate_evaluation_data(
        evaluation: EvaluationCreateRequest,
        session: AsyncSession = Depends(get_async_session)
) -> tuple[Task, User]:
    task_result = await session.execute(select(Task).where(Task.id == evaluation.task_id))
    task = task_result.scalar_one_or_none()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    user_result = await session.execute(select(User).where(User.id == evaluation.user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return task, user


@router.get("/list", response_model=List[EvaluationWithDetails])
async def get_evaluations_api(
        skip: int = Query(0, ge=0),
        limit: int = Query(50, ge=1, le=100),
        session: AsyncSession = Depends(get_async_session),
        current_user: User = Depends(current_active_user)
):
    query = select(EvaluationModel).order_by(desc(EvaluationModel.created_at)).offset(skip).limit(limit)
    result = await session.execute(query)
    evaluations = result.scalars().all()

    evaluations_with_details = []
    for evaluation in evaluations:
        enriched_eval = await enrich_evaluation_with_details(evaluation, session)
        evaluations_with_details.append(enriched_eval)

    return evaluations_with_details


@router.get("/", response_model=List[EvaluationWithDetails])
async def get_evaluations(
        skip: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=1000),
        task_id: Optional[int] = None,
        user_id: Optional[int] = None,
        evaluator_id: Optional[int] = None,
        session: AsyncSession = Depends(get_async_session),
):
    query = select(EvaluationModel)

    if task_id:
        query = query.where(EvaluationModel.task_id == task_id)
    if user_id:
        query = query.where(EvaluationModel.user_id == user_id)
    if evaluator_id:
        query = query.where(EvaluationModel.evaluator_id == evaluator_id)

    query = query.offset(skip).limit(limit)
    result = await session.execute(query)
    evaluations = result.scalars().all()

    evaluations_with_details = []
    for eval_obj in evaluations:
        enriched_eval = await enrich_evaluation_with_details(eval_obj, session)
        evaluations_with_details.append(enriched_eval)

    return evaluations_with_details


@router.get("/{evaluation_id}", response_model=EvaluationWithDetails)
async def get_evaluation(
        evaluation: EvaluationModel = Depends(get_evaluation_model),
        session: AsyncSession = Depends(get_async_session)
):
    return await enrich_evaluation_with_details(evaluation, session)


@router.post("/", response_model=Evaluation, status_code=status.HTTP_201_CREATED)
async def create_evaluation(
        evaluation: EvaluationCreateRequest,
        validated_data: tuple[Task, User] = Depends(validate_evaluation_data),
        session: AsyncSession = Depends(get_async_session),
        current_user: User = Depends(current_active_user)
):
    evaluation_data = evaluation.dict()
    evaluation_data["evaluator_id"] = current_user.id

    try:
        db_evaluation = EvaluationModel(**evaluation_data)
        session.add(db_evaluation)
        await session.commit()
        await session.refresh(db_evaluation)

    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при создании оценки: {str(e)}"
        )

    return db_evaluation


@router.put("/{evaluation_id}", response_model=Evaluation)
async def update_evaluation(
        evaluation_update: EvaluationUpdate,
        db_evaluation: EvaluationModel = Depends(require_evaluation_owner),
        session: AsyncSession = Depends(get_async_session)
):
    try:
        update_data = evaluation_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_evaluation, field, value)

        session.add(db_evaluation)
        await session.commit()
        await session.refresh(db_evaluation)

    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при обновлении оценки: {str(e)}"
        )

    return db_evaluation


@router.delete("/{evaluation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_evaluation(
        db_evaluation: EvaluationModel = Depends(require_evaluation_owner_or_superuser),
        session: AsyncSession = Depends(get_async_session)
):
    try:
        await session.delete(db_evaluation)
        await session.commit()

    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при удалении оценки: {str(e)}"
        )

    return None


@router.get("/user/{user_id}/stats", response_model=EvaluationStats)
async def get_user_evaluation_stats(
        user_id: int = Depends(require_own_evaluations_or_superuser),
        period_days: int = Query(30, ge=1, le=365),
        session: AsyncSession = Depends(get_async_session),
):
    end_date = datetime.now()
    start_date = end_date - timedelta(days=period_days)

    result = await session.execute(
        select(
            func.avg(EvaluationModel.rating).label("average_rating"),
            func.count(EvaluationModel.id).label("total_evaluations")
        ).where(
            EvaluationModel.user_id == user_id,
            EvaluationModel.created_at >= start_date,
            EvaluationModel.created_at <= end_date
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


@router.get("/user/{user_id}", response_model=List[EvaluationWithDetails])
async def get_user_evaluations(
        user_id: int = Depends(require_own_evaluations_or_superuser),
        skip: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=1000),
        session: AsyncSession = Depends(get_async_session),
):
    return await get_evaluations(
        skip=skip,
        limit=limit,
        user_id=user_id,
        session=session,
    )


@router.get("/task/{task_id}", response_model=List[EvaluationWithDetails])
async def get_task_evaluations(
        task_id: int,
        skip: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=1000),
        session: AsyncSession = Depends(get_async_session),
):
    return await get_evaluations(
        skip=skip,
        limit=limit,
        task_id=task_id,
        session=session,
    )


@router.get("", response_class=HTMLResponse)
async def get_evaluations_page(request: Request):
    return templates.TemplateResponse("evaluations/evaluations.html", {
        "request": request,
    })
