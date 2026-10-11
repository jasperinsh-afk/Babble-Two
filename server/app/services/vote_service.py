"""投票中心核心业务（PRD §3.1 V-001 ~ V-204，王牌模块）。"""
from __future__ import annotations

import json
import logging
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Sequence, Tuple

from sqlalchemy import asc, case, desc, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    ERR_ALREADY_CHANGED,
    ERR_ALREADY_VOTED,
    ERR_CHANGE_NOT_ALLOWED,
    ERR_GROUP_FULL,
    ERR_NOT_VOTED_YET,
    ERR_OPTION_COUNT_INVALID,
    ERR_OPTION_INVALID,
    ERR_POLL_CLOSED,
    ERR_POLL_NOT_ACTIVE,
    AppError,
    conflict,
    not_found,
)
from app.core.redis import bump_vote_count, clear_vote_counts, read_vote_counts
from app.models.club import Club
from app.models.common import (
    POLL_OPTION_RANGE,
    PollSource,
    PollStatus,
    PollTag,
    PollType,
    ReviewStatus,
    UserRole,
)
from app.models.user import User
from app.models.vote import Ballot, Comment, Poll, PollOption
from app.schemas.vote import OptionOut, PollCreateIn, PollOut

logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ── 创建 ──


async def create_poll(db: AsyncSession, payload: PollCreateIn, user: User) -> Poll:
    """运营/管理员创建投票。草稿 → 定时 → 进行中。

    技术架构文档：poll_type 单选/多选/PK/排序；选项数按类型校验。
    """
    lo, hi = POLL_OPTION_RANGE.get(payload.poll_type, (2, 6))
    n = len(payload.options)
    if payload.poll_type != PollType.GROUP_BUY and not (lo <= n <= hi):
        raise AppError(
            ERR_OPTION_COUNT_INVALID,
            f"{payload.poll_type.value} 类型需要 {lo}~{hi} 个选项，当前 {n} 个",
        )
    if payload.poll_type == PollType.RANKING and n < 3:
        raise AppError(ERR_OPTION_COUNT_INVALID, "排序题至少 3 个选项")

    status = PollStatus.DRAFT
    start_at = payload.start_at
    if payload.publish_mode == "active":
        status = PollStatus.ACTIVE
        start_at = start_at or _now()
    elif payload.publish_mode == "scheduled":
        status = PollStatus.SCHEDULED
        start_at = payload.scheduled_at or payload.start_at

    poll = Poll(
        title=payload.title,
        description=payload.description,
        poll_type=payload.poll_type,
        source_type=PollSource.MANUAL,
        status=status,
        category=payload.category,
        tag=payload.tag,
        topic_tags=payload.topic_tags,
        start_at=start_at,
        end_at=payload.end_at or (start_at + timedelta(hours=24) if start_at else None),
        allow_change=payload.allow_change,
        anonymous=payload.anonymous,
        max_choices=payload.max_choices,
        max_participants=payload.max_participants,
        cover_url=payload.cover_url,
        created_by=user.id,
        crawler_item_id=payload.crawler_item_id,
        review_status=ReviewStatus.PENDING,
        created_at=_now(),
        updated_at=_now(),
    )
    db.add(poll)
    await db.flush()

    for idx, opt in enumerate(payload.options):
        db.add(
            PollOption(
                poll_id=poll.id,
                label=opt.label,
                sort_order=opt.sort_order or idx,
            )
        )
    await db.flush()
    return poll


# ── 查询 ──


async def _counts(db: AsyncSession, poll: Poll) -> Dict[int, int]:
    """优先读 Redis 计数，回落到数据库聚合。"""
    cached = await read_vote_counts(poll.id)
    if cached:
        return {int(k): v for k, v in cached.items()}

    rows = (
        await db.execute(
            select(Ballot.option_id, func.count(Ballot.id)).where(
                Ballot.poll_id == poll.id, Ballot.option_id.is_not(None)
            ).group_by(Ballot.option_id)
        )
    ).all()
    return {r[0]: r[1] for r in rows if r[0] is not None}


def _serialize_poll(
    poll: Poll,
    options: Sequence[PollOption],
    counts: Dict[int, int],
    my_choice: Optional[List[int]] = None,
    is_changed: bool = False,
    user: Optional[User] = None,
) -> PollOut:
    total = sum(counts.values())
    opts_out: List[OptionOut] = []
    for o in sorted(options, key=lambda x: (x.sort_order, x.id)):
        c = counts.get(o.id, 0)
        opts_out.append(
            OptionOut(
                id=o.id,
                label=o.label,
                sort_order=o.sort_order,
                vote_count=c,
                percent=round(c / total * 100, 1) if total else 0.0,
            )
        )

    remaining = None
    if poll.end_at:
        delta = poll.end_at - _now()
        remaining = max(0, int(delta.total_seconds()))

    return PollOut(
        id=poll.id,
        title=poll.title,
        description=poll.description,
        poll_type=poll.poll_type,
        status=poll.status,
        category=poll.category,
        tag=poll.tag,
        topic_tags=poll.topic_tags,
        start_at=poll.start_at,
        end_at=poll.end_at,
        allow_change=poll.allow_change,
        anonymous=poll.anonymous,
        max_choices=poll.max_choices,
        max_participants=poll.max_participants,
        cover_url=poll.cover_url,
        created_by=poll.created_by,
        created_at=poll.created_at,
        options=opts_out,
        total_votes=total,
        my_choice=my_choice,
        has_voted=my_choice is not None,
        is_changed=is_changed,
        remaining_seconds=remaining,
        participant_count=total,
    )


async def get_poll(db: AsyncSession, poll_id: int, user: Optional[User] = None) -> PollOut:
    poll = await db.get(Poll, poll_id)
    if poll is None or poll.is_deleted:
        raise not_found("投票不存在")

    options = (
        await db.execute(select(PollOption).where(PollOption.poll_id == poll_id))
    ).scalars().all()
    counts = await _counts(db, poll)

    my_choice = None
    is_changed = False
    if user:
        ballot = (
            await db.execute(
                select(Ballot).where(Ballot.poll_id == poll_id, Ballot.user_id == user.id)
            )
        ).scalars().first()
        if ballot:
            is_changed = ballot.is_changed
            if ballot.option_id:
                my_choice = [ballot.option_id]
            elif ballot.option_ids:
                try:
                    my_choice = json.loads(ballot.option_ids)
                except json.JSONDecodeError:
                    my_choice = []

    return _serialize_poll(poll, options, counts, my_choice, is_changed, user)


async def list_polls(
    db: AsyncSession,
    user: Optional[User] = None,
    tag: Optional[PollTag] = None,
    status: Optional[PollStatus] = None,
    include_archived: bool = False,
    offset: int = 0,
    limit: int = 20,
) -> Tuple[List[PollOut], int]:
    """V-201 排序：进行中 → 即将结束 → 最新。"""
    conditions = [Poll.is_deleted.is_(False), Poll.review_status == ReviewStatus.APPROVED]
    if tag:
        conditions.append(Poll.tag == tag)
    if status:
        conditions.append(Poll.status == status)
    else:
        conditions.append(Poll.status.in_([PollStatus.ACTIVE, PollStatus.CLOSED]))
        if not include_archived:
            conditions.append(Poll.status != PollStatus.ARCHIVED)

    base = select(Poll).where(*conditions)

    # 进行中优先，其次按剩余时间升序（即将结束在前），再按创建时间倒序
    status_order = case(
        (Poll.status == PollStatus.ACTIVE, 0),
        (Poll.status == PollStatus.SCHEDULED, 1),
        (Poll.status == PollStatus.CLOSED, 2),
        else_=3,
    )
    stmt = (
        base.order_by(status_order.asc(), asc(Poll.end_at), desc(Poll.created_at))
        .offset(offset)
        .limit(limit)
    )
    polls = (await db.execute(stmt)).scalars().all()
    total = (
        await db.execute(select(func.count(Poll.id)).where(*conditions))
    ).scalar() or 0

    result: List[PollOut] = []
    for p in polls:
        options = (
            await db.execute(
                select(PollOption).where(PollOption.poll_id == p.id).order_by(PollOption.sort_order)
            )
        ).scalars().all()
        counts = await _counts(db, p)
        my_choice = None
        is_changed = False
        if user:
            b = (
                await db.execute(
                    select(Ballot).where(Ballot.poll_id == p.id, Ballot.user_id == user.id)
                )
            ).scalars().first()
            if b:
                is_changed = b.is_changed
                my_choice = [b.option_id] if b.option_id else (
                    json.loads(b.option_ids) if b.option_ids else []
                )
        result.append(_serialize_poll(p, options, counts, my_choice, is_changed, user))
    return result, total


async def get_today_poll(db: AsyncSession, user: Optional[User] = None) -> Optional[PollOut]:
    """H-002 今日头条：当前进行中热度最高的投票。"""
    polls, _ = await list_polls(db, user=user, status=PollStatus.ACTIVE, limit=1)
    return polls[0] if polls else None


# ── 投票 ──


async def cast_vote(
    db: AsyncSession, poll_id: int, option_ids: List[int], user: User
) -> PollOut:
    """V-001 ~ V-003：提交投票，幂等 + 允许改一次。"""
    poll = await db.get(Poll, poll_id)
    if poll is None or poll.is_deleted:
        raise not_found("投票不存在")
    if poll.status != PollStatus.ACTIVE:
        if poll.status == PollStatus.CLOSED:
            raise AppError(ERR_POLL_CLOSED, "投票已结束", 400)
        raise AppError(ERR_POLL_NOT_ACTIVE, "投票尚未开始", 400)
    if poll.end_at and poll.end_at < _now():
        raise AppError(ERR_POLL_CLOSED, "投票已结束", 400)

    valid = {
        o.id
        for o in (
            await db.execute(select(PollOption).where(PollOption.poll_id == poll_id))
        ).scalars().all()
    }
    if not set(option_ids).issubset(valid):
        raise AppError(ERR_OPTION_INVALID, "选项不存在", 400)

    if poll.poll_type == PollType.SINGLE or poll.poll_type == PollType.PK:
        if len(option_ids) != 1:
            raise AppError(ERR_OPTION_COUNT_INVALID, "单选只能选 1 项", 400)
    elif poll.poll_type == PollType.MULTI:
        if poll.max_choices and len(option_ids) > poll.max_choices:
            raise AppError(
                ERR_OPTION_COUNT_INVALID, f"最多可选 {poll.max_choices} 项", 400
            )

    existing = (
        await db.execute(
            select(Ballot).where(Ballot.poll_id == poll_id, Ballot.user_id == user.id)
        )
    ).scalars().first()

    if existing:
        if not poll.allow_change:
            raise AppError(ERR_CHANGE_NOT_ALLOWED, "该投票不允许修改", 400)
        if existing.is_changed:
            raise AppError(ERR_ALREADY_CHANGED, "你已修改过一次，无法再次修改", 400)
        await _revert_counts(poll_id, existing)
        existing.option_id = option_ids[0] if len(option_ids) == 1 else None
        existing.option_ids = json.dumps(option_ids) if len(option_ids) > 1 else None
        existing.is_changed = True
        existing.updated_at = _now()
    else:
        db.add(
            Ballot(
                poll_id=poll_id,
                user_id=user.id,
                option_id=option_ids[0] if len(option_ids) == 1 else None,
                option_ids=json.dumps(option_ids) if len(option_ids) > 1 else None,
                created_at=_now(),
                updated_at=_now(),
            )
        )

    for oid in option_ids:
        await bump_vote_count(poll_id, oid, 1)

    await db.flush()

    # 投票后评估勋章（首投 / 十连投 / 全勤）
    from app.services.badge_service import evaluate_user

    await evaluate_user(db, user.id)

    return await get_poll(db, poll_id, user)


async def _revert_counts(poll_id: int, ballot: Ballot) -> None:
    ids = [ballot.option_id] if ballot.option_id else (
        json.loads(ballot.option_ids) if ballot.option_ids else []
    )
    for oid in ids:
        if oid:
            await bump_vote_count(poll_id, oid, -1)


# ── 结果 ──


async def get_results(db: AsyncSession, poll_id: int, user: Optional[User] = None) -> dict:
    """V-002 实时结果 + V-006 年级/住宿维度脱敏分组统计。"""
    poll = await db.get(Poll, poll_id)
    if poll is None:
        raise not_found("投票不存在")

    options = (
        await db.execute(
            select(PollOption).where(PollOption.poll_id == poll_id).order_by(PollOption.sort_order)
        )
    ).scalars().all()
    counts = await _counts(db, poll)
    total = sum(counts.values())

    opts = []
    for o in options:
        c = counts.get(o.id, 0)
        opts.append(
            OptionOut(
                id=o.id,
                label=o.label,
                sort_order=o.sort_order,
                vote_count=c,
                percent=round(c / total * 100, 1) if total else 0.0,
            )
        )

    breakdown = await _breakdown(db, poll, options)

    return {
        "poll_id": poll.id,
        "title": poll.title,
        "total_votes": total,
        "options": opts,
        "breakdown": breakdown,
        "closed": poll.status in (PollStatus.CLOSED, PollStatus.ARCHIVED),
    }


async def _breakdown(db: AsyncSession, poll: Poll, options) -> dict:
    """年级 / 住宿维度拆分。仅当参与人数 ≥ 阈值才展示，避免反推个人（脱敏）。"""
    MIN_SAMPLE = 10
    rows = (
        await db.execute(
            select(Ballot.option_id, User.grade, User.dormitory)
            .join(User, User.id == Ballot.user_id)
            .where(Ballot.poll_id == poll.id, Ballot.option_id.is_not(None))
        )
    ).all()
    if len(rows) < MIN_SAMPLE:
        return {}

    def _group(key_fn):
        agg: Dict[str, Counter] = {}
        for oid, grade, dorm in rows:
            key = key_fn(grade, dorm) or "未知"
            agg.setdefault(key, Counter())[oid] += 1
        return {
            k: {
                "total": sum(c.values()),
                "options": {
                    str(o.id): {
                        "count": c.get(o.id, 0),
                        "percent": round(
                            c.get(o.id, 0) / sum(c.values()) * 100, 1
                        ) if sum(c.values()) else 0.0,
                    }
                    for o in options
                },
            }
            for k, c in agg.items()
        }

    return {
        "by_grade": _group(lambda g, d: g),
        "by_dormitory": _group(lambda g, d: (d or "")[:1] or None),
    }


# ── 立场评论 ──


async def add_comment(db: AsyncSession, poll_id: int, content: str, user: User) -> Comment:
    """V-005：仅投票后可写，≤200 字，过机审。"""
    from app.services.moderation_service import assert_text_ok, moderate_ugc

    voted = (
        await db.execute(
            select(Ballot).where(Ballot.poll_id == poll_id, Ballot.user_id == user.id)
        )
    ).scalars().first()
    if voted is None:
        raise AppError(ERR_NOT_VOTED_YET, "请先参与投票后再发表立场", 400)

    result = await moderate_ugc(db, content)
    assert_text_ok(result)

    c = Comment(
        poll_id=poll_id,
        user_id=user.id,
        content=content,
        review_status=ReviewStatus.APPROVED if result.passed else ReviewStatus.PENDING,
        is_hidden=not result.passed,
        created_at=_now(),
    )
    db.add(c)
    await db.flush()
    return c


async def list_comments(
    db: AsyncSession, poll_id: int, user: Optional[User], offset: int = 0, limit: int = 20
) -> Tuple[List[dict], int]:
    conds = [Comment.poll_id == poll_id, Comment.is_hidden.is_(False)]
    rows = (
        await db.execute(
            select(Comment, User.nickname)
            .join(User, User.id == Comment.user_id)
            .where(*conds)
            .order_by(desc(Comment.like_count), desc(Comment.created_at))
            .offset(offset)
            .limit(limit)
        )
    ).all()
    total = (await db.execute(select(func.count(Comment.id)).where(*conds))).scalar() or 0

    items = []
    for c, nickname in rows:
        items.append(
            {
                "id": c.id,
                "poll_id": c.poll_id,
                "user_id": c.user_id,
                "author_nickname": nickname,
                "content": c.content,
                "like_count": c.like_count,
                "created_at": c.created_at,
                "liked_by_me": False,
            }
        )
    return items, total


# ── 活动接龙 / 组团（V-101 ~ V-106）──


async def join_group(db: AsyncSession, poll_id: int, option_id: int, user: User) -> PollOut:
    poll = await db.get(Poll, poll_id)
    if poll is None or poll.poll_type != PollType.GROUP_BUY:
        raise not_found("接龙不存在")
    if poll.status != PollStatus.ACTIVE:
        raise AppError(ERR_POLL_CLOSED, "接龙已关闭", 400)

    total = sum((await _counts(db, poll)).values())
    if poll.max_participants and total >= poll.max_participants:
        raise AppError(ERR_GROUP_FULL, "接龙人数已满", 400)

    return await cast_vote(db, poll_id, [option_id], user)


async def leave_group(db: AsyncSession, poll_id: int, user: User) -> None:
    poll = await db.get(Poll, poll_id)
    if poll is None:
        raise not_found("接龙不存在")
    ballot = (
        await db.execute(
            select(Ballot).where(Ballot.poll_id == poll_id, Ballot.user_id == user.id)
        )
    ).scalars().first()
    if ballot is None:
        return
    await _revert_counts(poll_id, ballot)
    await db.delete(ballot)
    await db.flush()


# ── 生命周期 ──


async def publish_poll(db: AsyncSession, poll_id: int) -> Poll:
    """人工终审通过后上线（ML-I-005 定时发布 / 立即发布）。"""
    poll = await db.get(Poll, poll_id)
    if poll is None:
        raise not_found("投票不存在")
    poll.status = PollStatus.ACTIVE
    poll.review_status = ReviewStatus.APPROVED
    poll.start_at = poll.start_at or _now()
    poll.end_at = poll.end_at or (poll.start_at + timedelta(hours=24))
    poll.updated_at = _now()
    await db.flush()
    return poll


async def close_expired_polls(db: AsyncSession) -> int:
    """V-008：到期自动关闭。计数最终落库（技术架构文档 §4.4）。"""
    now = _now()
    polls = (
        await db.execute(
            select(Poll).where(
                Poll.status.in_([PollStatus.ACTIVE, PollStatus.SCHEDULED]),
                Poll.end_at.is_not(None),
                Poll.end_at <= now,
            )
        )
    ).scalars().all()
    closed = 0
    for p in polls:
        p.status = PollStatus.CLOSED
        p.updated_at = now
        closed += 1
        await clear_vote_counts(p.id)
    if closed:
        await db.flush()
    return closed


async def activate_scheduled_polls(db: AsyncSession) -> int:
    now = _now()
    polls = (
        await db.execute(
            select(Poll).where(
                Poll.status == PollStatus.SCHEDULED,
                or_(Poll.start_at.is_(None), Poll.start_at <= now),
            )
        )
    ).scalars().all()
    n = 0
    for p in polls:
        if p.review_status != ReviewStatus.APPROVED:
            continue  # 禁止无人审核自动上线（风控红线）
        p.status = PollStatus.ACTIVE
        p.updated_at = now
        n += 1
    if n:
        await db.flush()
    return n
