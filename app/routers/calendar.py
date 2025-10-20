from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.requests import Request
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import current_active_user
from app.core.database import get_async_session
from app.core.templates import templates
from app.models.user import User
from app.schemas.calendar import CalendarResponse, CalendarViewType
from app.utils.calendar import get_user_calendar_events

router = APIRouter(prefix="/calendar", tags=["calendar"])


def month_name(month_num: int) -> str:
    months = [
        '',
        'Январь',
        'Февраль',
        'Март',
        'Апрель',
        'Май',
        'Июнь',
        'Июль',
        'Август',
        'Сентябрь',
        'Октябрь',
        'Ноябрь',
        'Декабрь'
    ]
    return months[month_num]


templates.env.filters["month_name"] = month_name


@router.get("", response_class=HTMLResponse)
async def calendar_page(
        request: Request,
        view: CalendarViewType = Query(CalendarViewType.MONTH, description="Вид календаря"),
        year: Optional[int] = Query(None, description="Год"),
        month: Optional[int] = Query(None, description="Месяц"),
        day: Optional[int] = Query(None, description="День"),
):
    return templates.TemplateResponse(
        "calendar/calendar.html",
        {
            "request": request,
            "view": view.value if view else CalendarViewType.MONTH.value,
            "year": year or datetime.now().year,
            "month": month or datetime.now().month,
            "day": day or datetime.now().day,
            "now": datetime.now(),
            "timedelta": timedelta
        }
    )


@router.get("/events", response_model=CalendarResponse)
async def get_calendar_events_api(
        start: datetime = Query(..., description="Начало периода"),
        end: datetime = Query(..., description="Конец периода"),
        view: CalendarViewType = Query(CalendarViewType.MONTH, description="Вид календаря"),
        user: User = Depends(current_active_user),
        db: AsyncSession = Depends(get_async_session)
):
    events = await get_user_calendar_events(db, user.id, start, end)

    return CalendarResponse(
        events=events,
        view_type=view,
        current_date=datetime.now()
    )
