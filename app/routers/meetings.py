from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.requests import Request
from starlette.responses import HTMLResponse

from app.core.auth import current_active_user
from app.core.database import get_async_session
from app.core.templates import templates
from app.models.meeting import Meeting, MeetingParticipant
from app.models.user import User
from app.schemas.meeting import MeetingCreate, MeetingRead, MeetingUpdate
from app.utils.meetings import get_meeting_by_id, is_meeting_organizer, is_meeting_participant
from app.utils.teams import get_user_team_role

router = APIRouter(prefix="/meetings", tags=["meetings"])


@router.get("", response_class=HTMLResponse)
async def meetings_page(
        request: Request,
        page: int = Query(1, ge=1, description="Номер страницы"),
        per_page: int = Query(10, ge=1, le=100, description="Элементов на странице")
):
    return templates.TemplateResponse(
        "meetings/meetings.html",
        {
            "request": request,
            "page": page,
            "per_page": per_page
        }
    )


@router.get("/list", response_model=List[MeetingRead])
async def get_meetings_list(
        filter: str = Query("all", description="Фильтр по времени"),
        user: User = Depends(current_active_user),
        db: AsyncSession = Depends(get_async_session)
):
    try:
        from sqlalchemy import distinct
        from datetime import datetime

        meeting_ids_query = select(distinct(MeetingParticipant.meeting_id)).filter(
            MeetingParticipant.user_id == user.id
        )

        meeting_ids_result = await db.execute(meeting_ids_query)
        meeting_ids = meeting_ids_result.scalars().all()

        if not meeting_ids:
            return []

        query = select(Meeting).options(
            selectinload(Meeting.organizer),
            selectinload(Meeting.team),
            selectinload(Meeting.participants).selectinload(MeetingParticipant.user)
        ).filter(Meeting.id.in_(meeting_ids))

        now = datetime.utcnow()
        if filter == "upcoming":
            query = query.filter(Meeting.start_time >= now)
        elif filter == "past":
            query = query.filter(Meeting.end_time < now)

        query = query.order_by(Meeting.start_time)

        result = await db.execute(query)
        meetings = result.scalars().all()
        return meetings
    except Exception as e:
        print(f"Error in get_meetings_list: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("", response_model=MeetingRead)
async def create_meeting(
        meeting_data: MeetingCreate,
        user: User = Depends(current_active_user),
        db: AsyncSession = Depends(get_async_session)
):
    user_role = await get_user_team_role(db, user.id, meeting_data.team_id)
    if not user_role:
        raise HTTPException(status_code=403, detail="You are not a member of this team")

    if meeting_data.end_time <= meeting_data.start_time:
        raise HTTPException(status_code=400, detail="End time must be after start time")

    for participant_id in meeting_data.participant_ids:
        participant_role = await get_user_team_role(db, participant_id, meeting_data.team_id)
        if not participant_role:
            raise HTTPException(status_code=400, detail=f"User {participant_id} is not a member of this team")

    conflict_errors = await check_meeting_time_conflicts(
        db, meeting_data, user.id, meeting_data.participant_ids
    )
    if conflict_errors:
        raise HTTPException(
            status_code=400,
            detail="Time conflicts detected: " + "; ".join(conflict_errors)
        )

    meeting = Meeting(
        title=meeting_data.title,
        description=meeting_data.description,
        start_time=meeting_data.start_time,
        end_time=meeting_data.end_time,
        team_id=meeting_data.team_id,
        organizer_id=user.id
    )

    db.add(meeting)
    await db.flush()

    for participant_id in meeting_data.participant_ids:
        participant = MeetingParticipant(
            meeting_id=meeting.id,
            user_id=participant_id
        )
        db.add(participant)

    organizer_participant = MeetingParticipant(
        meeting_id=meeting.id,
        user_id=user.id
    )
    db.add(organizer_participant)

    await db.commit()

    result = await db.execute(
        select(Meeting)
        .options(
            selectinload(Meeting.organizer),
            selectinload(Meeting.team),
            selectinload(Meeting.participants).selectinload(MeetingParticipant.user)
        )
        .where(Meeting.id == meeting.id)
    )
    meeting_with_relations = result.scalar_one()

    return meeting_with_relations


@router.put("/{meeting_id}", response_model=MeetingRead)
async def update_meeting(
        meeting_id: int,
        meeting_data: MeetingUpdate,
        user: User = Depends(current_active_user),
        db: AsyncSession = Depends(get_async_session)
):
    if not await is_meeting_organizer(db, user.id, meeting_id):
        raise HTTPException(status_code=403, detail="Only meeting organizer can update meeting")

    meeting = await get_meeting_by_id(db, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    if meeting_data.title is not None:
        meeting.title = meeting_data.title
    if meeting_data.description is not None:
        meeting.description = meeting_data.description

    start_time = meeting_data.start_time if meeting_data.start_time is not None else meeting.start_time
    end_time = meeting_data.end_time if meeting_data.end_time is not None else meeting.end_time

    if meeting_data.start_time is not None:
        meeting.start_time = meeting_data.start_time
    if meeting_data.end_time is not None:
        meeting.end_time = meeting_data.end_time

    if meeting.end_time <= meeting.start_time:
        raise HTTPException(status_code=400, detail="End time must be after start time")

    current_participants_result = await db.execute(
        select(MeetingParticipant.user_id)
        .filter(MeetingParticipant.meeting_id == meeting_id)
    )
    current_participant_ids = [row[0] for row in current_participants_result.all()]

    participant_ids_to_check = current_participant_ids
    if meeting_data.participant_ids is not None:
        participant_ids_to_check = meeting_data.participant_ids + [user.id]

    if meeting_data.start_time is not None or meeting_data.end_time is not None or meeting_data.participant_ids is not None:
        conflict_errors = await check_meeting_time_conflicts(
            db, meeting_data, user.id, participant_ids_to_check, exclude_meeting_id=meeting_id
        )
        if conflict_errors:
            raise HTTPException(
                status_code=400,
                detail="Time conflicts detected: " + "; ".join(conflict_errors)
            )

    if meeting_data.participant_ids is not None:
        await db.execute(
            MeetingParticipant.__table__.delete()
            .where(MeetingParticipant.meeting_id == meeting_id)
            .where(MeetingParticipant.user_id != user.id)
        )

        for participant_id in meeting_data.participant_ids:
            if participant_id == user.id:
                continue

            participant = MeetingParticipant(
                meeting_id=meeting_id,
                user_id=participant_id
            )
            db.add(participant)

    meeting.updated_at = datetime.utcnow()
    await db.commit()

    result = await db.execute(
        select(Meeting)
        .options(
            selectinload(Meeting.organizer),
            selectinload(Meeting.team),
            selectinload(Meeting.participants).selectinload(MeetingParticipant.user)
        )
        .where(Meeting.id == meeting_id)
    )
    updated_meeting = result.scalar_one()

    return updated_meeting


async def check_meeting_time_conflicts(
        db: AsyncSession,
        meeting_data: MeetingCreate,
        organizer_id: int,
        participant_ids: List[int],
        exclude_meeting_id: int = None
) -> List[str]:
    errors = []

    all_participants = set(participant_ids + [organizer_id])

    for participant_id in all_participants:
        query = select(Meeting).join(
            MeetingParticipant, Meeting.id == MeetingParticipant.meeting_id
        ).filter(
            MeetingParticipant.user_id == participant_id,
            or_(
                and_(
                    Meeting.start_time <= meeting_data.start_time,
                    Meeting.end_time > meeting_data.start_time
                ),
                and_(
                    Meeting.start_time < meeting_data.end_time,
                    Meeting.end_time >= meeting_data.end_time
                ),
                and_(
                    Meeting.start_time >= meeting_data.start_time,
                    Meeting.end_time <= meeting_data.end_time
                ),
                and_(
                    Meeting.start_time <= meeting_data.start_time,
                    Meeting.end_time >= meeting_data.end_time
                )
            )
        )

        if exclude_meeting_id:
            query = query.filter(Meeting.id != exclude_meeting_id)

        result = await db.execute(query)
        conflicting_meetings = result.scalars().all()

        if conflicting_meetings:
            user_result = await db.execute(
                select(User).filter(User.id == participant_id)
            )
            user = user_result.scalar_one()

            conflict_times = []
            for conflict in conflicting_meetings:
                start_str = conflict.start_time.strftime("%d.%m.%Y %H:%M")
                end_str = conflict.end_time.strftime("%d.%m.%Y %H:%M")
                conflict_times.append(f"{conflict.title} ({start_str} - {end_str})")

            errors.append(
                f"User {user.email} has conflicting meetings: {', '.join(conflict_times)}"
            )

    return errors


@router.get("/{meeting_id}", response_model=MeetingRead)
async def get_meeting(
        meeting_id: int,
        user: User = Depends(current_active_user),
        db: AsyncSession = Depends(get_async_session)
):
    result = await db.execute(
        select(Meeting)
        .options(
            selectinload(Meeting.organizer),
            selectinload(Meeting.team),
            selectinload(Meeting.participants).selectinload(MeetingParticipant.user)
        )
        .where(Meeting.id == meeting_id)
    )
    meeting = result.scalar_one_or_none()

    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    is_participant = await is_meeting_participant(db, user.id, meeting_id)
    user_role = await get_user_team_role(db, user.id, meeting.team_id)

    if not is_participant and not user_role:
        raise HTTPException(status_code=403, detail="You don't have access to this meeting")

    return meeting


@router.delete("/{meeting_id}")
async def delete_meeting(
        meeting_id: int,
        user: User = Depends(current_active_user),
        db: AsyncSession = Depends(get_async_session)
):
    result = await db.execute(
        select(Meeting)
        .options(
            selectinload(Meeting.organizer),
            selectinload(Meeting.team)
        )
        .where(Meeting.id == meeting_id)
    )
    meeting = result.scalar_one_or_none()

    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    is_organizer = meeting.organizer_id == user.id
    user_role = await get_user_team_role(db, user.id, meeting.team_id)
    is_team_admin = user_role == 'admin'

    if not (is_organizer or is_team_admin):
        raise HTTPException(
            status_code=403,
            detail="Only meeting organizer or team admin can delete meeting"
        )

    await db.execute(
        MeetingParticipant.__table__.delete()
        .where(MeetingParticipant.meeting_id == meeting_id)
    )

    await db.delete(meeting)
    await db.commit()

    return {"message": "Meeting deleted successfully"}


@router.get("/team/{team_id}", response_model=List[MeetingRead])
async def get_team_meetings(
        team_id: int,
        user: User = Depends(current_active_user),
        db: AsyncSession = Depends(get_async_session)
):
    user_role = await get_user_team_role(db, user.id, team_id)
    if not user_role:
        raise HTTPException(status_code=403, detail="You are not a member of this team")

    result = await db.execute(
        select(Meeting)
        .options(
            selectinload(Meeting.organizer),
            selectinload(Meeting.team),
            selectinload(Meeting.participants).selectinload(MeetingParticipant.user)
        )
        .filter(Meeting.team_id == team_id)
        .order_by(Meeting.start_time)
    )
    meetings = result.scalars().all()

    return meetings


@router.get("/user/upcoming", response_model=List[MeetingRead])
async def get_upcoming_meetings(
        user: User = Depends(current_active_user),
        db: AsyncSession = Depends(get_async_session)
):
    result = await db.execute(
        select(Meeting)
        .join(MeetingParticipant, Meeting.id == MeetingParticipant.meeting_id)
        .options(
            selectinload(Meeting.organizer),
            selectinload(Meeting.team),
            selectinload(Meeting.participants).selectinload(MeetingParticipant.user)
        )
        .filter(
            MeetingParticipant.user_id == user.id,
            Meeting.start_time >= datetime.utcnow()
        )
        .order_by(Meeting.start_time)
    )
    meetings = result.scalars().all()

    return meetings
