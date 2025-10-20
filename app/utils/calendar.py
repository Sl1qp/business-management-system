from datetime import datetime, timedelta
from typing import List, Dict, Any

from sqlalchemy import or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

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
        tasks_query = select(Task).filter(
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
        tasks = tasks_result.scalars().all()

        for task in tasks:
            event_date = task.deadline or task.created_at
            events.append({
                'id': f"task_{task.id}",
                'title': task.title,
                'description': task.description,
                'start_time': event_date,
                'end_time': event_date + timedelta(hours=1),
                'event_type': 'TASK',
                'all_day': task.deadline is not None,
                'status': task.status.value,
                'task_id': task.id,
                'url': f"/tasks/{task.id}",
                'color': get_task_color(task.status),
                'priority': 'medium'
            })

        meetings_query = select(Meeting).join(
            MeetingParticipant, Meeting.id == MeetingParticipant.meeting_id
        ).filter(
            MeetingParticipant.user_id == user_id,
            or_(
                Meeting.start_time.between(start_date, end_date),
                Meeting.end_time.between(start_date, end_date)
            )
        )

        meetings_result = await db.execute(meetings_query)
        meetings = meetings_result.scalars().all()

        for meeting in meetings:
            events.append({
                'id': f"meeting_{meeting.id}",
                'title': meeting.title,
                'description': meeting.description,
                'start_time': meeting.start_time,
                'end_time': meeting.end_time,
                'event_type': 'MEETING',
                'all_day': False,
                'meeting_id': meeting.id,
                'url': f"/meetings/{meeting.id}",
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
