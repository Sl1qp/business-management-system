from sqladmin import ModelView

from app.models.evaluation import Evaluation
from app.models.meeting import Meeting, MeetingParticipant
from app.models.task import Task, TaskComment
from app.models.team import Team, UserTeam
from app.models.user import User


class UserAdmin(ModelView, model=User):
    name = "Пользователь"
    name_plural = "Пользователи"
    icon = "fa-solid fa-user"

    column_list = [
        User.id,
        User.email,
        User.first_name,
        User.last_name,
        User.is_active,
        User.is_superuser,
        User.is_verified,
        User.created_at
    ]

    column_searchable_list = [User.email, User.first_name, User.last_name]

    form_columns = [
        'email', 'first_name', 'last_name',
        'is_active', 'is_superuser', 'is_verified'
    ]


class TeamAdmin(ModelView, model=Team):
    name = "Команда"
    name_plural = "Команды"
    icon = "fa-solid fa-users"

    column_list = [Team.id, Team.name, Team.description, Team.invite_code, Team.created_at]
    column_searchable_list = [Team.name]

    form_excluded_columns = [Team.members, Team.tasks, Team.meetings]


class UserTeamAdmin(ModelView, model=UserTeam):
    name = "Участник команды"
    name_plural = "Участники команд"
    icon = "fa-solid fa-user-plus"

    column_list = [UserTeam.id, UserTeam.user_id, UserTeam.team_id, UserTeam.role, UserTeam.created_at]


class TaskAdmin(ModelView, model=Task):
    name = "Задача"
    name_plural = "Задачи"
    icon = "fa-solid fa-tasks"

    column_list = [
        Task.id,
        Task.title,
        Task.status,
        Task.deadline,
        Task.creator_id,
        Task.assignee_id,
        Task.team_id,
        Task.created_at
    ]

    column_searchable_list = [Task.title]
    form_excluded_columns = [Task.comments, Task.evaluation]


class TaskCommentAdmin(ModelView, model=TaskComment):
    name = "Комментарий"
    name_plural = "Комментарии"
    icon = "fa-solid fa-comment"

    column_list = [
        TaskComment.id,
        TaskComment.content,
        TaskComment.task_id,
        TaskComment.author_id,
        TaskComment.created_at
    ]

    column_searchable_list = [TaskComment.content]


class MeetingAdmin(ModelView, model=Meeting):
    name = "Встреча"
    name_plural = "Встречи"
    icon = "fa-solid fa-calendar"

    column_list = [
        Meeting.id,
        Meeting.title,
        Meeting.start_time,
        Meeting.end_time,
        Meeting.organizer_id,
        Meeting.team_id,
        Meeting.created_at
    ]

    column_searchable_list = [Meeting.title]
    form_excluded_columns = [Meeting.participants]


class MeetingParticipantAdmin(ModelView, model=MeetingParticipant):
    name = "Участник встречи"
    name_plural = "Участники встреч"
    icon = "fa-solid fa-user-check"

    column_list = [
        MeetingParticipant.id,
        MeetingParticipant.meeting_id,
        MeetingParticipant.user_id,
        MeetingParticipant.created_at
    ]


class EvaluationAdmin(ModelView, model=Evaluation):
    name = "Оценка"
    name_plural = "Оценки"
    icon = "fa-solid fa-star"

    column_list = [
        Evaluation.id,
        Evaluation.rating,
        Evaluation.user_id,
        Evaluation.evaluator_id,
        Evaluation.task_id,
        Evaluation.created_at
    ]
