"""社团广场业务（PRD §3.2 C-001 ~ C-204）。"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    ERR_CLUB_APPLY_EXISTS,
    ERR_CLUB_NOT_VERIFIED,
    ERR_NOT_CLUB_ADMIN,
    ERR_PIN_LIMIT,
    AppError,
    not_found,
)
from app.models.club import Club, ClubMember, Post, PostComment
from app.models.common import ReviewStatus
from app.models.user import User

logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def apply_club(db: AsyncSession, payload, user: User) -> Club:
    """C-001 入驻申请 → C-002 运营审核 → C-003 通过后自动建主页。"""
    exists = (
        await db.execute(
            select(Club).where(
                Club.name == payload.name, Club.review_status != ReviewStatus.REJECTED
            )
        )
    ).scalars().first()
    if exists:
        raise AppError(ERR_CLUB_APPLY_EXISTS, "该社团名已存在或已有待审核申请", 400)

    club = Club(
        name=payload.name,
        description=payload.description,
        logo_url=payload.logo_url,
        category=payload.category,
        is_verified=False,
        review_status=ReviewStatus.PENDING,
        owner_id=user.id,
        member_count=1,
        created_at=_now(),
        updated_at=_now(),
    )
    db.add(club)
    await db.flush()
    db.add(
        ClubMember(
            club_id=club.id, user_id=user.id, role="admin", joined_at=_now()
        )
    )
    await db.flush()
    return club


async def review_club(db: AsyncSession, club_id: int, approved: bool, note: str = "") -> Club:
    club = await db.get(Club, club_id)
    if club is None:
        raise not_found("社团不存在")
    club.review_status = ReviewStatus.APPROVED if approved else ReviewStatus.REJECTED
    club.review_note = note
    club.is_verified = approved  # C-005 认证标识
    club.updated_at = _now()
    await db.flush()
    return club


async def list_clubs(
    db: AsyncSession,
    user: Optional[User],
    category=None,
    keyword: str = "",
    sort: str = "heat",
    offset: int = 0,
    limit: int = 20,
) -> Tuple[List[dict], int]:
    conds = [Club.is_deleted.is_(False), Club.review_status == ReviewStatus.APPROVED]
    if category:
        conds.append(Club.category == category)
    if keyword:
        conds.append(or_(Club.name.like(f"%{keyword}%"), Club.description.like(f"%{keyword}%")))

    order = desc(Club.heat_score) if sort == "heat" else desc(Club.created_at)
    rows = (await db.execute(select(Club).where(*conds).order_by(order).offset(offset).limit(limit))).scalars().all()
    total = (await db.execute(select(func.count(Club.id)).where(*conds))).scalar() or 0

    member_ids = set()
    if user:
        member_ids = {
            r.club_id
            for r in (
                await db.execute(select(ClubMember).where(ClubMember.user_id == user.id))
            ).scalars().all()
        }

    items = []
    for c in rows:
        items.append(
            {
                "id": c.id,
                "name": c.name,
                "description": c.description,
                "logo_url": c.logo_url,
                "cover_url": c.cover_url,
                "category": c.category,
                "is_verified": c.is_verified,
                "member_count": c.member_count,
                "follower_count": c.follower_count,
                "heat_score": c.heat_score,
                "is_member": c.id in member_ids,
                "is_following": c.id in member_ids,
            }
        )
    return items, total


async def get_club(db: AsyncSession, club_id: int, user: Optional[User]) -> dict:
    club = await db.get(Club, club_id)
    if club is None or club.is_deleted:
        raise not_found("社团不存在")
    my_role = None
    if user:
        m = await db.get(ClubMember, (club_id, user.id))
        my_role = m.role if m else None
    return {
        "id": club.id,
        "name": club.name,
        "description": club.description,
        "logo_url": club.logo_url,
        "cover_url": club.cover_url,
        "category": club.category,
        "is_verified": club.is_verified,
        "member_count": club.member_count,
        "follower_count": club.follower_count,
        "heat_score": club.heat_score,
        "review_status": club.review_status.value if club.review_status else None,
        "my_role": my_role,
        "is_member": my_role is not None,
        "is_following": my_role is not None,
        "created_at": club.created_at,
    }


async def join_club(db: AsyncSession, club_id: int, user: User) -> None:
    club = await db.get(Club, club_id)
    if club is None or club.review_status != ReviewStatus.APPROVED:
        raise AppError(ERR_CLUB_NOT_VERIFIED, "社团尚未通过认证", 400)
    m = await db.get(ClubMember, (club_id, user.id))
    if m:
        return
    db.add(ClubMember(club_id=club_id, user_id=user.id, role="member", joined_at=_now()))
    club.member_count = (club.member_count or 0) + 1
    club.heat_score = (club.heat_score or 0) + 5
    await db.flush()

    from app.services.badge_service import evaluate_user

    await evaluate_user(db, user.id)


async def leave_club(db: AsyncSession, club_id: int, user: User) -> None:
    m = await db.get(ClubMember, (club_id, user.id))
    if not m:
        return
    await db.delete(m)
    club = await db.get(Club, club_id)
    if club:
        club.member_count = max(0, (club.member_count or 1) - 1)
    await db.flush()


async def is_club_admin(db: AsyncSession, club_id: int, user: User) -> bool:
    if user.role.value in ("operator", "admin"):
        return True
    m = await db.get(ClubMember, (club_id, user.id))
    return m is not None and m.role == "admin"


async def create_post(db: AsyncSession, club_id: int, payload, user: User) -> Post:
    """C-101 ~ C-103：发布图文 → 进入审核队列（机审 + 人工）。"""
    from app.services.moderation_service import assert_text_ok, moderate_ugc

    if not await is_club_admin(db, club_id, user):
        raise AppError(ERR_NOT_CLUB_ADMIN, "你不是该社团管理员", 403)

    text = f"{payload.title or ''} {payload.content}"
    result = await moderate_ugc(db, text)
    assert_text_ok(result)

    if payload.is_pinned:
        pinned = (
            await db.execute(
                select(func.count(Post.id)).where(Post.club_id == club_id, Post.is_pinned.is_(True))
            )
        ).scalar() or 0
        if pinned >= 1:
            raise AppError(ERR_PIN_LIMIT, "每个社团最多置顶 1 条", 400)

    post = Post(
        club_id=club_id,
        author_id=user.id,
        title=payload.title,
        content=payload.content,
        images=json.dumps(payload.images, ensure_ascii=False) if payload.images else None,
        status=ReviewStatus.APPROVED if result.passed and result.status != ReviewStatus.NEEDS_MANUAL else ReviewStatus.PENDING,
        is_pinned=payload.is_pinned,
        created_at=_now(),
    )
    db.add(post)
    await db.flush()

    club = await db.get(Club, club_id)
    if club:
        club.heat_score = (club.heat_score or 0) + 10
    return post


async def list_posts(
    db: AsyncSession, club_id: Optional[int], user: Optional[User], offset: int = 0, limit: int = 20
) -> Tuple[List[dict], int]:
    conds = [Post.status == ReviewStatus.APPROVED]
    if club_id:
        conds.append(Post.club_id == club_id)
    rows = (
        await db.execute(
            select(Post, Club.name, User.nickname)
            .join(Club, Club.id == Post.club_id)
            .join(User, User.id == Post.author_id)
            .where(*conds)
            .order_by(Post.is_pinned.desc(), desc(Post.created_at))
            .offset(offset)
            .limit(limit)
        )
    ).all()
    total = (await db.execute(select(func.count(Post.id)).where(*conds))).scalar() or 0

    items = []
    for p, club_name, nickname in rows:
        items.append(
            {
                "id": p.id,
                "club_id": p.club_id,
                "club_name": club_name,
                "author_id": p.author_id,
                "author_nickname": nickname,
                "title": p.title,
                "content": p.content,
                "images": p.images,
                "status": p.status.value if p.status else None,
                "is_pinned": p.is_pinned,
                "like_count": p.like_count,
                "comment_count": p.comment_count,
                "created_at": p.created_at,
                "liked_by_me": False,
            }
        )
    return items, total


async def like_post(db: AsyncSession, post_id: int, user: User) -> int:
    post = await db.get(Post, post_id)
    if post is None:
        raise not_found("内容不存在")
    post.like_count = (post.like_count or 0) + 1
    club = await db.get(Club, post.club_id)
    if club:
        club.heat_score = (club.heat_score or 0) + 1
    await db.flush()
    return post.like_count
