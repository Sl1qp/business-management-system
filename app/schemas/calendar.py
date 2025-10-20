from datetime import datetime
from enum import Enum
from typing import List, Dict, Any

from pydantic import BaseModel


class CalendarViewType(str, Enum):
    MONTH = "month"
    DAY = "day"


class CalendarEventType(str, Enum):
    TASK = "TASK"
    MEETING = "MEETING"


class CalendarResponse(BaseModel):
    events: List[Dict[str, Any]]
    view_type: CalendarViewType
    current_date: datetime
