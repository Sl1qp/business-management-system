from typing import List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.requests import Request
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.core.auth import current_active_user
from app.core.database import get_async_session
from app.core.templates import templates
from app.models.team import Team, UserTeam
from app.models.user import User
from app.schemas.team import (
    TeamCreate,
    TeamRead,
    TeamUpdate,
    InviteUserRequest,
    JoinTeamRequest,
)
from app.schemas.user import UserRead
from app.utils.teams import (
    generate_invite_code,
    get_team_by_id,
    is_team_admin,
    is_team_manager_or_admin,
    get_user_team_role,
)

router = APIRouter(prefix="/teams", tags=["teams"])


async def require_team_membership(
        team_id: int,
        user: User = Depends(current_active_user),
        db: AsyncSession = Depends(get_async_session)
):
    user_role = await get_user_team_role(db, user.id, team_id)
    if not user_role:
        raise HTTPException(status_code=403, detail="Not a member of this team")
    return user_role


async def require_team_admin(
        team_id: int,
        user: User = Depends(current_active_user),
        db: AsyncSession = Depends(get_async_session)
):
    if not await is_team_admin(db, user.id, team_id):
        raise HTTPException(status_code=403, detail="Only team admin can perform this action")
    return True


async def require_team_manager_or_admin_dep(
        team_id: int,
        user: User = Depends(current_active_user),
        db: AsyncSession = Depends(get_async_session)
):
    if not await is_team_manager_or_admin(db, user.id, team_id):
        raise HTTPException(status_code=403, detail="Only team managers or admins can perform this action")
    return True


async def get_team_with_members(
        team_id: int,
        db: AsyncSession = Depends(get_async_session)
) -> Team:
    result = await db.execute(
        select(Team)
        .options(selectinload(Team.members).selectinload(UserTeam.user))
        .where(Team.id == team_id)
    )
    team = result.scalar_one_or_none()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    return team


async def get_team_for_admin(
        team_id: int,
        user: User = Depends(current_active_user),
        db: AsyncSession = Depends(get_async_session)
) -> Team:
    team = await get_team_by_id(db, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    if not await is_team_admin(db, user.id, team_id):
        raise HTTPException(status_code=403, detail="Only team admin can perform this action")

    return team


@router.get("/list", response_model=List[TeamRead])
async def get_user_teams(
        user: User = Depends(current_active_user),
        db: AsyncSession = Depends(get_async_session)
):
    result = await db.execute(
        select(Team)
        .join(UserTeam, Team.id == UserTeam.team_id)
        .filter(UserTeam.user_id == user.id)
        .options(
            selectinload(Team.members)
            .selectinload(UserTeam.user)
        )
        .distinct()
    )

    teams = result.scalars().all()

    teams_read = []
    for team in teams:
        members_data = []
        for user_team in team.members:
            member_data = {
                "user": user_team.user,
                "role": user_team.role,
                "joined_at": user_team.created_at
            }
            members_data.append(member_data)

        team_read = TeamRead.model_validate({**team.__dict__, "members": members_data}, from_attributes=True)
        teams_read.append(team_read)

    return teams_read


@router.get("", response_class=HTMLResponse)
async def teams_page(request: Request):
    return templates.TemplateResponse("teams/teams.html", {"request": request})


@router.post("", response_model=TeamRead)
async def create_team(
        team_data: TeamCreate,
        user: User = Depends(current_active_user),
        db: AsyncSession = Depends(get_async_session)
):
    if user.role != "manager" and user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Только менеджеры могут создавать команды"
        )

    try:
        team = Team(
            name=team_data.name,
            description=team_data.description,
            invite_code=generate_invite_code()
        )
        db.add(team)
        await db.flush()

        user_team = UserTeam(
            user_id=user.id,
            team_id=team.id,
            role="admin"
        )
        db.add(user_team)
        await db.commit()

        await db.refresh(team)

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при создании команды: {str(e)}"
        )

    result = await db.execute(
        select(Team)
        .options(selectinload(Team.members).selectinload(UserTeam.user))
        .where(Team.id == team.id)
    )
    team = result.scalar_one()

    return TeamRead.model_validate(team, from_attributes=True)


@router.get("/{team_id}", response_model=TeamRead)
async def get_team(
        team: Team = Depends(get_team_with_members),
        user_role: str = Depends(require_team_membership),
):
    team_dict = {
        "id": team.id,
        "name": team.name,
        "description": team.description,
        "invite_code": team.invite_code,
        "created_at": team.created_at,
        "updated_at": team.updated_at,
        "members": [
            {
                "user": {
                    "id": member.user.id,
                    "email": member.user.email,
                    "first_name": member.user.first_name,
                    "last_name": member.user.last_name
                },
                "role": member.role,
                "joined_at": member.created_at
            }
            for member in team.members
        ]
    }

    return team_dict


@router.put("/{team_id}", response_model=TeamRead)
async def update_team(
        team_id: int,
        team_data: TeamUpdate,
        team: Team = Depends(get_team_for_admin),
        db: AsyncSession = Depends(get_async_session)
):
    try:
        if team_data.name is not None:
            team.name = team_data.name
        if team_data.description is not None:
            team.description = team_data.description

        await db.commit()
        await db.refresh(team)

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при обновлении команды: {str(e)}"
        )

    return team


@router.delete("/{team_id}")
async def delete_team(
        team: Team = Depends(get_team_for_admin),
        db: AsyncSession = Depends(get_async_session)
):
    try:
        await db.delete(team)
        await db.commit()

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при удалении команды: {str(e)}"
        )

    return {"message": "Team deleted successfully"}


@router.get("/{team_id}/members", response_model=List[UserRead])
async def get_team_members(
        team_id: int,
        _: str = Depends(require_team_membership),
        db: AsyncSession = Depends(get_async_session)
):
    result = await db.execute(
        select(User)
        .join(UserTeam, User.id == UserTeam.user_id)
        .filter(UserTeam.team_id == team_id)
    )
    members = result.scalars().all()
    return members


@router.post("/{team_id}/invite")
async def invite_user(
        team_id: int,
        invite_data: InviteUserRequest,
        _: bool = Depends(require_team_manager_or_admin_dep),
        db: AsyncSession = Depends(get_async_session)
):
    result = await db.execute(select(User).filter(User.email == invite_data.email))
    invited_user = result.scalar_one_or_none()

    if not invited_user:
        raise HTTPException(status_code=404, detail="User not found")

    existing_membership = await get_user_team_role(db, invited_user.id, team_id)
    if existing_membership:
        raise HTTPException(status_code=400, detail="User is already a member of this team")

    try:
        user_team = UserTeam(
            user_id=invited_user.id,
            team_id=team_id,
            role=invite_data.role
        )
        db.add(user_team)
        await db.commit()

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при приглашении пользователя: {str(e)}"
        )

    return {"message": f"User {invited_user.email} added to team as {invite_data.role}"}


@router.post("/join")
async def join_team(
        join_data: JoinTeamRequest,
        user: User = Depends(current_active_user),
        db: AsyncSession = Depends(get_async_session)
):
    result = await db.execute(select(Team).filter(Team.invite_code == join_data.invite_code))
    team = result.scalar_one_or_none()

    if not team:
        raise HTTPException(status_code=404, detail="Invalid invite code")

    existing_membership = await get_user_team_role(db, user.id, team.id)
    if existing_membership:
        raise HTTPException(status_code=400, detail="You are already a member of this team")

    try:
        user_team = UserTeam(
            user_id=user.id,
            team_id=team.id,
            role="member"
        )
        db.add(user_team)
        await db.commit()

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при присоединении к команде: {str(e)}"
        )

    return {"message": f"Joined team {team.name} successfully"}


@router.delete("/{team_id}/members/{user_id}")
async def remove_member(
        team_id: int,
        user_id: int,
        _: bool = Depends(require_team_manager_or_admin_dep),
        user: User = Depends(current_active_user),
        db: AsyncSession = Depends(get_async_session)
):
    if user.id == user_id:
        raise HTTPException(status_code=400, detail="Cannot remove yourself from team")

    result = await db.execute(
        select(UserTeam).filter(
            UserTeam.user_id == user_id,
            UserTeam.team_id == team_id
        )
    )
    user_team = result.scalar_one_or_none()

    if not user_team:
        raise HTTPException(status_code=404, detail="User is not a member of this team")

    try:
        await db.delete(user_team)
        await db.commit()

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при удалении участника из команды: {str(e)}"
        )

    return {"message": "User removed from team successfully"}


@router.get("/{team_id}/invite-code")
async def get_invite_code(
        team_id: int,
        _: bool = Depends(require_team_admin),
        db: AsyncSession = Depends(get_async_session)
):
    result = await db.execute(select(Team).filter(Team.id == team_id))
    team = result.scalar_one_or_none()

    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    return {"invite_code": team.invite_code}
