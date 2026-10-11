"""OMEGA / NFC 接口（OMEGA 文档 §8.1）。

GET  /api/v1/nfc/{card_id}        卡片信息（App 端解析跳转目标）
POST /api/v1/nfc/tap              上报碰触事件
GET  /api/v1/nfc/me/checkins      我的打卡进度（N-201）
"""
from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import func, select

from app.api.deps import CurrentUser, Db, OptionalUser
from app.models.nfc import NfcCheckin
from app.schemas.common import ApiResponse
from app.schemas.nfc import NfcTapIn
from app.services import nfc_service

router = APIRouter(prefix="/nfc", tags=["OMEGA/NFC"])


@router.get("/me/checkins")
async def my_checkins(db: Db, user: CurrentUser) -> ApiResponse:
    rows = (
        await db.execute(
            select(NfcCheckin).where(NfcCheckin.user_id == user.id).order_by(
                NfcCheckin.first_tap_at.desc()
            )
        )
    ).scalars().all()
    unique = len(rows)
    total_taps = sum(r.tap_count or 0 for r in rows)
    return ApiResponse.ok(
        {
            "unique_cards": unique,
            "total_taps": total_taps,
            "cards": [
                {
                    "card_id": r.card_id,
                    "tap_count": r.tap_count,
                    "first_tap_at": r.first_tap_at,
                }
                for r in rows
            ],
        }
    )


@router.get("/{card_id}")
async def card_info(card_id: str, db: Db) -> ApiResponse:
    """N-002 / N-005：后端决定跳转目标，卡片不存业务逻辑。"""
    return ApiResponse.ok(await nfc_service.resolve_card(db, card_id))


@router.post("/tap")
async def record_tap(payload: NfcTapIn, db: Db, user: OptionalUser) -> ApiResponse:
    """N-103 碰触埋点 + N-201 打卡 + N-202 勋章解锁。"""
    result = await nfc_service.record_tap(
        db,
        payload.card_id,
        device_type=payload.device_type,
        app_installed=payload.app_installed,
        action_result="app_open" if payload.app_installed else "store_redirect",
        user=user,
    )
    return ApiResponse.ok(result, "打卡成功")


@router.get("/{card_id}/stats")
async def card_stats(card_id: str, db: Db) -> ApiResponse:
    return ApiResponse.ok(await nfc_service.card_stats(db, card_id))
