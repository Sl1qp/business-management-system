from typing import AsyncGenerator

from fastapi import Depends
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from .config import settings

sync_engine = create_engine(
    settings.DATABASE_URL,
    echo=True,
)

async_engine = None
async_session_maker = None

Base = declarative_base()


async def init_db():
    print('Начат init_db')
    global async_engine, async_session_maker
    async_engine = create_async_engine(
        settings.DATABASE_URL.replace("postgresql", "postgresql+asyncpg"),
        echo=True,
        pool_pre_ping=True
    )
    async_session_maker = async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    print('End init_db')


async def create_table() -> bool:
    try:
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("Таблицы БД успешно созданы")
        return True
    except Exception as e:
        print(f"Ошибка при создании таблиц БД: {str(e)}")
        return False


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session


async def get_user_db(session: AsyncSession = Depends(get_async_session)):
    from app.models.user import User
    yield SQLAlchemyUserDatabase(session, User)
