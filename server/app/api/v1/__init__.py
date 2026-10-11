"""API v1 路由汇总。"""
from fastapi import APIRouter

from app.api.v1 import (
    admin,
    auth,
    badges,
    clubs,
    events,
    export,
    home,
    living,
    nfc,
    push,
    user,
    votes,
)

router = APIRouter()

router.include_router(auth.router, tags=["认证"])
router.include_router(user.router, tags=["个人中心"])
router.include_router(home.router, tags=["首页"])
router.include_router(votes.router, tags=["投票中心"])
router.include_router(clubs.router, tags=["社团广场"])
router.include_router(events.router, tags=["活动日历"])
router.include_router(living.router, tags=["住宿生活"])
router.include_router(nfc.router, tags=["OMEGA/NFC"])
router.include_router(badges.router, tags=["勋章"])
router.include_router(push.router, tags=["推送"])
router.include_router(admin.router, tags=["管理后台"])
router.include_router(export.router, tags=["墨麟书院·导出"])

__all__ = ["router"]
