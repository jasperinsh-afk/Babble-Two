"""管理后台接口（PRD §3.6.1 ML-I-006 + §4 审核）。

投票管理
  GET  /api/v1/admin/polls              投票管理列表（含草稿/待发布）
  POST /api/v1/admin/polls              创建投票
  POST /api/v1/admin/polls/{id}/approve 审核通过（人工终审，风控红线）
  POST /api/v1/admin/polls/{id}/reject  审核驳回
  POST /api/v1/admin/polls/{id}/publish 立即上线
  POST /api/v1/admin/polls/{id}/archive 归档

爬虫候选池
  GET  /api/v1/admin/candidates         候选话题池
  POST /api/v1/admin/candidates/{id}/review   人工终审
  POST /api/v1/admin/candidates/{id}/draft    LLM 生成投票草稿
  POST /api/v1/admin/crawler/run        手动触发抓取

内容审核
  GET  /api/v1/admin/review             审核队列（社团/活动/帖子）
  POST /api/v1/admin/review/club/{id}
  POST /api/v1/admin/review/event/{id}

敏感词库
  GET  /api/v1/admin/sensitive-words
  POST /api/v1/admin/sensitive-words
  DELETE /api/v1/admin/sensitive-words/{id}

NFC 卡片
  GET  /api/v1/admin/nfc/cards
  POST /api/v1/admin/nfc/cards
  PUT  /api/v1/admin/nfc/cards/{id}
  DELETE /api/v1/admin/nfc/cards/{id}
  GET  /api/v1/admin/nfc/stats
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import desc, select

from app.api.deps import Db, require_admin_dep, require_operator_dep
from app.core.exceptions import not_found
from app.models.club import Club, Post
from app.models.common import (
    CrawlerItemStatus,
    PollStatus,
    ReviewStatus,
)
from app.models.crawler import CrawlerItem, SensitiveWord
from app.models.event import Event
from app.models.living import DormPost
from app.models.vote import Poll
from app.schemas.common import ApiResponse, Page
from app.schemas.crawler import (
    CandidateReviewIn,
    DraftGenerateIn,
    PollReviewIn,
    SensitiveWordIn,
)
from app.schemas.nfc import NfcCardRegisterIn
from app.schemas.vote import PollCreateIn
from app.services import (
    club_service,
    event_service,
    export_service,
    moderation_service,
    nfc_service,
    vote_service,
)

router = APIRouter(prefix="/admin", tags=["管理后台"])


# ── 投票管理 ──


@router.get("/polls")
async def admin_polls(
    db: Db,
    _=require_operator_dep,
    status: str | None = None,
    offset: int = 0,
    limit: int = 20,
) -> ApiResponse[Page]:
    from sqlalchemy import func

    conds = [Poll.is_deleted.is_(False)]
    if status:
        try:
            conds.append(Poll.status == PollStatus(status))
        except ValueError:
            pass
    rows = (
        await db.execute(
            select(Poll).where(*conds).order_by(desc(Poll.created_at)).offset(offset).limit(limit)
        )
    ).scalars().all()
    total = (await db.execute(select(func.count(Poll.id)).where(*conds))).scalar() or 0
    items = [
        {
            "id": p.id,
            "title": p.title,
            "poll_type": p.poll_type.value,
            "status": p.status.value,
            "category": p.category.value if p.category else None,
            "review_status": p.review_status.value,
            "start_at": p.start_at,
            "end_at": p.end_at,
            "created_at": p.created_at,
        }
        for p in rows
    ]
    return ApiResponse.ok(Page.build(items, total, offset, limit))


@router.post("/polls")
async def create_poll(payload: PollCreateIn, db: Db, user=require_operator_dep) -> ApiResponse:
    poll = await vote_service.create_poll(db, payload, user)
    return ApiResponse.ok({"id": poll.id, "status": poll.status.value}, "投票已创建")


@router.post("/polls/{poll_id}/approve")
async def approve_poll(poll_id: int, payload: PollReviewIn | None, db: Db, _=require_operator_dep) -> ApiResponse:
    """人工终审通过（风控红线：AI 生成内容不可免审）。"""
    poll = await db.get(Poll, poll_id)
    if poll is None:
        raise not_found("投票不存在")
    poll.review_status = ReviewStatus.APPROVED
    poll.review_note = payload.note if payload else ""
    poll.updated_at = datetime.now(timezone.utc)
    await db.flush()
    return ApiResponse.ok({"id": poll.id}, "审核通过")


@router.post("/polls/{poll_id}/reject")
async def reject_poll(poll_id: int, payload: PollReviewIn | None, db: Db, _=require_operator_dep) -> ApiResponse:
    poll = await db.get(Poll, poll_id)
    if poll is None:
        raise not_found("投票不存在")
    poll.review_status = ReviewStatus.REJECTED
    poll.review_note = payload.note if payload else ""
    poll.status = PollStatus.WITHDRAWN
    await db.flush()
    return ApiResponse.ok({"id": poll.id}, "已驳回")


@router.post("/polls/{poll_id}/publish")
async def publish_poll(poll_id: int, db: Db, _=require_operator_dep) -> ApiResponse:
    poll = await vote_service.publish_poll(db, poll_id)
    from app.services import push_service

    await push_service.notify_poll_published(db, poll.id, poll.title)
    return ApiResponse.ok({"id": poll.id, "status": poll.status.value}, "已上线")


@router.post("/polls/{poll_id}/archive")
async def archive_poll(poll_id: int, db: Db, _=require_operator_dep) -> ApiResponse:
    poll = await db.get(Poll, poll_id)
    if poll is None:
        raise not_found("投票不存在")
    poll.status = PollStatus.ARCHIVED
    await db.flush()
    return ApiResponse.ok({"id": poll.id}, "已归档")


# ── 爬虫候选池（墨麟书院输入层）──


@router.get("/candidates")
async def candidates(
    db: Db,
    _=require_operator_dep,
    status: str = "pending",
    offset: int = 0,
    limit: int = 20,
) -> ApiResponse[Page]:
    from sqlalchemy import func

    conds = []
    if status:
        try:
            conds.append(CrawlerItem.status == CrawlerItemStatus(status))
        except ValueError:
            pass
    rows = (
        await db.execute(
            select(CrawlerItem)
            .where(*conds)
            .order_by(desc(CrawlerItem.heat_score), desc(CrawlerItem.crawled_at))
            .offset(offset)
            .limit(limit)
        )
    ).scalars().all()
    total = (await db.execute(select(func.count(CrawlerItem.id)).where(*conds))).scalar() or 0
    return ApiResponse.ok(Page.build(rows, total, offset, limit))


@router.post("/candidates/{item_id}/review")
async def review_candidate(
    item_id: int, payload: CandidateReviewIn, db: Db, user=require_operator_dep
) -> ApiResponse:
    item = await db.get(CrawlerItem, item_id)
    if item is None:
        raise not_found("候选话题不存在")
    item.status = (
        CrawlerItemStatus.APPROVED
        if payload.status == "approved"
        else CrawlerItemStatus.REJECTED
    )
    item.reviewed_at = datetime.now(timezone.utc)
    item.reviewed_by = user.id
    item.filter_reason = payload.note
    await db.flush()
    return ApiResponse.ok({"id": item.id, "status": item.status.value}, "已审核")


@router.post("/candidates/{item_id}/draft")
async def generate_draft(
    item_id: int, payload: DraftGenerateIn, db: Db, _=require_operator_dep
) -> ApiResponse:
    """ML-I-004：LLM 生成投票草稿（运营可修改，必须人工终审）。"""
    from app.crawler import draft_generator

    item = await db.get(CrawlerItem, item_id)
    if item is None:
        raise not_found("候选话题不存在")
    drafts = await draft_generator.generate_drafts(
        db, item, payload.operator_note, payload.variants
    )
    return ApiResponse.ok(drafts)


@router.post("/crawler/run")
async def run_crawler(db: Db, _=require_operator_dep) -> ApiResponse:
    """ML-I-006 手动触发抓取（默认关闭）。"""
    from app.services import crawler_service

    result = await crawler_service.run_once(db)
    return ApiResponse.ok(result, "抓取完成")


@router.get("/crawler/status")
async def crawler_status(db: Db, _=require_operator_dep) -> ApiResponse:
    from sqlalchemy import func

    from app.config import settings

    total = (await db.execute(select(func.count(CrawlerItem.id)))).scalar() or 0
    pending = (
        await db.execute(
            select(func.count(CrawlerItem.id)).where(
                CrawlerItem.status == CrawlerItemStatus.PENDING
            )
        )
    ).scalar() or 0
    return ApiResponse.ok(
        {
            "enabled": settings.CRAWLER_ENABLED,
            "sources": settings.crawler_source_list,
            "total_items": total,
            "pending_items": pending,
        }
    )


# ── 内容审核队列 ──


@router.get("/review")
async def review_queue(db: Db, _=require_operator_dep) -> ApiResponse:
    polls = (
        await db.execute(
            select(Poll).where(Poll.review_status == ReviewStatus.PENDING).order_by(desc(Poll.created_at)).limit(50)
        )
    ).scalars().all()
    clubs = (
        await db.execute(
            select(Club).where(Club.review_status == ReviewStatus.PENDING).limit(50)
        )
    ).scalars().all()
    events = (
        await db.execute(
            select(Event).where(Event.review_status == ReviewStatus.PENDING).limit(50)
        )
    ).scalars().all()
    posts = (
        await db.execute(
            select(Post).where(Post.status != ReviewStatus.APPROVED).limit(50)
        )
    ).scalars().all()
    dorm = (
        await db.execute(
            select(DormPost).where(DormPost.review_status != ReviewStatus.APPROVED).limit(50)
        )
    ).scalars().all()
    return ApiResponse.ok(
        {
            "polls": [
                {"id": p.id, "title": p.title, "type": "poll", "created_at": p.created_at}
                for p in polls
            ],
            "clubs": [
                {"id": c.id, "title": c.name, "type": "club", "created_at": c.created_at}
                for c in clubs
            ],
            "events": [
                {"id": e.id, "title": e.title, "type": "event", "created_at": e.created_at}
                for e in events
            ],
            "posts": [
                {"id": p.id, "title": p.title or p.content[:30], "type": "post", "created_at": p.created_at}
                for p in posts
            ],
            "dorm_posts": [
                {"id": p.id, "title": p.content[:30], "type": "dorm_post", "created_at": p.created_at}
                for p in dorm
            ],
        }
    )


@router.post("/review/club/{club_id}")
async def review_club(
    club_id: int, approved: bool = True, note: str = "", db: Db = None, _=require_operator_dep
) -> ApiResponse:
    club = await club_service.review_club(db, club_id, approved, note)
    return ApiResponse.ok({"id": club.id, "is_verified": club.is_verified}, "已审核")


@router.post("/review/event/{event_id}")
async def review_event(
    event_id: int, approved: bool = True, db: Db = None, _=require_operator_dep
) -> ApiResponse:
    ev = await event_service.review_event(db, event_id, approved)
    return ApiResponse.ok({"id": ev.id}, "已审核")


# ── 敏感词库 ──


@router.get("/sensitive-words")
async def list_words(db: Db, _=require_operator_dep) -> ApiResponse:
    rows = (await db.execute(select(SensitiveWord).order_by(desc(SensitiveWord.id)))).scalars().all()
    return ApiResponse.ok(rows)


@router.post("/sensitive-words")
async def add_word(payload: SensitiveWordIn, db: Db, _=require_operator_dep) -> ApiResponse:
    from datetime import datetime

    db.add(
        SensitiveWord(
            word=payload.word,
            category=payload.category,
            severity=payload.severity,
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )
    )
    await db.flush()
    await moderation_service.refresh_word_bank(db)
    return ApiResponse.ok({"added": True}, "已添加并热更新词库")


@router.delete("/sensitive-words/{word_id}")
async def delete_word(word_id: int, db: Db, _=require_operator_dep) -> ApiResponse:
    w = await db.get(SensitiveWord, word_id)
    if w is None:
        raise not_found("词条不存在")
    await db.delete(w)
    await db.flush()
    await moderation_service.refresh_word_bank(db)
    return ApiResponse.ok({"deleted": True}, "已删除")


# ── NFC 卡片管理 ──


@router.get("/nfc/cards")
async def admin_nfc_cards(db: Db, _=require_operator_dep, offset: int = 0, limit: int = 100) -> ApiResponse:
    return ApiResponse.ok(await nfc_service.list_cards(db, offset, limit))


@router.post("/nfc/cards")
async def register_card(payload: NfcCardRegisterIn, db: Db, _=require_operator_dep) -> ApiResponse:
    card = await nfc_service.register_card(db, payload)
    return ApiResponse.ok({"card_id": card.card_id}, "卡片已注册")


@router.put("/nfc/cards/{card_id}")
async def update_card(
    card_id: str, payload: NfcCardRegisterIn, db: Db, _=require_operator_dep
) -> ApiResponse:
    payload.card_id = card_id
    card = await nfc_service.register_card(db, payload)
    return ApiResponse.ok({"card_id": card.card_id}, "已更新跳转目标")


@router.delete("/nfc/cards/{card_id}")
async def retire_card(card_id: str, db: Db, _=require_operator_dep) -> ApiResponse:
    from sqlalchemy import select as _select

    from app.models.nfc import NfcCard

    card = (await db.execute(_select(NfcCard).where(NfcCard.card_id == card_id))).scalars().first()
    if card is None:
        raise not_found("卡片不存在")
    card.is_active = False
    await db.flush()
    return ApiResponse.ok({"card_id": card_id}, "卡片已报废")


@router.get("/nfc/stats")
async def nfc_stats(db: Db, _=require_operator_dep) -> ApiResponse:
    return ApiResponse.ok(await nfc_service.card_stats(db))


# ── 数据看板 ──


@router.get("/dashboard")
async def dashboard(db: Db, _=require_operator_dep) -> ApiResponse:
    from sqlalchemy import func

    from app.models.user import User
    from app.models.vote import Ballot

    users = (await db.execute(select(func.count(User.id)))).scalar() or 0
    polls = (await db.execute(select(func.count(Poll.id)))).scalar() or 0
    ballots = (await db.execute(select(func.count(Ballot.id)))).scalar() or 0
    active = (
        await db.execute(
            select(func.count(Poll.id)).where(Poll.status == PollStatus.ACTIVE)
        )
    ).scalar() or 0
    return ApiResponse.ok(
        {
            "users": users,
            "polls": polls,
            "active_polls": active,
            "total_ballots": ballots,
        }
    )
