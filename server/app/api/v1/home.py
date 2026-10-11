"""首页（发现）接口（PRD §3.5 H-001 ~ H-008）。

GET /api/v1/home/feed    首页聚合：Banner + 今日头条 + 热门投票 + 推荐活动 + 社团精选
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import Db, OptionalUser
from app.models.club import Club
from app.models.common import ReviewStatus
from app.models.event import Event, EventStatus
from app.schemas.common import ApiResponse
from app.services import event_service, vote_service

router = APIRouter(prefix="/home", tags=["首页"])


# 运营位 Banner（H-001 / H-006：后台可配置，此处读取常量）
BANNERS = [
    {
        "id": 1,
        "title": "每日时事投票 18:00 准时上线",
        "subtitle": "3 秒表达你的态度",
        "image": "",
        "target": "/vote",
    },
    {
        "id": 2,
        "title": "社团招新季开启",
        "subtitle": "找到属于你的组织",
        "image": "",
        "target": "/club",
    },
    {
        "id": 3,
        "title": "碰一碰校园海报",
        "subtitle": "OMEGA 点位集章解锁勋章",
        "image": "",
        "target": "/nfc",
    },
]


@router.get("/feed")
async def home_feed(db: Db, user: OptionalUser) -> ApiResponse:
    today = await vote_service.get_today_poll(db, user)

    hot_polls, _ = await vote_service.list_polls(db, user=user, offset=0, limit=8)

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    events, _ = await event_service.list_events(db, user, start=now, offset=0, limit=5)

    clubs = (
        await db.execute(
            select(Club)
            .where(Club.is_deleted.is_(False), Club.review_status == ReviewStatus.APPROVED)
            .order_by(desc(Club.heat_score))
            .limit(6)
        )
    ).scalars().all()

    return ApiResponse.ok(
        {
            "banners": BANNERS,
            "today_poll": today,
            "hot_polls": hot_polls,
            "recommended_events": events,
            "featured_clubs": [
                {
                    "id": c.id,
                    "name": c.name,
                    "logo_url": c.logo_url,
                    "category": c.category,
                    "is_verified": c.is_verified,
                    "heat_score": c.heat_score,
                }
                for c in clubs
            ],
        }
    )
