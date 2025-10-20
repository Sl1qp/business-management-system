from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from app.schemas.team import TeamReadMeeting
from app.schemas.user import UserRead


class MeetingBase(BaseModel):
    title: str
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    team_id: int


class MeetingCreate(MeetingBase):
    participant_ids: List[int] = []


class MeetingUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    participant_ids: Optional[List[int]] = None


class MeetingParticipantRead(BaseModel):
    user: UserRead
    created_at: datetime


class MeetingRead(MeetingBase):
    id: int
    organizer_id: int
    created_at: datetime
    updated_at: datetime

    organizer: Optional[UserRead] = None
    team: Optional[TeamReadMeeting] = None
    participants: List[MeetingParticipantRead] = []

    model_config = {
        'from_attributes': True,
    }
