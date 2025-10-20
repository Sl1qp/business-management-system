from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.meeting import Meeting, MeetingParticipant


async def get_meeting_by_id(db: AsyncSession, meeting_id: int):
    result = await db.execute(select(Meeting).filter(Meeting.id == meeting_id))
    return result.scalar_one_or_none()


async def is_meeting_organizer(db: AsyncSession, user_id: int, meeting_id: int):
    result = await db.execute(
        select(Meeting).filter(
            Meeting.id == meeting_id,
            Meeting.organizer_id == user_id
        )
    )
    return result.scalar_one_or_none() is not None


async def is_meeting_participant(db: AsyncSession, user_id: int, meeting_id: int):
    result = await db.execute(
        select(MeetingParticipant).filter(
            MeetingParticipant.meeting_id == meeting_id,
            MeetingParticipant.user_id == user_id
        )
    )
    return result.scalar_one_or_none() is not None
