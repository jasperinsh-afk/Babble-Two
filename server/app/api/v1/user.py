"""个人中心接口（PRD §3.7 U-001 ~ U-009）。

GET   /api/v1/users/me              个人信息
PUT   /api/v1/users/me              更新资料
PUT   /api/v1/users/me/push         推送偏好
GET   /api/v1/users/me/votes        我的投票
GET   /api/v1/users/me/clubs        我的社团
GET   /api/v1/users/me/events       我的活动
GET   /api/v1/users/me/cas          CAS 履历
DELETE /api/v1/users/me             注销账号（合规）
"""
from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import select

from app.api.deps import CurrentUser, Db
from app.models.club import Club, ClubMember
from app.models.vote import Ballot
from app.schemas.auth import NotificationOut, PushPrefIn, UserOut, UserUpdateIn
from app.schemas.common import ApiResponse, Page
from app.services import auth_service, event_service, push_service

router = APIRouter(prefix="/users", tags=["个人中心"])


@router.get("/me")
async def me(user: CurrentUser) -> ApiResponse:
    return ApiResponse.ok(UserOut.model_validate(user))


@router.put("/me")
async def update_me(payload: UserUpdateIn, db: Db, user: CurrentUser) -> ApiResponse:
    for field in ("nickname", "avatar_url", "bio", "grade", "dormitory"):
        val = getattr(payload, field, None)
        if val is not None:
            setattr(user, field, val)
    await db.flush()
    return ApiResponse.ok(UserOut.model_validate(user), "资料已更新")


@router.put("/me/push")
async def update_push(payload: PushPrefIn, db: Db, user: CurrentUser) -> ApiResponse:
    for field in (
        "push_daily_poll",
        "push_poll_result",
        "push_event_remind",
        "push_club_update",
    ):
        val = getattr(payload, field, None)
        if val is not None:
            setattr(user, field, val)
    await db.flush()
    return ApiResponse.ok({"updated": True}, "推送偏好已保存")


@router.get("/me/votes")
async def my_votes(db: Db, user: CurrentUser, offset: int = 0, limit: int = 20) -> ApiResponse:
    rows = (
        await db.execute(
            select(Ballot.poll_id).where(Ballot.user_id == user.id).offset(offset).limit(limit)
        )
    ).scalars().all()
    items = []
    for pid in rows:
        try:
            items.append(await _safe_poll(db, pid, user))
        except Exception:  # noqa: BLE001
            continue
    return ApiResponse.ok(Page.build(items, len(rows), offset, limit))


async def _safe_poll(db, pid, user):
    from app.services import vote_service

    return await vote_service.get_poll(db, pid, user)


@router.get("/me/clubs")
async def my_clubs(db: Db, user: CurrentUser) -> ApiResponse:
    rows = (
        await db.execute(
            select(Club, ClubMember.role)
            .join(ClubMember, ClubMember.club_id == Club.id)
            .where(ClubMember.user_id == user.id)
        )
    ).all()
    items = [
        {
            "id": c.id,
            "name": c.name,
            "logo_url": c.logo_url,
            "category": c.category,
            "is_verified": c.is_verified,
            "my_role": role,
        }
        for c, role in rows
    ]
    return ApiResponse.ok(items)


@router.get("/me/events")
async def my_events(db: Db, user: CurrentUser) -> ApiResponse:
    return ApiResponse.ok(await event_service.list_my_events(db, user))


@router.get("/me/cas")
async def my_cas(db: Db, user: CurrentUser) -> ApiResponse:
    return ApiResponse.ok(await event_service.list_cas_records(db, user))


@router.get("/me/notifications")
async def my_notifications(
    db: Db, user: CurrentUser, unread: bool = False, offset: int = 0, limit: int = 20
) -> ApiResponse:
    rows, total = await push_service.list_notifications(
        db, user, unread_only=unread, offset=offset, limit=limit
    )
    return ApiResponse.ok(
        Page.build([NotificationOut.model_validate(r) for r in rows], total, offset, limit)
    )


@router.post("/me/notifications/read")
async def read_notifications(
    db: Db, user: CurrentUser, notification_id: int | None = None
) -> ApiResponse:
    n = await push_service.mark_read(db, user, notification_id)
    return ApiResponse.ok({"updated": n}, "已标记已读")


@router.delete("/me")
async def delete_me(db: Db, user: CurrentUser) -> ApiResponse:
    """U-009 注销账号：清除个人数据，保留匿名化投票统计。"""
    await auth_service.delete_account(db, user)
    return ApiResponse.ok({"deleted": True}, "账号已注销")
