"""API 层依赖快捷方式。"""
from __future__ import annotations

from typing import Annotated, Optional

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import (
    get_current_user,
    get_current_user_optional,
    require_admin,
    require_operator,
)
from app.core.rate_limit import check_ip_limit, check_register_limit
from app.models.user import User

Db = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalUser = Annotated[Optional[User], Depends(get_current_user_optional)]


OperatorUser = Annotated[User, Depends(require_operator)]
AdminUser = Annotated[User, Depends(require_admin)]


def require_operator_dep(user: OperatorUser) -> User:
    return user


def require_admin_dep(user: AdminUser) -> User:
    return user


async def rate_register(request: Request) -> None:
    await check_register_limit(request)


async def rate_default(request: Request) -> None:
    await check_ip_limit(request, "default", limit=120, window=60)


async def rate_sensitive(request: Request) -> None:
    await check_ip_limit(request, "sensitive", limit=20, window=60)


__all__ = [
    "Db",
    "CurrentUser",
    "OptionalUser",
    "OperatorUser",
    "AdminUser",
    "require_operator_dep",
    "require_admin_dep",
    "rate_register",
    "rate_default",
    "rate_sensitive",
]
