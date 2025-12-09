from datetime import datetime, timedelta
from typing import List, Dict, Any

from sqlalchemy import or_, and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.meeting import Meeting, MeetingParticipant
from app.models.task import Task, TaskStatus


async def get_user_calendar_events(
        db: AsyncSession,
        user_id: int,
        start_date: datetime,
        end_date: datetime
) -> List[Dict[str, Any]]:
    events = []

    try:
        from sqlalchemy.orm import aliased

        tasks_query = select(
            Task.id,
            Task.title,
            Task.description,
            Task.deadline,
            Task.created_at,
            Task.status
        ).filter(
            Task.assignee_id == user_id,
            or_(
                Task.deadline.between(start_date, end_date),
                and_(
                    Task.deadline.is_(None),
                    Task.created_at.between(start_date, end_date)
                )
            )
        )

        tasks_result = await db.execute(tasks_query)
        tasks = tasks_result.all()

        for task in tasks:
            task_id, title, description, deadline, created_at, status = task
            event_date = deadline or created_at
            events.append({
                'id': f"task_{task_id}",
                'title': title,
                'description': description,
                'start_time': event_date,
                'end_time': event_date + timedelta(hours=1),
                'event_type': 'TASK',
                'all_day': deadline is not None,
                'status': status.value,
                'task_id': task_id,
                'url': f"/tasks/{task_id}",
                'color': get_task_color(status),
                'priority': 'medium'
            })

        meetings_query = select(
            Meeting.id,
            Meeting.title,
            Meeting.description,
            Meeting.start_time,
            Meeting.end_time
        ).join(
            MeetingParticipant, Meeting.id == MeetingParticipant.meeting_id
        ).filter(
            MeetingParticipant.user_id == user_id,
            or_(
                Meeting.start_time.between(start_date, end_date),
                Meeting.end_time.between(start_date, end_date),
                and_(
                    Meeting.start_time <= start_date,
                    Meeting.end_time >= end_date
                )
            )
        ).distinct()

        meetings_result = await db.execute(meetings_query)
        meetings = meetings_result.all()

        for meeting in meetings:
            meeting_id, title, description, start_time, end_time = meeting
            events.append({
                'id': f"meeting_{meeting_id}",
                'title': title,
                'description': description,
                'start_time': start_time,
                'end_time': end_time,
                'event_type': 'MEETING',
                'all_day': False,
                'meeting_id': meeting_id,
                'url': f"/meetings/{meeting_id}",
                'color': '#3788d8',
                'priority': 'high'
            })

        return sorted(events, key=lambda x: x['start_time'])

    except Exception as e:
        print(f"Error in get_user_calendar_events: {str(e)}")
        return []


def get_task_color(status: TaskStatus) -> str:
    colors = {
        TaskStatus.OPEN: '#28a745',
        TaskStatus.IN_PROGRESS: '#ffc107',
        TaskStatus.COMPLETED: '#6c757d'
    }
    return colors.get(status, '#3788d8')


def generate_month_calendar_data(year: int, month: int, events: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
    first_day = datetime(year, month, 1)
    if month == 12:
        last_day = datetime(year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = datetime(year, month + 1, 1) - timedelta(days=1)

    calendar_start = first_day - timedelta(days=first_day.weekday())
    calendar_end = last_day + timedelta(days=6 - last_day.weekday())

    weeks = []
    current_day = calendar_start

    while current_day <= calendar_end:
        week = []
        for _ in range(7):
            day_events = [
                event for event in events
                if event['start_time'].date() == current_day.date()
            ]

            week.append({
                'date': current_day.date(),
                'day': current_day.day,
                'is_current_month': current_day.month == month,
                'is_today': current_day.date() == datetime.now().date(),
                'events': day_events[:3],
                'events_count': len(day_events)
            })
            current_day += timedelta(days=1)

        weeks.append(week)

    return weeks