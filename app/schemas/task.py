from datetime import datetime
from enum import Enum
from typing import List, Generic, TypeVar
from typing import Optional

from pydantic import BaseModel

from app.schemas.user import UserRead


class TaskStatus(str, Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"


class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.OPEN
    deadline: Optional[datetime] = None


class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    status: Optional[TaskStatus] = TaskStatus.OPEN
    deadline: Optional[datetime] = None
    assignee_id: Optional[int] = None
    team_id: int

    model_config = {
        'from_attributes': True,
        'json_encoders': {
            datetime: lambda v: v.isoformat() if v else None
        }
    }


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    deadline: Optional[datetime] = None
    assignee_id: Optional[int] = None


class TaskCommentBase(BaseModel):
    content: str


class TaskCommentCreate(TaskCommentBase):
    pass


class SimpleTeamRead(BaseModel):
    id: int
    name: str
    description: Optional[str] = None

    model_config = {
        'from_attributes': True,
    }


class TaskCommentRead(BaseModel):
    id: int
    content: str
    author: UserRead
    created_at: datetime

    model_config = {
        'from_attributes': True,
    }


class TaskRead(BaseModel):
    id: int
    title: str
    description: Optional[str]
    status: TaskStatus
    deadline: Optional[datetime]
    creator_id: int
    assignee_id: Optional[int]
    team_id: int
    created_at: datetime
    updated_at: datetime
    creator: Optional[UserRead] = None
    assignee: Optional[UserRead] = None
    team: Optional[SimpleTeamRead] = None
    comments: List[TaskCommentRead] = []

    model_config = {
        'from_attributes': True,
    }


T = TypeVar('T')


class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    page: int
    per_page: int
    total_count: int
    total_pages: int

    model_config = {
        'from_attributes': True,
    }
