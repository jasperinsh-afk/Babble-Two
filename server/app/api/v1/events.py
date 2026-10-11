"""活动日历接口（PRD §3.3）。

GET  /api/v1/events                活动列表
GET  /api/v1/events/calendar       日历数据（月视图）
POST /api/v1/events                发布活动（社团管理员/运营）
GET  /api/v1/events/{id}           活动详情
POST /api/v1/events/{id}/join      报名
DELETE /api/v1/events/{id}/join    取消报名
GET  /api/v1/events/me/cas         CAS 履历
"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, Db, OptionalUser
from app.core.exceptions import forbidden, not_found
from app.models.common import UserRole
from app.schemas.common import ApiResponse, Page
from app.schemas.event import EventCreateIn
from app.services import event_service

router = APIRouter(prefix="/events", tags=["活动日历"])


@router.get("")
async def list_events(
    db: Db,
    user: OptionalUser,
    start: datetime | None = None,
    end: datetime | None = None,
    club_id: int | None = None,
    offset: int = 0,
    limit: int = 20,
) -> ApiResponse[Page]:
    items, total = await event_service.list_events(
        db, user, start=start, end=end, club_id=club_id, offset=offset, limit=limit
    )
    return ApiResponse.ok(Page.build(items, total, offset, limit))


@router.get("/calendar")
async def calendar(
    db: Db,
    user: OptionalUser,
    year: int = Query(...),
    month: int = Query(..., ge=1, le=12),
) -> ApiResponse:
    return ApiResponse.ok(await event_service.get_calendar(db, user, year, month))


@router.post("")
async def create_event(payload: EventCreateIn, db: Db, user: CurrentUser) -> ApiResponse:
    if user.role not in (UserRole.CLUB_ADMIN, UserRole.OPERATOR, UserRole.ADMIN):
        raise forbidden("只有社团管理员或运营可以发布活动")
    ev = await event_service.create_event(db, payload, user)
    return ApiResponse.ok({"id": ev.id}, "活动已提交审核")


@router.get("/me/cas")
async def my_cas(db: Db, user: CurrentUser) -> ApiResponse:
    return ApiResponse.ok(await event_service.list_cas_records(db, user))


@router.get("/{event_id}")
async def event_detail(event_id: int, db: Db, user: OptionalUser) -> ApiResponse:
    from app.models.event import Event

    ev = await db.get(Event, event_id)
    if ev is None or ev.is_deleted:
        raise not_found("活动不存在")
    return ApiResponse.ok(await event_service._enrich(db, ev, user))


@router.post("/{event_id}/join")
async def join_event(event_id: int, db: Db, user: CurrentUser) -> ApiResponse:
    return ApiResponse.ok(await event_service.register_event(db, event_id, user), "报名成功")


@router.delete("/{event_id}/join")
async def cancel_event(event_id: int, db: Db, user: CurrentUser) -> ApiResponse:
    await event_service.cancel_registration(db, event_id, user)
    return ApiResponse.ok({"registered": False}, "已取消报名")
