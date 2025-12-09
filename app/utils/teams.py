import secrets

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.team import Team, UserTeam


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
