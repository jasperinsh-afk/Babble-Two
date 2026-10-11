"""限流：IP 级 + 用户级。

技术架构文档 §8.3 —— 刷票 / 注册机 / 恶意评论防御。
"""
from __future__ import annotations

from typing import Optional

from fastapi import Request

from app.core.exceptions import AppError, ERR_RATE_LIMITED
from app.core.redis import rate_limit


async def check_ip_limit(
    request: Request, scope: str, limit: int = 60, window: int = 60
) -> None:
    ip = request.client.host if request.client else "unknown"
    ok = await rate_limit(f"rate:{ip}:{scope}", limit, window)
    if not ok:
        raise AppError(ERR_RATE_LIMITED, "操作过于频繁，请稍后再试", 429)


async def check_user_limit(
    user_id: int, scope: str, limit: int = 30, window: int = 3600
) -> None:
    """用户级限流：如评论 10 条/小时。"""
    ok = await rate_limit(f"urate:{user_id}:{scope}", limit, window)
    if not ok:
        raise AppError(ERR_RATE_LIMITED, "操作过于频繁，请稍后再试", 429)


async def check_comment_limit(user_id: int) -> None:
    await check_user_limit(user_id, "comment", limit=10, window=3600)


async def check_register_limit(request: Request) -> None:
    await check_ip_limit(request, "register", limit=5, window=3600)


async def check_vote_limit(user_id: int) -> None:
    await check_user_limit(user_id, "vote", limit=60, window=3600)


def client_ip(request: Optional[Request]) -> str:
    if request is None or request.client is None:
        return "unknown"
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host
