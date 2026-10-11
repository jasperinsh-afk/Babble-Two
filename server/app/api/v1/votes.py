"""投票中心接口（PRD §3.1，技术架构文档 §3.2）。

GET    /api/v1/votes                 投票列表（筛选/分页）
GET    /api/v1/votes/today           今日投票（H-002）
GET    /api/v1/votes/{id}            投票详情
POST   /api/v1/votes/{id}/cast       提交投票
PUT    /api/v1/votes/{id}/cast       修改投票（限一次）
GET    /api/v1/votes/{id}/results    投票结果（含脱敏分组）
GET    /api/v1/votes/{id}/comments   立场列表
POST   /api/v1/votes/{id}/comments   发布立场
POST   /api/v1/votes/{id}/join       接龙报名（V-101）
DELETE /api/v1/votes/{id}/join       取消接龙
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, Db, OptionalUser
from app.core.exceptions import bad_request
from app.core.rate_limit import check_comment_limit, check_vote_limit
from app.models.common import PollStatus, PollTag
from app.schemas.common import ApiResponse, Page
from app.schemas.vote import CastVoteIn, CommentIn, CommentOut
from app.services import vote_service

router = APIRouter(prefix="/votes", tags=["投票中心"])


@router.get("")
async def list_votes(
    db: Db,
    user: OptionalUser,
    tag: str | None = Query(None, description="news/campus/meme/group"),
    status: str | None = Query(None, description="active/closed/archived"),
    offset: int = 0,
    limit: int = 20,
) -> ApiResponse[Page]:
    try:
        tag_enum = PollTag(tag) if tag else None
    except ValueError:
        raise bad_request("不支持的筛选标签")
    try:
        status_enum = PollStatus(status) if status else None
    except ValueError:
        raise bad_request("不支持的状态")

    items, total = await vote_service.list_polls(
        db, user=user, tag=tag_enum, status=status_enum, offset=offset, limit=limit
    )
    return ApiResponse.ok(Page.build(items, total, offset, limit))


@router.get("/today")
async def today_vote(db: Db, user: OptionalUser) -> ApiResponse:
    poll = await vote_service.get_today_poll(db, user)
    return ApiResponse.ok(poll)


@router.get("/{poll_id}")
async def poll_detail(poll_id: int, db: Db, user: OptionalUser) -> ApiResponse:
    return ApiResponse.ok(await vote_service.get_poll(db, poll_id, user))


@router.post("/{poll_id}/cast")
async def cast_vote(
    poll_id: int, payload: CastVoteIn, db: Db, user: CurrentUser
) -> ApiResponse:
    await check_vote_limit(user.id)
    return ApiResponse.ok(
        await vote_service.cast_vote(db, poll_id, payload.option_ids, user), "投票成功"
    )


@router.put("/{poll_id}/cast")
async def change_vote(
    poll_id: int, payload: CastVoteIn, db: Db, user: CurrentUser
) -> ApiResponse:
    await check_vote_limit(user.id)
    return ApiResponse.ok(
        await vote_service.cast_vote(db, poll_id, payload.option_ids, user), "已修改投票"
    )


@router.get("/{poll_id}/results")
async def poll_results(poll_id: int, db: Db, user: OptionalUser) -> ApiResponse:
    return ApiResponse.ok(await vote_service.get_results(db, poll_id, user))


@router.get("/{poll_id}/comments")
async def list_comments(
    poll_id: int, db: Db, user: OptionalUser, offset: int = 0, limit: int = 20
) -> ApiResponse[Page]:
    items, total = await vote_service.list_comments(db, poll_id, user, offset, limit)
    return ApiResponse.ok(Page.build([CommentOut(**i) for i in items], total, offset, limit))


@router.post("/{poll_id}/comments")
async def add_comment(
    poll_id: int, payload: CommentIn, db: Db, user: CurrentUser
) -> ApiResponse:
    await check_comment_limit(user.id)
    c = await vote_service.add_comment(db, poll_id, payload.content, user)
    return ApiResponse.ok(
        CommentOut(
            id=c.id,
            poll_id=c.poll_id,
            user_id=c.user_id,
            content=c.content,
            like_count=c.like_count,
            created_at=c.created_at,
        ),
        "已发布立场",
    )


@router.post("/{poll_id}/join")
async def join_group(
    poll_id: int, option_id: int = Query(...), db: Db = None, user: CurrentUser = None
) -> ApiResponse:
    return ApiResponse.ok(await vote_service.join_group(db, poll_id, option_id, user), "报名成功")


@router.delete("/{poll_id}/join")
async def leave_group(poll_id: int, db: Db, user: CurrentUser) -> ApiResponse:
    await vote_service.leave_group(db, poll_id, user)
    return ApiResponse.ok({"left": True}, "已取消报名")
