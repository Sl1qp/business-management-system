from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.requests import Request
from fastapi.responses import HTMLResponse
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.core.auth import current_active_user
from app.core.database import get_async_session
from app.core.templates import templates
from app.models.task import Task, TaskComment
from app.models.team import UserTeam, Team
from app.models.user import User
from app.schemas.task import PaginatedResponse, TaskCreate, TaskRead, TaskUpdate, TaskCommentCreate, TaskCommentRead
from app.utils.tasks import get_task_by_id
from app.utils.teams import is_team_manager_or_admin, get_user_team_role

router = APIRouter(prefix="/tasks", tags=["tasks"])


def load_task_relationships(query):
    return query.options(
        selectinload(Task.creator),
        selectinload(Task.assignee),
        selectinload(Task.team).selectinload(Team.members).selectinload(UserTeam.user),
        selectinload(Task.comments).selectinload(TaskComment.author)
    )


@router.get("/my-team-tasks", response_model=List[TaskRead])
async def get_my_team_tasks(
        user: User = Depends(current_active_user),
        db: AsyncSession = Depends(get_async_session)
):
    try:
        from sqlalchemy.orm import aliased

        team_subquery = (
            select(UserTeam.team_id)
            .filter(UserTeam.user_id == user.id)
        ).subquery()

        query = load_task_relationships(
            select(Task)
            .filter(Task.team_id.in_(team_subquery))
        )

        result = await db.execute(query)
        tasks = result.scalars().all()

        return tasks
    except Exception as e:
        print(f"Error in get_my_team_tasks: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("", response_class=HTMLResponse)
async def tasks_page(
        request: Request,
        page: int = Query(1, ge=1, description="Номер страницы"),
        per_page: int = Query(10, ge=1, le=100, description="Элементов на странице")
):
    return templates.TemplateResponse(
        "tasks/tasks.html",
        {
            "request": request,
            "page": page,
            "per_page": per_page
        }
    )


@router.get("/list", response_model=PaginatedResponse[TaskRead])
async def get_tasks_list(
        page: int = Query(1, ge=1, description="Номер страницы"),
        per_page: int = Query(10, ge=1, le=100, description="Элементов на странице"),
        filter: str = Query("all", description="Фильтр по статусу"),
        sort: str = Query("newest", description="Сортировка"),
        user: User = Depends(current_active_user),
        db: AsyncSession = Depends(get_async_session)
):
    try:
        offset = (page - 1) * per_page

        base_query = load_task_relationships(
            select(Task).filter(Task.assignee_id == user.id)
        )

        if filter != "all":
            base_query = base_query.filter(Task.status == filter)

        if sort == "newest":
            base_query = base_query.order_by(Task.created_at.desc())
        elif sort == "oldest":
            base_query = base_query.order_by(Task.created_at.asc())
        elif sort == "deadline":
            base_query = base_query.order_by(Task.deadline.asc())
        elif sort == "priority":
            base_query = base_query.order_by(Task.created_at.desc())

        result = await db.execute(
            base_query
            .offset(offset)
            .limit(per_page)
        )
        tasks = result.scalars().all()

        count_query = select(func.count(Task.id)).filter(Task.assignee_id == user.id)
        if filter != "all":
            count_query = count_query.filter(Task.status == filter)

        count_result = await db.execute(count_query)
        total_count = count_result.scalar()

        return PaginatedResponse[TaskRead](
            items=tasks,
            page=page,
            per_page=per_page,
            total_count=total_count,
            total_pages=(total_count + per_page - 1) // per_page if total_count > 0 else 0
        )
    except Exception as e:
        print(f"Error in get_tasks_list: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("", response_model=TaskRead)
async def create_task(
        task_data: TaskCreate,
        user: User = Depends(current_active_user),
        db: AsyncSession = Depends(get_async_session)
):
    user_role = await get_user_team_role(db, user.id, task_data.team_id)
    if not user_role:
        raise HTTPException(status_code=403, detail="You are not a member of this team")

    if task_data.assignee_id is not None:
        assignee_role = await get_user_team_role(db, task_data.assignee_id, task_data.team_id)
        if not assignee_role:
            raise HTTPException(status_code=400, detail="Assignee must be a member of this team")

    task = Task(
        title=task_data.title,
        description=task_data.description,
        status=task_data.status,
        deadline=task_data.deadline,
        creator_id=user.id,
        assignee_id=task_data.assignee_id,
        team_id=task_data.team_id
    )

    db.add(task)
    await db.commit()

    result = await db.execute(
        load_task_relationships(select(Task).where(Task.id == task.id))
    )
    task_with_relations = result.scalar_one()

    return task_with_relations


@router.get("/{task_id}", response_model=TaskRead)
async def get_task(
        task_id: int,
        user: User = Depends(current_active_user),
        db: AsyncSession = Depends(get_async_session)
):
    result = await db.execute(
        load_task_relationships(select(Task).where(Task.id == task_id))
    )
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    user_role = await get_user_team_role(db, user.id, task.team_id)
    if not user_role:
        raise HTTPException(status_code=403, detail="You are not a member of this task's team")

    return task


@router.put("/{task_id}", response_model=TaskRead)
async def update_task(
        task_id: int,
        task_data: TaskUpdate,
        user: User = Depends(current_active_user),
        db: AsyncSession = Depends(get_async_session)
):
    task = await get_task_by_id(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    user_role = await get_user_team_role(db, user.id, task.team_id)
    if user.id != task.assignee_id and not await is_team_manager_or_admin(db, user.id, task.team_id):
        raise HTTPException(status_code=403, detail="You can only update your own tasks")

    if task_data.title is not None:
        task.title = task_data.title
    if task_data.description is not None:
        task.description = task_data.description
    if task_data.status is not None:
        task.status = task_data.status
    if task_data.deadline is not None:
        task.deadline = task_data.deadline
    if task_data.assignee_id is not None:
        new_assignee_role = await get_user_team_role(db, task_data.assignee_id, task.team_id)
        if not new_assignee_role:
            raise HTTPException(status_code=400, detail="Assignee must be a team member")
        task.assignee_id = task_data.assignee_id

    task.updated_at = datetime.utcnow()
    await db.commit()

    result = await db.execute(
        load_task_relationships(select(Task).where(Task.id == task_id))
    )
    task = result.scalar_one()

    return task


@router.delete("/{task_id}")
async def delete_task(
        task_id: int,
        user: User = Depends(current_active_user),
        db: AsyncSession = Depends(get_async_session)
):
    task = await get_task_by_id(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    user_role = await get_user_team_role(db, user.id, task.team_id)
    if user.id != task.creator_id and not await is_team_manager_or_admin(db, user.id, task.team_id):
        raise HTTPException(status_code=403, detail="You can only delete your own tasks")

    await db.delete(task)
    await db.commit()

    return {"message": "Task deleted successfully"}


@router.post("/{task_id}/comments", response_model=TaskCommentRead)
async def add_comment(
        task_id: int,
        comment_data: TaskCommentCreate,
        user: User = Depends(current_active_user),
        db: AsyncSession = Depends(get_async_session)
):
    task = await get_task_by_id(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    user_role = await get_user_team_role(db, user.id, task.team_id)
    if not user_role:
        raise HTTPException(status_code=403, detail="You are not a member of this task's team")

    comment = TaskComment(
        content=comment_data.content,
        task_id=task_id,
        author_id=user.id
    )
    db.add(comment)
    await db.commit()
    await db.refresh(comment)

    result = await db.execute(
        select(TaskComment)
        .options(selectinload(TaskComment.author))
        .filter(TaskComment.id == comment.id)
    )
    comment_with_author = result.scalar_one()

    return TaskCommentRead(
        id=comment_with_author.id,
        content=comment_with_author.content,
        author=comment_with_author.author,
        created_at=comment_with_author.created_at
    )


@router.get("/{task_id}/comments", response_model=List[TaskCommentRead])
async def get_comments(
        task_id: int,
        user: User = Depends(current_active_user),
        db: AsyncSession = Depends(get_async_session)
):
    task = await get_task_by_id(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    user_role = await get_user_team_role(db, user.id, task.team_id)
    if not user_role:
        raise HTTPException(status_code=403, detail="You are not a member of this task's team")

    result = await db.execute(
        select(TaskComment)
        .options(selectinload(TaskComment.author))
        .filter(TaskComment.task_id == task_id)
        .order_by(TaskComment.created_at.asc())
    )
    comments = result.scalars().all()

    return [
        TaskCommentRead(
            id=comment.id,
            content=comment.content,
            author=comment.author,
            created_at=comment.created_at
        )
        for comment in comments
    ]