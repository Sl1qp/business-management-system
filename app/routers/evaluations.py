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

        eval_with_details = EvaluationWithDetails(
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
        evaluations_with_details.append(eval_with_details)

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
    query = select(Evaluation)

    if task_id:
        query = query.where(Evaluation.task_id == task_id)
    if user_id:
        query = query.where(Evaluation.user_id == user_id)
    if evaluator_id:
        query = query.where(Evaluation.evaluator_id == evaluator_id)

    query = query.offset(skip).limit(limit)
    result = await session.execute(query)
    evaluations = result.scalars().all()

    evaluations_with_details = []
    for eval in evaluations:
        eval_dict = eval.__dict__

        task_result = await session.execute(select(Task.title).where(Task.id == eval.task_id))
        eval_dict["task_title"] = task_result.scalar()

        user_result = await session.execute(
            select(User.first_name, User.last_name).where(User.id == eval.user_id)
        )
        user = user_result.first()
        eval_dict["user_name"] = f"{user.first_name} {user.last_name}" if user else "Unknown"

        evaluator_result = await session.execute(
            select(User.first_name, User.last_name).where(User.id == eval.evaluator_id)
        )
        evaluator = evaluator_result.first()
        eval_dict["evaluator_name"] = f"{evaluator.first_name} {evaluator.last_name}" if evaluator else "Unknown"

        evaluations_with_details.append(EvaluationWithDetails(**eval_dict))

    return evaluations_with_details


@router.get("/{evaluation_id}", response_model=EvaluationWithDetails)
async def get_evaluation(
        evaluation_id: int,
        session: AsyncSession = Depends(get_async_session)
):
    result = await session.execute(
        select(EvaluationModel).where(EvaluationModel.id == evaluation_id)
    )
    evaluation = result.scalar_one_or_none()

    if not evaluation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evaluation not found"
        )

    eval_dict = evaluation.__dict__

    task_result = await session.execute(select(Task.title).where(Task.id == evaluation.task_id))
    eval_dict["task_title"] = task_result.scalar()

    user_result = await session.execute(
        select(User.first_name, User.last_name).where(User.id == evaluation.user_id)
    )
    user = user_result.first()
    eval_dict["user_name"] = f"{user.first_name} {user.last_name}" if user else "Unknown"

    evaluator_result = await session.execute(
        select(User.first_name, User.last_name).where(User.id == evaluation.evaluator_id)
    )
    evaluator = evaluator_result.first()
    eval_dict["evaluator_name"] = f"{evaluator.first_name} {evaluator.last_name}" if evaluator else "Unknown"

    return EvaluationWithDetails(**eval_dict)


@router.post("/", response_model=Evaluation, status_code=status.HTTP_201_CREATED)
async def create_evaluation(
        evaluation: EvaluationCreateRequest,
        session: AsyncSession = Depends(get_async_session),
        current_user: User = Depends(current_active_user)
):
    task_result = await session.execute(select(Task).where(Task.id == evaluation.task_id))
    if not task_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    user_result = await session.execute(select(User).where(User.id == evaluation.user_id))
    if not user_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    evaluation_data = evaluation.dict()
    evaluation_data["evaluator_id"] = current_user.id

    db_evaluation = EvaluationModel(**evaluation_data)
    session.add(db_evaluation)
    await session.commit()
    await session.refresh(db_evaluation)

    return db_evaluation


@router.put("/{evaluation_id}", response_model=Evaluation)
async def update_evaluation(
        evaluation_id: int,
        evaluation_update: EvaluationUpdate,
        session: AsyncSession = Depends(get_async_session),
        current_user: User = Depends(current_active_user)
):
    result = await session.execute(
        select(Evaluation).where(Evaluation.id == evaluation_id)
    )
    db_evaluation = result.scalar_one_or_none()

    if not db_evaluation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evaluation not found"
        )

    if db_evaluation.evaluator_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own evaluations"
        )

    update_data = evaluation_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_evaluation, field, value)

    session.add(db_evaluation)
    await session.commit()
    await session.refresh(db_evaluation)

    return db_evaluation


@router.delete("/{evaluation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_evaluation(
        evaluation_id: int,
        session: AsyncSession = Depends(get_async_session),
        current_user: User = Depends(current_active_user)
):
    result = await session.execute(
        select(Evaluation).where(Evaluation.id == evaluation_id)
    )
    db_evaluation = result.scalar_one_or_none()

    if not db_evaluation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evaluation not found"
        )

    if db_evaluation.evaluator_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own evaluations"
        )

    await session.delete(db_evaluation)
    await session.commit()

    return None


@router.get("/user/{user_id}/stats", response_model=EvaluationStats)
async def get_user_evaluation_stats(
        user_id: int,
        period_days: int = Query(30, ge=1, le=365),
        session: AsyncSession = Depends(get_async_session),
        current_user: User = Depends(current_active_user)
):
    if user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own evaluation statistics"
        )

    end_date = datetime.now()
    start_date = end_date - timedelta(days=period_days)

    result = await session.execute(
        select(
            func.avg(Evaluation.rating).label("average_rating"),
            func.count(Evaluation.id).label("total_evaluations")
        ).where(
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


@router.get("/user/{user_id}", response_model=List[EvaluationWithDetails])
async def get_user_evaluations(
        user_id: int,
        skip: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=1000),
        session: AsyncSession = Depends(get_async_session),
        current_user: User = Depends(current_active_user)
):
    if user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own evaluations"
        )

    return await get_evaluations(
        skip=skip,
        limit=limit,
        user_id=user_id,
        session=session,
        current_user=current_user
    )


@router.get("/task/{task_id}", response_model=List[EvaluationWithDetails])
async def get_task_evaluations(
        task_id: int,
        skip: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=1000),
        session: AsyncSession = Depends(get_async_session),
        current_user: User = Depends(current_active_user)
):
    return await get_evaluations(
        skip=skip,
        limit=limit,
        task_id=task_id,
        session=session,
        current_user=current_user
    )


@router.get("", response_class=HTMLResponse)
async def get_evaluations_page(request: Request):
    return templates.TemplateResponse("evaluations/evaluations.html", {
        "request": request,
    })
