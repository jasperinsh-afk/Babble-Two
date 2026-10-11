"""勋章接口（PRD §6 / U-006）。

GET /api/v1/badges         勋章墙（已获得 + 待解锁）
"""
from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import CurrentUser, Db, OptionalUser
from app.schemas.common import ApiResponse
from app.services import badge_service

router = APIRouter(prefix="/badges", tags=["勋章"])


@router.get("")
async def list_badges(db: Db, user: OptionalUser) -> ApiResponse:
    return ApiResponse.ok(await badge_service.list_badges(db, user.id if user else None))
