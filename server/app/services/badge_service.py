"""勋章规则引擎（PRD §6 + U-006 勋章墙 + N-202 NFC 解锁）。"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.badge import BADGE_DEFS, Badge, UserBadge
from app.models.club import ClubMember
from app.models.event import EventRegistration
from app.models.nfc import NfcCheckin
from app.models.vote import Ballot, Comment

logger = logging.getLogger(__name__)


async def seed_badges(db: AsyncSession) -> None:
    """幂等写入 PRD §6 的 9 个勋章定义。"""
    for d in BADGE_DEFS:
        exists = (
            await db.execute(select(Badge).where(Badge.code == d["code"]))
        ).scalars().first()
        if exists:
            continue
        db.add(
            Badge(
                code=d["code"],
                name=d["name"],
                description=d["description"],
                rarity=d["rarity"],
                rule=json.dumps(d["rule"], ensure_ascii=False),
            )
        )
    await db.flush()


async def _grant(db: AsyncSession, user_id: int, badge_id: int) -> bool:
    exists = (
        await db.execute(
            select(UserBadge).where(
                UserBadge.user_id == user_id, UserBadge.badge_id == badge_id
            )
        )
    ).scalars().first()
    if exists:
        return False
    db.add(
        UserBadge(
            user_id=user_id, badge_id=badge_id, earned_at=datetime.now(timezone.utc)
        )
    )
    return True


async def _notify_badge(db: AsyncSession, user_id: int, badge_name: str) -> None:
    from app.models.common import PushType
    from app.models.user import Notification

    db.add(
        Notification(
            user_id=user_id,
            type=PushType.SYSTEM,
            title="解锁新勋章",
            content=f"恭喜获得勋章「{badge_name}」！",
            ref_type="badge",
            created_at=datetime.now(timezone.utc),
        )
    )


async def evaluate_user(db: AsyncSession, user_id: int) -> List[str]:
    """按规则引擎检查并解锁勋章，返回本次新解锁的勋章名。"""
    badges = (await db.execute(select(Badge))).scalars().all()
    owned = {
        r.badge_id
        for r in (
            await db.execute(select(UserBadge).where(UserBadge.user_id == user_id))
        ).scalars().all()
    }

    vote_count = (
        await db.execute(select(func.count(Ballot.id)).where(Ballot.user_id == user_id))
    ).scalar() or 0
    club_count = (
        await db.execute(
            select(func.count(ClubMember.club_id)).where(ClubMember.user_id == user_id)
        )
    ).scalar() or 0
    event_count = (
        await db.execute(
            select(func.count(EventRegistration.event_id)).where(
                EventRegistration.user_id == user_id
            )
        )
    ).scalar() or 0
    nfc_unique = (
        await db.execute(
            select(func.count(NfcCheckin.card_id)).where(NfcCheckin.user_id == user_id)
        )
    ).scalar() or 0
    max_comment_likes = (
        await db.execute(
            select(func.max(Comment.like_count)).where(Comment.user_id == user_id)
        )
    ).scalar() or 0
    vote_streak = await _vote_streak(db, user_id)
    early = await _is_early_user(db, user_id)

    counters = {
        "vote_count": vote_count,
        "club_count": club_count,
        "event_count": event_count,
        "nfc_unique": nfc_unique,
        "comment_likes": max_comment_likes,
        "vote_streak": vote_streak,
    }

    newly: List[str] = []
    for b in badges:
        if b.id in owned:
            continue
        try:
            rule = json.loads(b.rule) if b.rule else {}
        except json.JSONDecodeError:
            continue
        rtype = rule.get("type")

        if rtype == "register":
            ok = True
        elif rtype == "early_user":
            ok = early
        elif rtype in counters:
            ok = counters[rtype] >= int(rule.get("count", 1))
        else:
            ok = False

        if ok:
            if await _grant(db, user_id, b.id):
                await _notify_badge(db, user_id, b.name)
                newly.append(b.name)

    if newly:
        await db.flush()
    return newly


async def _vote_streak(db: AsyncSession, user_id: int) -> int:
    """连续每日投票天数（简化实现：统计最近 30 天有投票的不同日期连续性）。"""
    from datetime import timedelta

    rows = (
        await db.execute(
            select(Ballot.created_at).where(Ballot.user_id == user_id).order_by(Ballot.created_at.desc())
        )
    ).scalars().all()
    if not rows:
        return 0
    days = set()
    for r in rows:
        if r:
            days.add(r.date())
    streak = 0
    cur = datetime.now(timezone.utc).date()
    while cur in days:
        streak += 1
        cur -= timedelta(days=1)
    return streak


async def _is_early_user(db: AsyncSession, user_id: int) -> bool:
    from app.models.user import User

    total = (await db.execute(select(func.count(User.id)))).scalar() or 0
    return user_id <= 100 and total <= 10000


async def list_badges(db: AsyncSession, user_id: Optional[int] = None):
    """勋章墙（U-006）：展示已获得和待解锁。"""
    badges = (await db.execute(select(Badge))).scalars().all()
    owned_map = {}
    if user_id:
        rows = (
            await db.execute(select(UserBadge).where(UserBadge.user_id == user_id))
        ).scalars().all()
        owned_map = {r.badge_id: r.earned_at for r in rows}

    result = []
    for b in badges:
        result.append(
            {
                "badge": {
                    "id": b.id,
                    "code": b.code,
                    "name": b.name,
                    "description": b.description,
                    "icon_url": b.icon_url,
                    "rarity": b.rarity,
                },
                "earned_at": owned_map.get(b.id),
            }
        )
    return result
