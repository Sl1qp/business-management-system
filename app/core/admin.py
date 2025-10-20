from sqladmin import Admin
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request

from app.core.database import sync_engine
from app.core.admin_models import (
    UserAdmin,
    TeamAdmin,
    UserTeamAdmin,
    TaskAdmin,
    TaskCommentAdmin,
    MeetingAdmin,
    MeetingParticipantAdmin,
    EvaluationAdmin,
)

class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        form = await request.form()
        username = form.get("username")
        password = form.get("password")

        if username == "admin" and password == "1234":
            request.session.update({"token": "admin-token"})
            return True
        return False

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        token = request.session.get("token")
        if token == "admin-token":
            return True
        return False


def setup_admin(app):
    admin = Admin(
        app,
        sync_engine,
        base_url="/admin",
        title="BMS Admin"
    )

    admin.add_view(UserAdmin)
    admin.add_view(TeamAdmin)
    admin.add_view(UserTeamAdmin)
    admin.add_view(TaskAdmin)
    admin.add_view(TaskCommentAdmin)
    admin.add_view(MeetingAdmin)
    admin.add_view(MeetingParticipantAdmin)
    admin.add_view(EvaluationAdmin)

    return admin
