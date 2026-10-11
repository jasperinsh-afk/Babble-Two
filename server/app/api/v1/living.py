"""住宿生活接口（PRD §3.4）。

GET  /api/v1/living/channels                 频道列表（按可见性过滤）
GET  /api/v1/living/channels/{id}/posts      频道帖子
POST /api/v1/living/channels/{id}/posts      发帖
POST /api/v1/living/posts/{id}/reply         回复
POST /api/v1/living/posts/{id}/report        举报
GET  /api/v1/living/lost-found               失物招领
POST /api/v1/living/lost-found               发布失物
GET  /api/v1/living/second-hand              二手交换
POST /api/v1/living/second-hand              发布闲置
"""
from __future__ import annotations

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, Db, OptionalUser
from app.models.common import LostFoundKind
from app.schemas.common import ApiResponse, Page
from app.schemas.living import (
    DormPostIn,
    DormPostOut,
    DormReplyIn,
    LostFoundIn,
    LostFoundOut,
    SecondHandIn,
    SecondHandOut,
)
from app.services import living_service

router = APIRouter(prefix="/living", tags=["住宿生活"])


@router.get("/channels")
async def channels(db: Db, user: OptionalUser) -> ApiResponse:
    return ApiResponse.ok(await living_service.list_channels(db, user))


@router.get("/channels/{channel_id}/posts")
async def channel_posts(
    channel_id: int, db: Db, user: OptionalUser, offset: int = 0, limit: int = 20
) -> ApiResponse[Page]:
    items, total = await living_service.list_posts(
        db, channel_id, user, offset=offset, limit=limit
    )
    return ApiResponse.ok(Page.build([DormPostOut(**i) for i in items], total, offset, limit))


@router.post("/channels/{channel_id}/posts")
async def create_post(
    channel_id: int, payload: DormPostIn, db: Db, user: CurrentUser
) -> ApiResponse:
    payload.channel_id = channel_id
    post = await living_service.create_post(db, payload, user)
    return ApiResponse.ok({"id": post.id}, "已发布")


@router.post("/posts/{post_id}/reply")
async def reply_post(
    post_id: int, payload: DormReplyIn, db: Db, user: CurrentUser
) -> ApiResponse:
    r = await living_service.reply_post(db, post_id, payload.content, user)
    return ApiResponse.ok({"id": r.id}, "已回复")


@router.get("/posts/{post_id}/replies")
async def replies(post_id: int, db: Db, limit: int = 50) -> ApiResponse:
    return ApiResponse.ok(await living_service.list_replies(db, post_id, limit))


@router.post("/posts/{post_id}/report")
async def report_post(post_id: int, db: Db, user: CurrentUser) -> ApiResponse:
    await living_service.report_post(db, post_id)
    return ApiResponse.ok({"reported": True}, "已举报，将进入人工复核")


@router.get("/lost-found")
async def lost_found_list(
    db: Db,
    kind: str | None = None,
    resolved: bool | None = None,
    offset: int = 0,
    limit: int = 20,
) -> ApiResponse[Page]:
    k = None
    if kind:
        try:
            k = LostFoundKind(kind)
        except ValueError:
            k = None
    rows, total = await living_service.list_lost_found(
        db, kind=k, resolved=resolved, offset=offset, limit=limit
    )
    return ApiResponse.ok(
        Page.build([LostFoundOut.model_validate(r) for r in rows], total, offset, limit)
    )


@router.post("/lost-found")
async def create_lost_found(payload: LostFoundIn, db: Db, user: CurrentUser) -> ApiResponse:
    item = await living_service.create_lost_found(db, payload, user)
    return ApiResponse.ok({"id": item.id}, "已发布")


@router.get("/second-hand")
async def second_hand_list(
    db: Db, sold: bool | None = None, offset: int = 0, limit: int = 20
) -> ApiResponse[Page]:
    rows, total = await living_service.list_second_hand(
        db, sold=sold, offset=offset, limit=limit
    )
    return ApiResponse.ok(
        Page.build([SecondHandOut.model_validate(r) for r in rows], total, offset, limit)
    )


@router.post("/second-hand")
async def create_second_hand(payload: SecondHandIn, db: Db, user: CurrentUser) -> ApiResponse:
    item = await living_service.create_second_hand(db, payload, user)
    return ApiResponse.ok({"id": item.id}, "已发布")
