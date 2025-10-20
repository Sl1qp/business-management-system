import secrets

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.team import Team, UserTeam
from app.models.user import User
from app.schemas.team import TeamRead, TeamMember
from app.schemas.user import UserRead


def generate_invite_code():
    return secrets.token_urlsafe(12)


async def get_team_by_id(db: AsyncSession, team_id: int):
    result = await db.execute(select(Team).filter(Team.id == team_id))
    return result.scalar_one_or_none()


async def get_user_team_role(db: AsyncSession, user_id: int, team_id: int):
    result = await db.execute(
        select(UserTeam).filter(
            UserTeam.user_id == user_id,
            UserTeam.team_id == team_id
        )
    )
    user_team = result.scalar_one_or_none()
    return user_team.role if user_team else None


async def is_team_admin(db: AsyncSession, user_id: int, team_id: int):
    role = await get_user_team_role(db, user_id, team_id)
    return role == 'admin'


async def is_team_manager_or_admin(db: AsyncSession, user_id: int, team_id: int):
    role = await get_user_team_role(db, user_id, team_id)
    return role in ['manager', 'admin']


async def get_team_members(db: AsyncSession, team_id: int):
    result = await db.execute(
        select(User, UserTeam.role, UserTeam.created_at)
        .join(UserTeam, UserTeam.user_id == User.id)
        .filter(UserTeam.team_id == team_id)
    )
    return result.all()


async def get_common_teams(db: AsyncSession, user1_id: int, user2_id: int):
    result = await db.execute(
        select(Team)
        .join(UserTeam, UserTeam.team_id == Team.id)
        .filter(
            UserTeam.user_id == user1_id,
            Team.id.in_(
                select(UserTeam.team_id)
                .filter(UserTeam.user_id == user2_id)
            )
        )
    )
    return result.scalars().all()


async def convert_team_to_team_read(db: AsyncSession, team: Team) -> TeamRead:
    result = await db.execute(
        select(UserTeam)
        .filter(UserTeam.team_id == team.id)
    )
    user_teams = result.scalars().all()

    members = []
    for user_team in user_teams:
        user_read = UserRead(
            id=user_team.user.id,
            email=user_team.user.email,
        )

        member = TeamMember(
            user=user_read,
            role=user_team.role,
            joined_at=user_team.created_at
        )
        members.append(member)

    return TeamRead(
        id=team.id,
        name=team.name,
        description=team.description,
        invite_code=team.invite_code,
        created_at=team.created_at,
        updated_at=team.updated_at,
        members=members
    )
