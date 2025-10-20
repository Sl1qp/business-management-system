from fastapi import APIRouter, Depends
from fastapi.requests import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.core.auth import fastapi_users, auth_backend
from app.models.user import User
from app.schemas.user import UserRead, UserCreate, UserUpdate

router = APIRouter(prefix="/auth", tags=["auth"])
templates = Jinja2Templates(directory="app/templates")

router.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/jwt",
)
router.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="",
)
router.include_router(
    fastapi_users.get_reset_password_router(),
    prefix="",
)
router.include_router(
    fastapi_users.get_verify_router(UserRead),
    prefix="",
)
router.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
)


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("auth/login.html", {"request": request})


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("auth/register.html", {"request": request})


@router.get("/me", response_model=UserRead)
async def get_current_user(user: User = Depends(fastapi_users.current_user(active=True))):
    return user
