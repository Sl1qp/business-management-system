from typing import List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.requests import Request
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

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
    TeamMember,
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


@router.get("/list", response_model=List[TeamRead])
async def get_user_teams(
        user: User = Depends(current_active_user),
        db: AsyncSession = Depends(get_async_session)
):
    result = await db.execute(
        select(Team)
        .join(UserTeam)
        .filter(UserTeam.user_id == user.id)
    )
    teams = result.scalars().all()
    teams_with_members = []
    for team in teams:
        members_result = await db.execute(
            select(UserTeam, User)
            .join(User, UserTeam.user_id == User.id)
            .filter(UserTeam.team_id == team.id)
        )
        members_data = members_result.all()

        members = [
            TeamMember(
                user=member.User,
                role=member.UserTeam.role,
                created_at=member.UserTeam.created_at
            )
            for member in members_data
        ]

        team_dict = {
            "id": team.id,
            "name": team.name,
            "description": team.description,
            "invite_code": team.invite_code,
            "created_at": team.created_at,
            "updated_at": team.updated_at,
            "members": members
        }
        teams_with_members.append(team_dict)

    return teams_with_members


@router.get("", response_class=HTMLResponse)
async def teams_page(request: Request):
    return templates.TemplateResponse("teams/teams.html", {"request": request})


@router.post("", response_model=TeamRead)
async def create_team(
        team_data: TeamCreate,
        user: User = Depends(current_active_user),
        db: AsyncSession = Depends(get_async_session)
):
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
    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(Team)
        .options(selectinload(Team.members).selectinload(UserTeam.user))
        .where(Team.id == team.id)
    )
    team = result.scalar_one()
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
                "created_at": member.created_at
            }
            for member in team.members
        ]
    }

    return team_dict


@router.get("/{team_id}", response_model=TeamRead)
async def get_team(
        team_id: int,
        user: User = Depends(current_active_user),
        db: AsyncSession = Depends(get_async_session)
):
    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(Team)
        .options(selectinload(Team.members).selectinload(UserTeam.user))
        .where(Team.id == team_id)
    )
    team = result.scalar_one_or_none()

    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    user_role = await get_user_team_role(db, user.id, team_id)
    if not user_role:
        raise HTTPException(status_code=403, detail="Not a member of this team")
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
        user: User = Depends(current_active_user),
        db: AsyncSession = Depends(get_async_session)
):
    if not await is_team_admin(db, user.id, team_id):
        raise HTTPException(status_code=403, detail="Only team admin can update team")

    team = await get_team_by_id(db, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    if team_data.name is not None:
        team.name = team_data.name
    if team_data.description is not None:
        team.description = team_data.description

    await db.commit()
    await db.refresh(team)

    return team


@router.delete("/{team_id}")
async def delete_team(
        team_id: int,
        user: User = Depends(current_active_user),
        db: AsyncSession = Depends(get_async_session)
):
    if not await is_team_admin(db, user.id, team_id):
        raise HTTPException(status_code=403, detail="Only team admin can delete team")

    team = await get_team_by_id(db, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    await db.delete(team)
    await db.commit()

    return {"message": "Team deleted successfully"}


@router.get("/{team_id}/members", response_model=List[UserRead])
async def get_team_members(
        team_id: int,
        user: User = Depends(current_active_user),
        db: AsyncSession = Depends(get_async_session)
):
    user_team = await db.execute(
        select(UserTeam)
        .filter(UserTeam.team_id == team_id, UserTeam.user_id == user.id)
    )
    if not user_team.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Вы не являетесь участником этой команды")
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
        user: User = Depends(current_active_user),
        db: AsyncSession = Depends(get_async_session)
):
    if not await is_team_manager_or_admin(db, user.id, team_id):
        raise HTTPException(status_code=403, detail="Only team managers or admins can invite users")
    result = await db.execute(select(User).filter(User.email == invite_data.email))
    invited_user = result.scalar_one_or_none()

    if not invited_user:
        raise HTTPException(status_code=404, detail="User not found")
    existing_membership = await get_user_team_role(db, invited_user.id, team_id)
    if existing_membership:
        raise HTTPException(status_code=400, detail="User is already a member of this team")
    user_team = UserTeam(
        user_id=invited_user.id,
        team_id=team_id,
        role=invite_data.role
    )
    db.add(user_team)
    await db.commit()

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
    user_team = UserTeam(
        user_id=user.id,
        team_id=team.id,
        role="member"
    )
    db.add(user_team)
    await db.commit()

    return {"message": f"Joined team {team.name} successfully"}


@router.delete("/{team_id}/members/{user_id}")
async def remove_member(
        team_id: int,
        user_id: int,
        user: User = Depends(current_active_user),
        db: AsyncSession = Depends(get_async_session)
):
    if not await is_team_manager_or_admin(db, user.id, team_id):
        raise HTTPException(status_code=403, detail="Only team managers or admins can remove members")
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
    await db.delete(user_team)
    await db.commit()

    return {"message": "User removed from team successfully"}


@router.get("/{team_id}/invite-code")
async def get_invite_code(
        team_id: int,
        user: User = Depends(current_active_user),
        db: AsyncSession = Depends(get_async_session)
):
    if not await is_team_admin(db, user.id, team_id):
        raise HTTPException(status_code=403, detail="Only team admin can view invite code")

    result = await db.execute(select(Team).filter(Team.id == team_id))
    team = result.scalar_one_or_none()

    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    return {"invite_code": team.invite_code}
