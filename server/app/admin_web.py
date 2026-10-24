"""运营后台（FastAPI + Jinja2 服务端渲染，零 Node 依赖）。

改造后定位：墨麟书院的**输入层与输出层控制台**。

- 输入层：爬虫候选池（本地 PostgreSQL crawler_items）+ 敏感词库
- 输出层：投票数据导出页
- 看板 / 投票管理 / 卡片管理：数据读写全部经微信云开发数据库

C 端小程序已无登录体系，本后台独立使用 ADMIN_WEB_TOKEN 口令保护。
"""
from __future__ import annotations

from datetime import datetime, timezone
from hmac import compare_digest

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import desc, func, select
from sqlalchemy.exc import IntegrityError

from app import cloudbase_client
from app.config import SERVER_ROOT, settings
from app.core.admin_gate import (
    ACCOUNT_COOKIE_NAME,
    COOKIE_NAME,
    ROLE_CLUB_MODERATOR,
    ROLE_REVIEWER,
    AdminPrincipal,
    create_account_session,
    require_reviewer,
    require_super_admin,
)
from app.core.database import SessionLocal
from app.core.security import hash_password, validate_password_strength, verify_password
from app.models.admin_account import AdminAccount
from app.models.common import CrawlerItemStatus, ReviewStatus
from app.models.crawler import CrawlerItem, SensitiveWord
from app.models.user import User
from app.services import content_service

router = APIRouter(prefix="/admin/web", include_in_schema=False)
templates = Jinja2Templates(directory=str(SERVER_ROOT / "admin-web" / "templates"))


# ── 字段适配：把云数据库文档包装成模板可识别的形状 ──


class Enumish(str):
    """模板里用 `x.value` 取枚举值，云数据库存的是字符串，做一层兼容。"""

    @property
    def value(self) -> str:
        return str(self)


def _dt(value) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def _poll_row(p: dict) -> dict:
    return {
        "id": p.get("_id", ""),
        "title": p.get("title", ""),
        "poll_type": Enumish(p.get("pollType", "single")),
        "status": Enumish(p.get("status", "draft")),
        "review_status": Enumish(p.get("reviewStatus", "approved")),
        "start_at": _dt(p.get("startAt")),
        "end_at": _dt(p.get("endAt")),
    }


def _card_row(c: dict) -> dict:
    target_type = c.get("targetType") or (c.get("target") or {}).get("type") or "download"
    target_id = c.get("targetId") or (c.get("target") or {}).get("id") or ""
    return {
        "id": c.get("_id", ""),
        "card_id": c.get("cardId", ""),
        "location_desc": c.get("locationDesc", ""),
        "target_type": Enumish(target_type),
        "target_id": target_id,
        "poster_batch": c.get("posterBatch", "-"),
        "tap_count": c.get("tapCount", 0),
        "unique_user_count": c.get("uniqueUserCount", 0),
        "is_active": bool(c.get("isActive", True)),
    }


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def _cloud_or_empty(fn, *args, **kwargs):
    """云开发不可用时后台仍需可打开，降级为空列表/0。"""
    try:
        return await fn(*args, **kwargs)
    except Exception as exc:  # noqa: BLE001
        print(f"[admin-web] 云开发读取失败: {exc}")
        return kwargs.get("fallback", [] if "limit" in kwargs else 0)


# ── 登录 ──


async def _login_page(request: Request, error: str = "", register_error: str = ""):
    clubs = []
    try:
        clubs = await content_service.list_documents("clubs")
    except Exception as exc:  # noqa: BLE001
        print(f"[admin-web] 注册页社团读取失败: {exc}")
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "nav": "login", "clubs": clubs, "error": error, "register_error": register_error},
    )


def _account_login_response(account_id: int) -> RedirectResponse:
    resp = RedirectResponse(url="/admin/web/content", status_code=303)
    resp.set_cookie(
        ACCOUNT_COOKIE_NAME,
        create_account_session(account_id),
        httponly=True,
        secure=settings.is_production,
        samesite="strict",
        max_age=settings.ADMIN_SESSION_MINUTES * 60,
    )
    resp.delete_cookie(COOKIE_NAME)
    return resp


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return await _login_page(request)


@router.post("/login")
async def login(request: Request, token: str = Form(""), nickname: str = Form(""), password: str = Form("")):
    if settings.ADMIN_WEB_TOKEN and compare_digest(token.encode("utf-8"), settings.ADMIN_WEB_TOKEN.encode("utf-8")):
        resp = RedirectResponse(url="/admin/web/content", status_code=303)
        resp.set_cookie(COOKIE_NAME, token, httponly=True, secure=settings.is_production, samesite="strict", max_age=8 * 60 * 60)
        resp.delete_cookie(ACCOUNT_COOKIE_NAME)
        return resp
    nickname = nickname.strip()
    if nickname and password:
        async with SessionLocal() as db:
            account = (await db.execute(select(AdminAccount).where(AdminAccount.nickname == nickname))).scalar_one_or_none()
        if account and account.is_active and verify_password(password, account.password_hash):
            return _account_login_response(account.id)
    return await _login_page(request, error="管理员口令或账号密码不正确")


@router.post("/register")
async def register(
    request: Request,
    role: str = Form(...),
    nickname: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...),
    authorization_code: str = Form(...),
    club_id: str = Form(""),
):
    nickname = nickname.strip()
    club_id = club_id.strip()
    expected_code = {
        ROLE_CLUB_MODERATOR: settings.CLUB_MODERATOR_AUTH_CODE,
        ROLE_REVIEWER: settings.REVIEWER_AUTH_CODE,
    }.get(role)
    error = ""
    if not expected_code or not compare_digest(authorization_code.encode("utf-8"), expected_code.encode("utf-8")):
        error = "角色或授权码不正确"
    elif not 1 <= len(nickname) <= 50:
        error = "昵称长度需为 1-50 个字符"
    elif password != password_confirm:
        error = "两次输入的密码不一致"
    elif not validate_password_strength(password):
        error = "密码至少 8 位，且同时包含字母和数字"
    elif role == ROLE_CLUB_MODERATOR and not club_id:
        error = "社团版主必须选择所属社团"
    if not error and role == ROLE_CLUB_MODERATOR:
        club = await content_service.get_document("clubs", club_id)
        if not club:
            error = "所选社团不存在，请刷新后重试"
    if not error:
        async with SessionLocal() as db:
            exists = (await db.execute(select(AdminAccount.id).where(AdminAccount.nickname == nickname))).first()
            if exists:
                error = "昵称已被使用"
            else:
                db.add(AdminAccount(
                    nickname=nickname,
                    password_hash=hash_password(password),
                    role=role,
                    club_id=club_id if role == ROLE_CLUB_MODERATOR else None,
                    is_active=True,
                ))
                try:
                    await db.commit()
                except IntegrityError:
                    await db.rollback()
                    error = "昵称已被使用"
                else:
                    account = (await db.execute(select(AdminAccount).where(AdminAccount.nickname == nickname))).scalar_one()
                    return _account_login_response(account.id)
    return await _login_page(request, register_error=error)


@router.get("/logout")
async def logout():
    resp = RedirectResponse(url="/admin/web/login", status_code=303)
    resp.delete_cookie(COOKIE_NAME)
    resp.delete_cookie(ACCOUNT_COOKIE_NAME)
    return resp


# ── 页面 ──


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, _=Depends(require_super_admin)):
    async with SessionLocal() as db:
        users = (await db.execute(select(func.count(User.id)))).scalar() or 0

    try:
        polls = await cloudbase_client.count("polls")
        active = await cloudbase_client.count("polls", {"status": "active"})
        clubs = await cloudbase_client.count("clubs")
        ballots = await cloudbase_client.count("ballots")
    except Exception as exc:  # noqa: BLE001
        print(f"[admin-web] 看板云开发读取失败: {exc}")
        polls = active = clubs = ballots = 0

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
async def candidates(request: Request, status: str = "pending", _=Depends(require_super_admin)):
    async with SessionLocal() as db:
        conds = []
        try:
            conds.append(CrawlerItem.status == CrawlerItemStatus(status))
        except ValueError:
            pass
        rows = (
            await db.execute(
                select(CrawlerItem).where(*conds).order_by(desc(CrawlerItem.heat_score)).limit(50)
            )
        ).scalars().all()
    return templates.TemplateResponse(
        "candidates.html",
        {"request": request, "nav": "candidates", "items": rows, "status": status},
    )


@router.get("/polls", response_class=HTMLResponse)
async def polls(request: Request, _=Depends(require_super_admin)):
    rows = []
    try:
        docs = await cloudbase_client.query("polls", order_by="createdAt", limit=50)
        rows = [_poll_row(d) for d in docs]
    except Exception as exc:  # noqa: BLE001
        print(f"[admin-web] 投票列表读取失败: {exc}")
    return templates.TemplateResponse(
        "polls.html", {"request": request, "nav": "polls", "items": rows}
    )


@router.get("/review", response_class=HTMLResponse)
async def review(request: Request, principal: AdminPrincipal = Depends(require_reviewer)):
    pending_polls = []
    try:
        docs = await cloudbase_client.query(
            "polls", where={"reviewStatus": ReviewStatus.PENDING.value}, limit=50
        )
        pending_polls = [_poll_row(d) for d in docs]
    except Exception as exc:  # noqa: BLE001
        print(f"[admin-web] 待审投票读取失败: {exc}")

    words = []
    if principal.is_admin:
        async with SessionLocal() as db:
            words = (await db.execute(select(SensitiveWord).order_by(desc(SensitiveWord.id)))).scalars().all()

    return templates.TemplateResponse(
        "review.html",
        {
            "request": request,
            "nav": "review",
            "polls": pending_polls,
            "clubs": [],
            "events": [],
            "posts": [],
            "words": words,
        },
    )


@router.get("/nfc", response_class=HTMLResponse)
async def nfc(request: Request, _=Depends(require_super_admin)):
    cards = []
    try:
        docs = await cloudbase_client.query("nfc_cards", order_by="cardId", order="asc", limit=200)
        cards = [_card_row(d) for d in docs]
    except Exception as exc:  # noqa: BLE001
        print(f"[admin-web] 卡片列表读取失败: {exc}")
    return templates.TemplateResponse(
        "nfc.html", {"request": request, "nav": "nfc", "cards": cards}
    )


@router.get("/export", response_class=HTMLResponse)
async def export_page(request: Request, _=Depends(require_super_admin)):
    return templates.TemplateResponse("export.html", {"request": request, "nav": "export"})


# ── 运营动作（替代已下线的 /api/v1/admin/* 端点）──


@router.post("/api/polls/{poll_id}/{action}")
async def poll_action(poll_id: str, action: str, principal: AdminPrincipal = Depends(require_reviewer)):
    if not principal.is_admin and action not in {"approve", "reject"}:
        raise HTTPException(status_code=403, detail="审核员只能执行通过或驳回")
    patch_map = {
        "approve": {"reviewStatus": "approved"},
        "reject": {"reviewStatus": "rejected"},
        "publish": {"status": "active", "reviewStatus": "approved"},
        "archive": {"status": "archived"},
    }
    patch = patch_map.get(action)
    if patch:
        patch["updatedAt"] = _now().isoformat()
        try:
            await cloudbase_client.update("polls", {"_id": poll_id}, patch)
        except Exception as exc:  # noqa: BLE001
            print(f"[admin-web] 投票操作失败: {exc}")
    return {"ok": True}


@router.post("/api/nfc/cards")
async def register_card(request: Request, _=Depends(require_super_admin)):
    body = await request.json()
    card = {
        "cardId": body.get("card_id", ""),
        "code": body.get("card_id", ""),
        "locationType": body.get("location_type", "bulletin"),
        "locationDesc": body.get("location_desc", ""),
        "targetType": body.get("target_type", "download"),
        "targetId": body.get("target_id") or None,
        "isActive": True,
        "createdAt": _now().isoformat(),
    }
    try:
        await cloudbase_client.add("nfc_cards", card)
    except Exception as exc:  # noqa: BLE001
        print(f"[admin-web] 卡片注册失败: {exc}")
    return {"ok": True}


@router.post("/api/sensitive-words")
async def add_sensitive_word(request: Request, _=Depends(require_super_admin)):
    body = await request.json()
    async with SessionLocal() as db:
        db.add(
            SensitiveWord(
                word=body.get("word", ""),
                category=body.get("category", "custom"),
                severity=body.get("severity", "block"),
                is_active=True,
                created_at=_now(),
            )
        )
        await db.commit()
    return {"ok": True}


@router.post("/api/candidates/{item_id}/review")
async def candidate_review(item_id: int, request: Request, _=Depends(require_super_admin)):
    body = await request.json()
    status_map = {
        "approved": CrawlerItemStatus.APPROVED,
        "rejected": CrawlerItemStatus.REJECTED,
    }
    status = status_map.get(body.get("status", ""), CrawlerItemStatus.REJECTED)
    async with SessionLocal() as db:
        item = await db.get(CrawlerItem, item_id)
        if item:
            item.status = status
            item.reviewed_at = _now()
            await db.commit()
    return {"ok": True}


@router.post("/api/candidates/{item_id}/draft")
async def candidate_draft(item_id: int, request: Request, _=Depends(require_super_admin)):
    """墨麟书院输入层：为候选话题生成投票草稿，并推送到云数据库待审。"""
    from app.crawler.draft_generator import generate_drafts

    body = await request.json()
    variants = int(body.get("variants", 3) or 3)

    async with SessionLocal() as db:
        item = await db.get(CrawlerItem, item_id)
        if not item:
            return {"ok": False, "message": "候选项不存在"}
        drafts = await generate_drafts(db, item, operator_note="", variants=variants)

    pushed = []
    for d in drafts:
        draft = {
            "source": "crawler",
            "crawlerItemId": item_id,
            "title": d.get("title", item.title),
            "description": d.get("description", ""),
            "pollType": d.get("poll_type", "single"),
            "tag": d.get("category", "news"),
            "options": [
                {"optionId": f"o{i + 1}", "label": o, "sortOrder": i, "count": 0}
                for i, o in enumerate(d.get("options", []))
            ],
            "reviewStatus": "pending",
            "status": "draft",
            "createdAt": _now().isoformat(),
        }
        try:
            res = await cloudbase_client.upsert_draft(draft)
            pushed.append(res)
        except Exception as exc:  # noqa: BLE001
            pushed.append({"ok": False, "message": str(exc)})

    return {"ok": True, "drafts": pushed}


@router.post("/api/clubs/{club_id}/{action}")
async def club_action(club_id: str, action: str, _=Depends(require_reviewer)):
    if action == "approve":
        try:
            await cloudbase_client.update("clubs", {"_id": club_id}, {"isVerified": True})
        except Exception as exc:  # noqa: BLE001
            print(f"[admin-web] 社团审核失败: {exc}")
    return {"ok": True}


@router.post("/api/events/{event_id}/{action}")
async def event_action(event_id: str, action: str, _=Depends(require_reviewer)):
    if action == "approve":
        try:
            # 查询端只认 active/full（如 home_feed），published 永远查不到
            await cloudbase_client.update(
                "events", {"_id": event_id}, {"status": "active", "updatedAt": _now().isoformat()}
            )
        except Exception as exc:  # noqa: BLE001
            print(f"[admin-web] 活动审核失败: {exc}")
    return {"ok": True}


@router.post("/api/candidates/{item_id}/{action}")
async def candidate_action(item_id: int, action: str, _=Depends(require_super_admin)):
    status_map = {
        "approve": CrawlerItemStatus.APPROVED,
        "reject": CrawlerItemStatus.REJECTED,
    }
    status = status_map.get(action)
    if status:
        async with SessionLocal() as db:
            item = await db.get(CrawlerItem, item_id)
            if item:
                item.status = status
                item.reviewed_at = _now()
                await db.commit()
    return {"ok": True}
