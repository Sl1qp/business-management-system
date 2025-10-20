from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.auth import current_active_user
from app.core.database import get_async_session
from app.models.user import User
from app.schemas.user import UserRead
from app.schemas.user_evalluations import User as UserSchema

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/", response_model=list[UserSchema])
async def get_users(
        skip: int = 0,
        limit: int = 100,
        session: AsyncSession = Depends(get_async_session),
        current_user: User = Depends(current_active_user)
):
    result = await session.execute(
        select(User)
        .offset(skip)
        .limit(limit)
    )
    users = result.scalars().all()
    return users


@router.get("/list", response_model=List[UserRead])
async def get_users_list(
        skip: int = 0,
        limit: int = 100,
        session: AsyncSession = Depends(get_async_session),
        current_user: User = Depends(current_active_user)
):
    result = await session.execute(
        select(User).offset(skip).limit(limit)
    )
    users = result.scalars().all()
    return users
