"""住宿生活业务（PRD §3.4 L-001 ~ L-103）。"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ERR_DORM_CHANNEL_FORBIDDEN, AppError, not_found
from app.models.common import DormChannelScope, ReviewStatus
from app.models.living import (
    DormChannel,
    DormPost,
    DormReply,
    LostFound,
    SecondHand,
)
from app.models.user import User


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ── 频道可见性（L-001 ~ L-003）──


async def can_access_channel(db: AsyncSession, channel: DormChannel, user: User) -> bool:
    if channel.scope == DormChannelScope.ALL:
        return True
    if channel.scope == DormChannelScope.FLOOR:
        return (user.dorm_floor or "").strip() == (channel.floor or "").strip()
    if channel.scope == DormChannelScope.ROOM:
        return (user.dormitory or "").strip() == (channel.room or "").strip()
    return False


async def list_channels(db: AsyncSession, user: Optional[User]) -> List[dict]:
    rows = (
        await db.execute(
            select(DormChannel).where(DormChannel.is_active.is_(True)).order_by(DormChannel.id)
        )
    ).scalars().all()
    out = []
    for c in rows:
        visible = True if user is None else await can_access_channel(db, c, user)
        if not visible:
            continue
        out.append(
            {
                "id": c.id,
                "name": c.name,
                "scope": c.scope,
                "building": c.building,
                "floor": c.floor,
                "room": c.room,
            }
        )
    return out


async def create_post(db: AsyncSession, payload, user: User) -> DormPost:
    """L-004 发帖（≤3 图），过机审；L-006 举报由 report 接口触发。"""
    from app.services.moderation_service import assert_text_ok, moderate_ugc

    channel = await db.get(DormChannel, payload.channel_id)
    if channel is None:
        raise not_found("频道不存在")
    if not await can_access_channel(db, channel, user):
        raise AppError(ERR_DORM_CHANNEL_FORBIDDEN, "你没有权限在该频道发帖", 403)

    result = await moderate_ugc(db, payload.content)
    assert_text_ok(result)

    post = DormPost(
        channel_id=payload.channel_id,
        author_id=user.id,
        content=payload.content,
        images=json.dumps(payload.images, ensure_ascii=False) if payload.images else None,
        review_status=ReviewStatus.APPROVED if result.passed else ReviewStatus.PENDING,
        created_at=_now(),
    )
    db.add(post)
    await db.flush()
    return post


async def list_posts(
    db: AsyncSession, channel_id: int, user: Optional[User], offset: int = 0, limit: int = 20
) -> Tuple[List[dict], int]:
    channel = await db.get(DormChannel, channel_id)
    if channel is None:
        raise not_found("频道不存在")
    if user is None or not await can_access_channel(db, channel, user):
        raise AppError(ERR_DORM_CHANNEL_FORBIDDEN, "你没有权限访问该频道", 403)

    conds = [
        DormPost.channel_id == channel_id,
        DormPost.is_deleted.is_(False),
        DormPost.review_status == ReviewStatus.APPROVED,
    ]
    rows = (
        await db.execute(
            select(DormPost, User.nickname)
            .join(User, User.id == DormPost.author_id)
            .where(*conds)
            .order_by(desc(DormPost.created_at))
            .offset(offset)
            .limit(limit)
        )
    ).all()
    total = (await db.execute(select(func.count(DormPost.id)).where(*conds))).scalar() or 0
    items = [
        {
            "id": p.id,
            "channel_id": p.channel_id,
            "author_id": p.author_id,
            "author_nickname": nickname,
            "content": p.content,
            "images": p.images,
            "like_count": p.like_count,
            "reply_count": p.reply_count,
            "created_at": p.created_at,
            "liked_by_me": False,
        }
        for p, nickname in rows
    ]
    return items, total


async def reply_post(db: AsyncSession, post_id: int, content: str, user: User) -> DormReply:
    from app.services.moderation_service import assert_text_ok, moderate_ugc

    post = await db.get(DormPost, post_id)
    if post is None:
        raise not_found("帖子不存在")
    result = await moderate_ugc(db, content)
    assert_text_ok(result)

    r = DormReply(post_id=post_id, user_id=user.id, content=content, created_at=_now())
    db.add(r)
    post.reply_count = (post.reply_count or 0) + 1
    await db.flush()
    return r


async def list_replies(db: AsyncSession, post_id: int, limit: int = 50) -> List[dict]:
    rows = (
        await db.execute(
            select(DormReply, User.nickname)
            .join(User, User.id == DormReply.user_id)
            .where(DormReply.post_id == post_id)
            .order_by(DormReply.created_at)
            .limit(limit)
        )
    ).all()
    return [
        {
            "id": r.id,
            "post_id": r.post_id,
            "user_id": r.user_id,
            "author_nickname": nickname,
            "content": r.content,
            "created_at": r.created_at,
        }
        for r, nickname in rows
    ]


async def report_post(db: AsyncSession, post_id: int) -> None:
    """L-006 举报 → 触发人工审核。"""
    post = await db.get(DormPost, post_id)
    if post is None:
        raise not_found("帖子不存在")
    post.report_count = (post.report_count or 0) + 1
    if post.report_count >= 3:
        post.review_status = ReviewStatus.NEEDS_MANUAL
    await db.flush()


# ── 失物招领 / 二手交换 ──


async def create_lost_found(db: AsyncSession, payload, user: User) -> LostFound:
    item = LostFound(
        kind=payload.kind,
        title=payload.title,
        description=payload.description,
        location=payload.location,
        contact=payload.contact,
        images=json.dumps(payload.images, ensure_ascii=False) if payload.images else None,
        user_id=user.id,
        created_at=_now(),
        updated_at=_now(),
    )
    db.add(item)
    await db.flush()
    return item


async def list_lost_found(
    db: AsyncSession, kind=None, resolved: Optional[bool] = None, offset: int = 0, limit: int = 20
) -> Tuple[List[LostFound], int]:
    conds = [LostFound.is_deleted.is_(False)]
    if kind:
        conds.append(LostFound.kind == kind)
    if resolved is not None:
        conds.append(LostFound.is_resolved.is_(resolved))
    rows = (
        await db.execute(
            select(LostFound).where(*conds).order_by(desc(LostFound.created_at)).offset(offset).limit(limit)
        )
    ).scalars().all()
    total = (await db.execute(select(func.count(LostFound.id)).where(*conds))).scalar() or 0
    return list(rows), total


async def create_second_hand(db: AsyncSession, payload, user: User) -> SecondHand:
    item = SecondHand(
        title=payload.title,
        description=payload.description,
        price=payload.price,
        contact=payload.contact,
        images=json.dumps(payload.images, ensure_ascii=False) if payload.images else None,
        user_id=user.id,
        created_at=_now(),
        updated_at=_now(),
    )
    db.add(item)
    await db.flush()
    return item


async def list_second_hand(
    db: AsyncSession, sold: Optional[bool] = None, offset: int = 0, limit: int = 20
) -> Tuple[List[SecondHand], int]:
    conds = [SecondHand.is_deleted.is_(False)]
    if sold is not None:
        conds.append(SecondHand.is_sold.is_(sold))
    rows = (
        await db.execute(
            select(SecondHand).where(*conds).order_by(desc(SecondHand.created_at)).offset(offset).limit(limit)
        )
    ).scalars().all()
    total = (await db.execute(select(func.count(SecondHand.id)).where(*conds))).scalar() or 0
    return list(rows), total
