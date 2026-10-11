"""FastAPI 依赖注入：数据库会话、当前用户、角色校验。

技术架构文档 §3.3 —— 角色权限 student / club_admin / operator / admin
"""
from __future__ import annotations

from typing import Optional

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.database import get_db
from app.core.exceptions import forbidden, unauthorized
from app.core.security import decode_token, is_token_blacklisted
from app.models.common import ROLE_LEVEL, UserRole
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user_optional(
    request: Request,
    creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """未登录返回 None（访客可浏览公开内容，PRD §1.2 普通访客）。"""
    token = creds.credentials if creds else None
    if not token:
        token = request.query_params.get("access_token")
    if not token:
        return None

    payload = decode_token(token, expect_type="access")
    if await is_token_blacklisted(token):
        return None

    user = await db.get(User, int(payload["sub"]))
    if user is None or not user.is_active:
        return None
    return user


async def get_current_user(
    user: Optional[User] = Depends(get_current_user_optional),
) -> User:
    if user is None:
        raise unauthorized()
    return user


def require_role(min_role: UserRole):
    """角色门槛依赖。"""

    async def _dep(user: User = Depends(get_current_user)) -> User:
        if ROLE_LEVEL.get(user.role, 1) < ROLE_LEVEL[min_role]:
            raise forbidden("没有权限执行该操作")
        return user

    return _dep


# 语义化快捷依赖
require_student = require_role(UserRole.STUDENT)
require_club_admin = require_role(UserRole.CLUB_ADMIN)
require_operator = require_role(UserRole.OPERATOR)
require_admin = require_role(UserRole.ADMIN)


async def get_pagination(
    offset: int = 0, limit: int = settings.DEFAULT_PAGE_SIZE
) -> tuple[int, int]:
    limit = max(1, min(limit, settings.MAX_PAGE_SIZE))
    offset = max(0, offset)
    return offset, limit


__all__ = [
    "get_db",
    "get_current_user",
    "get_current_user_optional",
    "require_role",
    "require_student",
    "require_club_admin",
    "require_operator",
    "require_admin",
    "get_pagination",
]
