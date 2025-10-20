from fastapi import FastAPI
from fastapi.requests import Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.core.admin import setup_admin
from app.core.auth import current_active_user
from app.core.config import settings
from app.core.database import sync_engine, init_db, create_table
from app.core.templates import templates
from app.routers import auth, teams, tasks, evaluations, meetings, calendar, users

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION
)


@app.on_event("startup")
async def startup_event():
    await init_db()
    await create_table()


app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(auth.router)
app.include_router(teams.router)
app.include_router(tasks.router)
app.include_router(evaluations.router)
app.include_router(meetings.router)
app.include_router(calendar.router)
app.include_router(users.router)

admin = setup_admin(app)


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    try:
        user = await current_active_user(request)
        return templates.TemplateResponse("dashboard.html", {"request": request, "user": user})
    except:
        return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health")
async def health_check():
    try:
        with sync_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "OK", "database": "Connected"}
    except Exception as e:
        return {"status": "Error", "database": str(e)}
