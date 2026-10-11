"""推送与站内信接口（PRD §5）。

POST /api/v1/push/devices     绑定推送设备（RegistrationID）
GET  /api/v1/push/settings     推送偏好
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.deps import CurrentUser, Db
from app.models.user import PushDevice
from app.schemas.common import ApiResponse

router = APIRouter(prefix="/push", tags=["推送"])


class DeviceIn(BaseModel):
    platform: str = Field(..., pattern="^(ios|android)$")
    registration_id: str = Field(..., min_length=1, max_length=200)


@router.post("/devices")
async def bind_device(payload: DeviceIn, db: Db, user: CurrentUser) -> ApiResponse:
    existing = (
        await db.execute(
            select(PushDevice).where(
                PushDevice.user_id == user.id,
                PushDevice.platform == payload.platform,
            )
        )
    ).scalars().first()
    if existing:
        existing.registration_id = payload.registration_id
        existing.is_active = True
    else:
        db.add(
            PushDevice(
                user_id=user.id,
                platform=payload.platform,
                registration_id=payload.registration_id,
                is_active=True,
                created_at=datetime.now(timezone.utc),
            )
        )
    await db.flush()
    return ApiResponse.ok({"bound": True}, "设备已绑定")


@router.get("/settings")
async def push_settings(user: CurrentUser) -> ApiResponse:
    return ApiResponse.ok(
        {
            "daily_poll": user.push_daily_poll,
            "poll_result": user.push_poll_result,
            "event_remind": user.push_event_remind,
            "club_update": user.push_club_update,
        }
    )
