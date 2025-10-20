from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from app.schemas.user import UserRead


class TeamBase(BaseModel):
    name: str
    description: Optional[str] = None


class TeamCreate(TeamBase):
    pass


class TeamUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class TeamMember(BaseModel):
    user: UserRead
    role: str
    created_at: datetime = Field(alias="joined_at")

    model_config = {
        'from_attributes': True,
        'populate_by_name': True
    }


class TeamRead(BaseModel):
    id: int
    name: str
    description: Optional[str]
    invite_code: str
    created_at: datetime
    updated_at: datetime
    members: List[TeamMember]

    model_config = {
        'from_attributes': True,
    }


class InviteUserRequest(BaseModel):
    email: str
    role: str = "member"

    @field_validator('role')
    def validate_role(cls, v):
        if v not in ['member', 'manager', 'admin']:
            raise ValueError('Role must be one of: member, manager, admin')
        return v


class JoinTeamRequest(BaseModel):
    invite_code: str


class TeamReadMeeting(BaseModel):
    id: int
    name: str
    description: Optional[str] = None

    model_config = {
        'from_attributes': True,
    }
