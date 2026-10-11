"""推送服务：极光推送 + 站内信双通道。

PRD §5 推送策略 + 技术架构文档 §7
静默期 22:00-07:00，每日 ≤5 条/用户。
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.redis import rate_limit
from app.models.common import PushType
from app.models.user import Notification, PushDevice, User

logger = logging.getLogger(__name__)

# 推送类型 → 用户偏好字段
_PREF_FIELD = {
    PushType.DAILY_POLL: "push_daily_poll",
    PushType.POLL_RESULT: "push_poll_result",
    PushType.EVENT_REMIND: "push_event_remind",
    PushType.CLUB_UPDATE: "push_club_update",
}


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def in_quiet_hours(dt: Optional[datetime] = None) -> bool:
    dt = dt or _now()
    h = dt.hour
    start, end = settings.PUSH_QUIET_HOURS_START, settings.PUSH_QUIET_HOURS_END
    if start > end:
        return h >= start or h < end
    return start <= h < end


def next_available_time(dt: Optional[datetime] = None) -> datetime:
    """静默期内延迟到 07:00 发出。"""
    dt = dt or _now()
    if not in_quiet_hours(dt):
        return dt
    nxt = dt.replace(hour=settings.PUSH_QUIET_HOURS_END, minute=0, second=0, microsecond=0)
    if nxt <= dt:
        nxt = nxt.replace(day=nxt.day + 1) if False else nxt
    return nxt


def user_allows(user: User, ptype: PushType) -> bool:
    field = _PREF_FIELD.get(ptype)
    if field is None:
        return True
    return bool(getattr(user, field, True))


async def within_daily_limit(user_id: int) -> bool:
    key = f"push:{user_id}:{_now().date().isoformat()}"
    return await rate_limit(key, settings.PUSH_DAILY_LIMIT, 86400)


async def send_push(
    db: AsyncSession,
    user: User,
    ptype: PushType,
    title: str,
    content: str = "",
    ref_type: Optional[str] = None,
    ref_id: Optional[int] = None,
) -> bool:
    """写站内信 + （可选）极光推送。返回是否发送。"""
    if in_quiet_hours():
        logger.info("推送处于静默期，延迟发送: user=%s type=%s", user.id, ptype.value)
        return False
    if not user_allows(user, ptype):
        return False
    if not await within_daily_limit(user.id):
        return False

    db.add(
        Notification(
            user_id=user.id,
            type=ptype,
            title=title,
            content=content,
            ref_type=ref_type,
            ref_id=ref_id,
            created_at=_now(),
        )
    )
    await db.flush()

    if settings.PUSH_ENABLED and settings.JPUSH_APP_KEY:
        await _jpush(user, title, content)
    return True


async def _jpush(user: User, title: str, content: str) -> None:
    """极光推送 REST API（未配置 Key 时静默跳过）。"""
    import base64

    import httpx

    devices = (
        await db_devices(user)
    )
    if not devices:
        return
    token = base64.b64encode(
        f"{settings.JPUSH_APP_KEY}:{settings.JPUSH_MASTER_SECRET}".encode()
    ).decode()
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            await client.post(
                "https://api.jpush.cn/v3/push",
                headers={"Authorization": f"Basic {token}"},
                json={
                    "platform": "all",
                    "audience": {"registration_id": devices},
                    "notification": {
                        "alert": title,
                        "ios": {"alert": {"title": title, "body": content}},
                        "android": {"alert": content, "title": title},
                    },
                    "options": {"apns_production": settings.is_production},
                },
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning("极光推送失败（已保留站内信）: %s", exc)


async def db_devices(user: User):
    """返回用户已绑定的 RegistrationID 列表。"""
    from app.core.database import SessionLocal

    async with SessionLocal() as s:
        rows = (
            await s.execute(
                select(PushDevice.registration_id).where(
                    PushDevice.user_id == user.id, PushDevice.is_active.is_(True)
                )
            )
        ).scalars().all()
    return list(rows)


async def notify_poll_published(db: AsyncSession, poll_id: int, title: str) -> int:
    """每日 18:00 新投票上线 → 全员推送。"""
    users = (
        await db.execute(select(User).where(User.is_active.is_(True)))
    ).scalars().all()
    n = 0
    for u in users:
        if await send_push(
            db,
            u,
            PushType.DAILY_POLL,
            "今日投票已上线",
            title,
            ref_type="vote",
            ref_id=poll_id,
        ):
            n += 1
    return n


async def notify_event_reminder(db: AsyncSession, event_id: int, title: str) -> int:
    """活动开始前 1 小时提醒已报名用户。"""
    from app.models.event import EventRegistration

    rows = (
        await db.execute(
            select(EventRegistration.user_id).where(
                EventRegistration.event_id == event_id,
                EventRegistration.is_waitlist.is_(False),
            )
        )
    ).scalars().all()
    n = 0
    for uid in rows:
        u = await db.get(User, uid)
        if u and await send_push(
            db, u, PushType.EVENT_REMIND, "活动即将开始", title, ref_type="event", ref_id=event_id
        ):
            n += 1
    return n


async def list_notifications(
    db: AsyncSession, user: User, unread_only: bool = False, offset: int = 0, limit: int = 20
):
    conds = [Notification.user_id == user.id]
    if unread_only:
        conds.append(Notification.is_read.is_(False))
    rows = (
        await db.execute(
            select(Notification)
            .where(*conds)
            .order_by(Notification.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
    ).scalars().all()
    total = (await db.execute(select(func.count(Notification.id)).where(*conds))).scalar() or 0
    return list(rows), total


async def mark_read(db: AsyncSession, user: User, notif_id: Optional[int] = None) -> int:
    from sqlalchemy import update

    conds = [Notification.user_id == user.id, Notification.is_read.is_(False)]
    if notif_id:
        conds.append(Notification.id == notif_id)
    res = await db.execute(update(Notification).where(*conds).values(is_read=True))
    await db.flush()
    return res.rowcount or 0
