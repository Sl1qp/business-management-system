from datetime import datetime, timezone
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
from app.models import UserTeam
from app.models.meeting import Meeting, MeetingParticipant
from app.models.user import User
from app.schemas.meeting import MeetingCreate, MeetingRead, MeetingUpdate
from app.utils.teams import get_user_team_role

router = APIRouter(prefix="/meetings", tags=["meetings"])


def load_meeting_relationships(query):
    return query.options(
        selectinload(Meeting.organizer),
        selectinload(Meeting.team),
        selectinload(Meeting.participants).selectinload(MeetingParticipant.user)
    )


async def get_meeting_with_relations(
        meeting_id: int,
        db: AsyncSession = Depends(get_async_session)
) -> Meeting:
    result = await db.execute(
        load_meeting_relationships(select(Meeting).where(Meeting.id == meeting_id))
    )
    meeting = result.scalar_one_or_none()

    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    return meeting


async def require_team_membership_for_meeting(
        meeting: Meeting = Depends(get_meeting_with_relations),
        user: User = Depends(current_active_user),
        db: AsyncSession = Depends(get_async_session)
) -> Meeting:
    user_role = await get_user_team_role(db, user.id, meeting.team_id)
    if not user_role:
        raise HTTPException(status_code=403, detail="You are not a member of this meeting's team")

    return meeting


async def require_meeting_access(
        meeting: Meeting = Depends(require_team_membership_for_meeting),
        user: User = Depends(current_active_user)
) -> Meeting:
    is_participant = any(p.user_id == user.id for p in meeting.participants)
    if not is_participant:
        raise HTTPException(status_code=403, detail="You don't have access to this meeting")

    return meeting


async def require_meeting_organizer(
        meeting: Meeting = Depends(get_meeting_with_relations),
        user: User = Depends(current_active_user)
) -> Meeting:
    if meeting.organizer_id != user.id:
        raise HTTPException(status_code=403, detail="Only meeting organizer can update meeting")

    return meeting


async def require_meeting_organizer_or_admin(
        meeting: Meeting = Depends(get_meeting_with_relations),
        user: User = Depends(current_active_user),
        db: AsyncSession = Depends(get_async_session)
) -> Meeting:
    user_role = await get_user_team_role(db, user.id, meeting.team_id)
    is_organizer = meeting.organizer_id == user.id
    is_team_admin = user_role == 'admin'

    if not (is_organizer or is_team_admin):
        raise HTTPException(
            status_code=403,
            detail="Only meeting organizer or team admin can delete meeting"
        )

    return meeting


async def require_team_membership_for_team_id(
        team_id: int,
        user: User = Depends(current_active_user),
        db: AsyncSession = Depends(get_async_session)
):
    user_role = await get_user_team_role(db, user.id, team_id)
    if not user_role:
        raise HTTPException(status_code=403, detail="You are not a member of this team")
    return user_role


async def validate_participants_in_team(
        participant_ids: List[int],
        team_id: int,
        db: AsyncSession
) -> List[int]:
    if not participant_ids:
        return []

    participants_query = select(UserTeam.user_id).filter(
        UserTeam.team_id == team_id,
        UserTeam.user_id.in_(participant_ids)
    )
    participants_result = await db.execute(participants_query)
    valid_participant_ids = {row[0] for row in participants_result.all()}

    invalid_participants = set(participant_ids) - valid_participant_ids
    if invalid_participants:
        raise HTTPException(
            status_code=400,
            detail=f"Users {invalid_participants} are not members of this team"
        )

    return list(valid_participant_ids)


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
        query = load_meeting_relationships(
            select(Meeting)
            .join(MeetingParticipant, Meeting.id == MeetingParticipant.meeting_id)
            .filter(MeetingParticipant.user_id == user.id)
            .distinct()
        )

        now = datetime.now(timezone.utc).replace(tzinfo=None)
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

    valid_participant_ids = []
    if meeting_data.participant_ids:
        valid_participant_ids = await validate_participants_in_team(
            meeting_data.participant_ids, meeting_data.team_id, db
        )

    conflict_errors = await check_meeting_time_conflicts_optimized(
        db, meeting_data, user.id, valid_participant_ids
    )
    if conflict_errors:
        raise HTTPException(
            status_code=400,
            detail="Time conflicts detected: " + "; ".join(conflict_errors)
        )

    try:
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

        all_participant_ids = set(valid_participant_ids + [user.id])

        participants = [
            MeetingParticipant(meeting_id=meeting.id, user_id=participant_id)
            for participant_id in all_participant_ids
        ]
        db.add_all(participants)

        await db.commit()

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при создании встречи: {str(e)}"
        )

    result = await db.execute(
        load_meeting_relationships(select(Meeting).where(Meeting.id == meeting.id))
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
    result = await db.execute(
        load_meeting_relationships(select(Meeting).where(Meeting.id == meeting_id))
    )
    meeting = result.scalar_one_or_none()

    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    if meeting.organizer_id != user.id:
        raise HTTPException(status_code=403, detail="Only meeting organizer can update meeting")

    start_time = meeting_data.start_time if meeting_data.start_time is not None else meeting.start_time
    end_time = meeting_data.end_time if meeting_data.end_time is not None else meeting.end_time

    if end_time <= start_time:
        raise HTTPException(status_code=400, detail="End time must be after start time")

    current_participant_ids = [p.user_id for p in meeting.participants if p.user_id != meeting.organizer_id]
    participant_ids_to_check = current_participant_ids

    if meeting_data.participant_ids is not None:
        valid_participant_ids = await validate_participants_in_team(
            meeting_data.participant_ids, meeting.team_id, db
        )
        participant_ids_to_check = valid_participant_ids

    if meeting_data.start_time is not None or meeting_data.end_time is not None or meeting_data.participant_ids is not None:
        from app.schemas.meeting import MeetingCreate
        temp_meeting_data = MeetingCreate(
            title=meeting.title,
            description=meeting.description,
            start_time=start_time,
            end_time=end_time,
            team_id=meeting.team_id,
            participant_ids=participant_ids_to_check
        )

        conflict_errors = await check_meeting_time_conflicts_optimized(
            db, temp_meeting_data, user.id, participant_ids_to_check, exclude_meeting_id=meeting_id
        )
        if conflict_errors:
            raise HTTPException(
                status_code=400,
                detail="Time conflicts detected: " + "; ".join(conflict_errors)
            )

    try:
        if meeting_data.title is not None:
            meeting.title = meeting_data.title
        if meeting_data.description is not None:
            meeting.description = meeting_data.description
        if meeting_data.start_time is not None:
            meeting.start_time = meeting_data.start_time
        if meeting_data.end_time is not None:
            meeting.end_time = meeting_data.end_time

        if meeting_data.participant_ids is not None:
            await db.execute(
                MeetingParticipant.__table__.delete()
                .where(MeetingParticipant.meeting_id == meeting.id)
                .where(MeetingParticipant.user_id != meeting.organizer_id)
            )

            new_participants = [
                MeetingParticipant(meeting_id=meeting.id, user_id=participant_id)
                for participant_id in meeting_data.participant_ids
                if participant_id != meeting.organizer_id
            ]
            if new_participants:
                db.add_all(new_participants)

        meeting.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        await db.commit()

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при обновлении встречи: {str(e)}"
        )

    result = await db.execute(
        load_meeting_relationships(select(Meeting).where(Meeting.id == meeting_id))
    )
    updated_meeting = result.scalar_one()

    return updated_meeting


async def check_meeting_time_conflicts_optimized(
        db: AsyncSession,
        meeting_data: MeetingCreate,
        organizer_id: int,
        participant_ids: List[int],
        exclude_meeting_id: int = None
) -> List[str]:
    all_participants = set(participant_ids + [organizer_id])

    query = select(
        Meeting.title,
        Meeting.start_time,
        Meeting.end_time,
        MeetingParticipant.user_id,
        User.email
    ).join(
        MeetingParticipant, Meeting.id == MeetingParticipant.meeting_id
    ).join(
        User, MeetingParticipant.user_id == User.id
    ).filter(
        MeetingParticipant.user_id.in_(all_participants),
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
    conflicts = result.all()

    if not conflicts:
        return []

    conflicts_by_user = {}
    for title, start_time, end_time, user_id, email in conflicts:
        if user_id not in conflicts_by_user:
            conflicts_by_user[user_id] = {"email": email, "conflicts": []}
        start_str = start_time.strftime("%d.%m.%Y %H:%M")
        end_str = end_time.strftime("%d.%m.%Y %H:%M")
        conflicts_by_user[user_id]["conflicts"].append(f"{title} ({start_str} - {end_str})")

    errors = []
    for user_id, data in conflicts_by_user.items():
        conflicts_list = ", ".join(data["conflicts"])
        errors.append(f"User {data['email']} has conflicting meetings: {conflicts_list}")

    return errors


@router.get("/{meeting_id}", response_model=MeetingRead)
async def get_meeting(
        meeting: Meeting = Depends(get_meeting_with_relations),
        user: User = Depends(current_active_user),
        db: AsyncSession = Depends(get_async_session)
):
    is_participant = any(p.user_id == user.id for p in meeting.participants)
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
        .options(selectinload(Meeting.organizer), selectinload(Meeting.team))
        .where(Meeting.id == meeting_id)
    )
    meeting = result.scalar_one_or_none()

    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    user_role = await get_user_team_role(db, user.id, meeting.team_id)
    is_organizer = meeting.organizer_id == user.id
    is_team_admin = user_role == 'admin'

    if not (is_organizer or is_team_admin):
        raise HTTPException(
            status_code=403,
            detail="Only meeting organizer or team admin can delete meeting"
        )

    try:
        await db.execute(
            MeetingParticipant.__table__.delete()
            .where(MeetingParticipant.meeting_id == meeting.id)
        )

        await db.delete(meeting)
        await db.commit()

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при удалении встречи: {str(e)}"
        )

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
        load_meeting_relationships(
            select(Meeting)
            .filter(Meeting.team_id == team_id)
            .order_by(Meeting.start_time)
        )
    )
    meetings = result.scalars().all()

    return meetings


@router.get("/user/upcoming", response_model=List[MeetingRead])
async def get_upcoming_meetings(
        user: User = Depends(current_active_user),
        db: AsyncSession = Depends(get_async_session)
):
    result = await db.execute(
        load_meeting_relationships(
            select(Meeting)
            .join(MeetingParticipant, Meeting.id == MeetingParticipant.meeting_id)
            .filter(
                MeetingParticipant.user_id == user.id,
                Meeting.start_time >= datetime.now(timezone.utc).replace(tzinfo=None)
            )
            .order_by(Meeting.start_time)
        )
    )
    meetings = result.scalars().all()

    return meetings
