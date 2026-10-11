"""社团广场接口（PRD §3.2）。

GET  /api/v1/clubs              社团列表（分类/搜索/热度排序）
POST /api/v1/clubs              申请入驻
GET  /api/v1/clubs/{id}         社团详情
POST /api/v1/clubs/{id}/join    加入社团
DELETE /api/v1/clubs/{id}/join  退出社团
GET  /api/v1/clubs/{id}/posts   社团内容流
POST /api/v1/clubs/{id}/posts   发布内容（管理员）
POST /api/v1/posts/{id}/like    点赞
GET  /api/v1/clubs/rank         社团热度榜（C-202）
"""
from __future__ import annotations

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, Db, OptionalUser
from app.models.common import ClubCategory
from app.schemas.club import ClubApplyIn, PostCreateIn, PostOut
from app.schemas.common import ApiResponse, Page
from app.services import club_service

router = APIRouter(prefix="/clubs", tags=["社团广场"])


@router.get("")
async def list_clubs(
    db: Db,
    user: OptionalUser,
    category: str | None = Query(None),
    keyword: str = "",
    sort: str = "heat",
    offset: int = 0,
    limit: int = 20,
) -> ApiResponse[Page]:
    cat = None
    if category:
        try:
            cat = ClubCategory(category)
        except ValueError:
            cat = None
    items, total = await club_service.list_clubs(
        db, user, category=cat, keyword=keyword, sort=sort, offset=offset, limit=limit
    )
    return ApiResponse.ok(Page.build(items, total, offset, limit))


@router.get("/rank")
async def club_rank(db: Db, user: OptionalUser, limit: int = 10) -> ApiResponse:
    items, total = await club_service.list_clubs(db, user, sort="heat", offset=0, limit=limit)
    return ApiResponse.ok(items)


@router.post("")
async def apply_club(payload: ClubApplyIn, db: Db, user: CurrentUser) -> ApiResponse:
    club = await club_service.apply_club(db, payload, user)
    return ApiResponse.ok({"id": club.id, "status": "pending"}, "入驻申请已提交，等待审核")


@router.get("/{club_id}")
async def club_detail(club_id: int, db: Db, user: OptionalUser) -> ApiResponse:
    return ApiResponse.ok(await club_service.get_club(db, club_id, user))


@router.post("/{club_id}/join")
async def join_club(club_id: int, db: Db, user: CurrentUser) -> ApiResponse:
    await club_service.join_club(db, club_id, user)
    return ApiResponse.ok({"joined": True}, "已加入社团")


@router.delete("/{club_id}/join")
async def leave_club(club_id: int, db: Db, user: CurrentUser) -> ApiResponse:
    await club_service.leave_club(db, club_id, user)
    return ApiResponse.ok({"joined": False}, "已退出社团")


@router.get("/{club_id}/posts")
async def club_posts(
    club_id: int, db: Db, user: OptionalUser, offset: int = 0, limit: int = 20
) -> ApiResponse[Page]:
    items, total = await club_service.list_posts(
        db, club_id=club_id, user=user, offset=offset, limit=limit
    )
    return ApiResponse.ok(Page.build([PostOut(**i) for i in items], total, offset, limit))


@router.post("/{club_id}/posts")
async def create_post(
    club_id: int, payload: PostCreateIn, db: Db, user: CurrentUser
) -> ApiResponse:
    post = await club_service.create_post(db, club_id, payload, user)
    return ApiResponse.ok({"id": post.id, "status": post.status.value}, "已提交审核")


@router.post("/posts/{post_id}/like")
async def like_post(post_id: int, db: Db, user: CurrentUser) -> ApiResponse:
    n = await club_service.like_post(db, post_id, user)
    return ApiResponse.ok({"like_count": n}, "已点赞")
