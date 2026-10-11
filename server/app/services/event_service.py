"""活动日历业务（PRD §3.3 E-001 ~ E-203）。"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

from sqlalchemy import asc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    ERR_ALREADY_REGISTERED,
    ERR_EVENT_CLOSED,
    ERR_EVENT_FULL,
    ERR_SIGNUP_DEADLINE_PASSED,
    AppError,
    not_found,
)
from app.models.club import Club
from app.models.common import CasType, EventStatus, ReviewStatus
from app.models.event import CasRecord, Event, EventRegistration
from app.models.user import User


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def create_event(db: AsyncSession, payload, user: User) -> Event:
    if payload.end_at <= payload.start_at:
        raise AppError(1001, "结束时间必须晚于开始时间")
    ev = Event(
        title=payload.title,
        description=payload.description,
        cover_url=payload.cover_url,
        location=payload.location,
        organizer_type=payload.organizer_type,
        organizer_id=payload.organizer_id,
        start_at=payload.start_at,
        end_at=payload.end_at,
        signup_deadline=payload.signup_deadline,
        max_participants=payload.max_participants,
        status=EventStatus.ACTIVE,
        review_status=ReviewStatus.PENDING,
        cas_type=payload.cas_type,
        created_by=user.id,
        created_at=_now(),
        updated_at=_now(),
    )
    db.add(ev)
    await db.flush()
    return ev


async def review_event(db: AsyncSession, event_id: int, approved: bool) -> Event:
    ev = await db.get(Event, event_id)
    if ev is None:
        raise not_found("活动不存在")
    ev.review_status = ReviewStatus.APPROVED if approved else ReviewStatus.REJECTED
    await db.flush()
    return ev


async def _enrich(db: AsyncSession, ev: Event, user: Optional[User]) -> dict:
    org_name = None
    if ev.organizer_type.value == "club" and ev.organizer_id:
        club = await db.get(Club, ev.organizer_id)
        org_name = club.name if club else None

    registered = False
    waitlist = False
    if user:
        r = await db.get(EventRegistration, (ev.id, user.id))
        if r:
            registered = True
            waitlist = r.is_waitlist
    return {
        "id": ev.id,
        "title": ev.title,
        "description": ev.description,
        "cover_url": ev.cover_url,
        "location": ev.location,
        "organizer_type": ev.organizer_type,
        "organizer_id": ev.organizer_id,
        "organizer_name": org_name,
        "start_at": ev.start_at,
        "end_at": ev.end_at,
        "signup_deadline": ev.signup_deadline,
        "max_participants": ev.max_participants,
        "status": ev.status,
        "participant_count": ev.participant_count,
        "cas_type": ev.cas_type,
        "registered_by_me": registered,
        "is_waitlist": waitlist,
    }


async def list_events(
    db: AsyncSession,
    user: Optional[User],
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    club_id: Optional[int] = None,
    offset: int = 0,
    limit: int = 20,
) -> Tuple[List[dict], int]:
    conds = [Event.is_deleted.is_(False), Event.review_status == ReviewStatus.APPROVED]
    if start:
        conds.append(Event.start_at >= start)
    if end:
        conds.append(Event.start_at <= end)
    if club_id:
        conds.append(Event.organizer_id == club_id)

    rows = (
        await db.execute(
            select(Event).where(*conds).order_by(asc(Event.start_at)).offset(offset).limit(limit)
        )
    ).scalars().all()
    total = (await db.execute(select(func.count(Event.id)).where(*conds))).scalar() or 0
    return [await _enrich(db, e, user) for e in rows], total


async def get_calendar(
    db: AsyncSession, user: Optional[User], year: int, month: int
) -> List[dict]:
    """E-001 月视图：按日聚合活动数量气泡。"""
    start = datetime(year, month, 1, tzinfo=timezone.utc)
    end = (
        datetime(year + (month // 12), (month % 12) + 1, 1, tzinfo=timezone.utc)
        if month < 12
        else datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    )
    rows, _ = await list_events(db, user, start=start, end=end, limit=500)

    buckets: Dict[str, List[dict]] = defaultdict(list)
    for e in rows:
        if e["start_at"]:
            buckets[e["start_at"].date().isoformat()].append(e)

    days = []
    cur = start.date()
    while cur < end.date():
        key = cur.isoformat()
        evs = buckets.get(key, [])
        days.append({"date": key, "count": len(evs), "events": evs})
        cur += timedelta(days=1)
    return days


async def register_event(db: AsyncSession, event_id: int, user: User) -> dict:
    ev = await db.get(Event, event_id)
    if ev is None or ev.is_deleted:
        raise not_found("活动不存在")
    if ev.status in (EventStatus.CLOSED, EventStatus.CANCELLED):
        raise AppError(ERR_EVENT_CLOSED, "活动已关闭", 400)
    if ev.signup_deadline and ev.signup_deadline < _now():
        raise AppError(ERR_SIGNUP_DEADLINE_PASSED, "报名已截止", 400)

    existing = await db.get(EventRegistration, (event_id, user.id))
    if existing:
        raise AppError(ERR_ALREADY_REGISTERED, "你已报名该活动", 400)

    is_waitlist = False
    if ev.max_participants and (ev.participant_count or 0) >= ev.max_participants:
        is_waitlist = True  # E-105 候补队列

    db.add(
        EventRegistration(
            event_id=event_id,
            user_id=user.id,
            is_waitlist=is_waitlist,
            registered_at=_now(),
        )
    )
    if not is_waitlist:
        ev.participant_count = (ev.participant_count or 0) + 1
        if ev.max_participants and ev.participant_count >= ev.max_participants:
            ev.status = EventStatus.FULL
    await db.flush()

    # E-107 / E-201 活动结束后沉淀 CAS 记录（此处先登记，结束后标记）
    if ev.cas_type:
        db.add(
            CasRecord(
                user_id=user.id,
                event_id=ev.id,
                title=ev.title,
                cas_type=ev.cas_type,
                role="participant",
                happened_at=ev.start_at,
                created_at=_now(),
            )
        )
        await db.flush()

    from app.services.badge_service import evaluate_user

    await evaluate_user(db, user.id)
    return await _enrich(db, ev, user)


async def cancel_registration(db: AsyncSession, event_id: int, user: User) -> None:
    r = await db.get(EventRegistration, (event_id, user.id))
    if not r:
        return
    ev = await db.get(Event, event_id)
    if not r.is_waitlist and ev:
        ev.participant_count = max(0, (ev.participant_count or 1) - 1)
        if ev.status == EventStatus.FULL and ev.max_participants:
            if ev.participant_count < ev.max_participants:
                ev.status = EventStatus.ACTIVE
    await db.delete(r)
    await db.flush()


async def list_my_events(db: AsyncSession, user: User, limit: int = 50) -> List[dict]:
    rows = (
        await db.execute(
            select(Event)
            .join(EventRegistration, EventRegistration.event_id == Event.id)
            .where(EventRegistration.user_id == user.id)
            .order_by(asc(Event.start_at))
            .limit(limit)
        )
    ).scalars().all()
    return [await _enrich(db, e, user) for e in rows]


async def list_cas_records(db: AsyncSession, user: User) -> List[dict]:
    rows = (
        await db.execute(
            select(CasRecord).where(CasRecord.user_id == user.id).order_by(CasRecord.happened_at.desc())
        )
    ).scalars().all()
    return [
        {
            "id": r.id,
            "event_id": r.event_id,
            "title": r.title,
            "cas_type": r.cas_type,
            "role": r.role,
            "happened_at": r.happened_at,
        }
        for r in rows
    ]
