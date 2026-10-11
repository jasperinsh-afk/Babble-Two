"""SQLAlchemy 2.0 异步数据库引擎与会话。

技术架构文档 §1.2 —— ORM: SQLAlchemy 2.0 / DB: PostgreSQL 15+
开发期可用 SQLite + aiosqlite 兜底，生产切 PostgreSQL + asyncpg。
"""
from __future__ import annotations

import os
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import StaticPool

from app.config import settings


class Base(DeclarativeBase):
    """ORM 基类。"""

    pass


def _build_engine():
    url = settings.DATABASE_URL
    kwargs = {"echo": settings.DB_ECHO, "future": True}

    if url.startswith("sqlite"):
        # SQLite: 确保目录存在；用 StaticPool 让内存/文件库共享连接，便于测试
        os.makedirs("data", exist_ok=True)
        kwargs["connect_args"] = {"check_same_thread": False}
        if ":memory:" in url:
            kwargs["poolclass"] = StaticPool
    else:
        kwargs["pool_size"] = 10
        kwargs["max_overflow"] = 20
        kwargs["pool_pre_ping"] = True

    return create_async_engine(url, **kwargs)


engine = _build_engine()

SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 依赖：请求级数据库会话。"""
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db(create_tables: bool = True) -> None:
    """建表（开发/测试用；生产走 Alembic 迁移）。"""
    from app import models  # noqa: F401  注册全部模型

    if create_tables:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)


async def drop_db() -> None:
    from app import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def close_db() -> None:
    await engine.dispose()
