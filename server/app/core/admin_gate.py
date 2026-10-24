"""运营后台会话与互斥角色权限。"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hmac import compare_digest

from fastapi import Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from jose import JWTError, jwt

from app.config import settings
from app.core.database import SessionLocal
from app.models.admin_account import AdminAccount

COOKIE_NAME = "admin_token"
ACCOUNT_COOKIE_NAME = "admin_account_token"
ROLE_ADMIN = "admin"
ROLE_CLUB_MODERATOR = "club_moderator"
ROLE_REVIEWER = "reviewer"


@dataclass(frozen=True)
class AdminPrincipal:
    role: str
    nickname: str = "管理员"
    account_id: int | None = None
    club_id: str | None = None

    @property
    def is_admin(self) -> bool:
        return self.role == ROLE_ADMIN

    @property
    def role_label(self) -> str:
        return {
            ROLE_ADMIN: "管理员",
            ROLE_CLUB_MODERATOR: "社团版主",
            ROLE_REVIEWER: "审核员",
        }[self.role]


ADMIN_PRINCIPAL = AdminPrincipal(role=ROLE_ADMIN)


def _login_required() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
        headers={"Location": "/admin/web/login"},
    )


def _is_admin_cookie(token: str) -> bool:
    return bool(
        settings.ADMIN_WEB_TOKEN
        and compare_digest(token.encode("utf-8"), settings.ADMIN_WEB_TOKEN.encode("utf-8"))
    )


def create_account_session(account_id: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(account_id),
        "type": "admin_account",
        "iat": now,
        "exp": now + timedelta(minutes=settings.ADMIN_SESSION_MINUTES),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


async def current_admin(request: Request) -> AdminPrincipal:
    """优先保留原管理员 Cookie，再校验独立账号的签名会话。"""
    if _is_admin_cookie(request.cookies.get(COOKIE_NAME, "")):
        request.state.principal = ADMIN_PRINCIPAL
        return ADMIN_PRINCIPAL

    token = request.cookies.get(ACCOUNT_COOKIE_NAME, "")
    if not token:
        raise _login_required()
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        if payload.get("type") != "admin_account":
            raise _login_required()
        account_id = int(payload.get("sub", ""))
    except (JWTError, TypeError, ValueError) as exc:
        raise _login_required() from exc

    async with SessionLocal() as db:
        account = await db.get(AdminAccount, account_id)
    if (
        not account
        or not account.is_active
        or account.role not in {ROLE_CLUB_MODERATOR, ROLE_REVIEWER}
        or (account.role == ROLE_CLUB_MODERATOR and not account.club_id)
    ):
        raise _login_required()
    principal = AdminPrincipal(
        role=account.role,
        nickname=account.nickname,
        account_id=account.id,
        club_id=account.club_id,
    )
    request.state.principal = principal
    return principal


def require_super_admin(principal: AdminPrincipal = Depends(current_admin)) -> AdminPrincipal:
    if not principal.is_admin:
        raise HTTPException(status_code=403, detail="仅管理员可访问此功能")
    return principal


def require_reviewer(principal: AdminPrincipal = Depends(current_admin)) -> AdminPrincipal:
    if principal.role not in {ROLE_ADMIN, ROLE_REVIEWER}:
        raise HTTPException(status_code=403, detail="仅管理员或审核员可访问内容审核")
    return principal


def require_admin_web(principal: AdminPrincipal = Depends(current_admin)) -> AdminPrincipal:
    return principal


def login_page_redirect() -> RedirectResponse:
    return RedirectResponse(url="/admin/web/login", status_code=307)
