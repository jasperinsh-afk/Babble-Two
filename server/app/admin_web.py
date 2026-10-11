"""运营后台（FastAPI + Jinja2 服务端渲染，零 Node 依赖）。

覆盖 5 个页面：数据看板 / 爬虫候选池 / 投票管理 / 内容审核 / NFC 卡片 / 数据导出
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import desc, func, select

from app.core.database import SessionLocal
from app.models.club import Club, Post
from app.models.common import CrawlerItemStatus, PollStatus, ReviewStatus
from app.models.crawler import CrawlerItem, SensitiveWord
from app.models.event import Event
from app.models.nfc import NfcCard
from app.models.user import User
from app.models.vote import Ballot, Poll
from app.services import nfc_service

router = APIRouter(prefix="/admin/web", include_in_schema=False)
templates = Jinja2Templates(directory="admin-web/templates")


def _now():
    return datetime.now(timezone.utc)


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    async with SessionLocal() as db:
        users = (await db.execute(select(func.count(User.id)))).scalar() or 0
        polls = (await db.execute(select(func.count(Poll.id)))).scalar() or 0
        active = (
            await db.execute(select(func.count(Poll.id)).where(Poll.status == PollStatus.ACTIVE))
        ).scalar() or 0
        ballots = (await db.execute(select(func.count(Ballot.id)))).scalar() or 0
        clubs = (
            await db.execute(
                select(func.count(Club.id)).where(Club.review_status == ReviewStatus.APPROVED)
            )
        ).scalar() or 0
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "nav": "dashboard",
            "stats": {
                "users": users,
                "polls": polls,
                "active_polls": active,
                "ballots": ballots,
                "clubs": clubs,
            },
        },
    )


@router.get("/candidates", response_class=HTMLResponse)
async def candidates(request: Request, status: str = "pending"):
    async with SessionLocal() as db:
        conds = []
        try:
            conds.append(CrawlerItem.status == CrawlerItemStatus(status))
        except ValueError:
            pass
        rows = (
            await db.execute(
                select(CrawlerItem)
                .where(*conds)
                .order_by(desc(CrawlerItem.heat_score))
                .limit(50)
            )
        ).scalars().all()
    return templates.TemplateResponse(
        "candidates.html",
        {"request": request, "nav": "candidates", "items": rows, "status": status},
    )


@router.get("/polls", response_class=HTMLResponse)
async def polls(request: Request):
    async with SessionLocal() as db:
        rows = (
            await db.execute(select(Poll).order_by(desc(Poll.created_at)).limit(50))
        ).scalars().all()
    return templates.TemplateResponse(
        "polls.html", {"request": request, "nav": "polls", "items": rows}
    )


@router.get("/review", response_class=HTMLResponse)
async def review(request: Request):
    async with SessionLocal() as db:
        pending_polls = (
            await db.execute(
                select(Poll).where(Poll.review_status == ReviewStatus.PENDING).limit(50)
            )
        ).scalars().all()
        pending_clubs = (
            await db.execute(select(Club).where(Club.review_status == ReviewStatus.PENDING).limit(50))
        ).scalars().all()
        pending_events = (
            await db.execute(
                select(Event).where(Event.review_status == ReviewStatus.PENDING).limit(50)
            )
        ).scalars().all()
        pending_posts = (
            await db.execute(select(Post).where(Post.status != ReviewStatus.APPROVED).limit(50))
        ).scalars().all()
        words = (await db.execute(select(SensitiveWord).order_by(desc(SensitiveWord.id)))).scalars().all()
    return templates.TemplateResponse(
        "review.html",
        {
            "request": request,
            "nav": "review",
            "polls": pending_polls,
            "clubs": pending_clubs,
            "events": pending_events,
            "posts": pending_posts,
            "words": words,
        },
    )


@router.get("/nfc", response_class=HTMLResponse)
async def nfc(request: Request):
    async with SessionLocal() as db:
        cards = await nfc_service.list_cards(db, 0, 200)
    return templates.TemplateResponse(
        "nfc.html", {"request": request, "nav": "nfc", "cards": cards}
    )


@router.get("/export", response_class=HTMLResponse)
async def export_page(request: Request):
    return templates.TemplateResponse(
        "export.html", {"request": request, "nav": "export"}
    )
