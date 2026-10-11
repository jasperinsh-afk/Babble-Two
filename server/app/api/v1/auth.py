"""认证接口（PRD U-001）。

POST /api/v1/auth/register        注册
POST /api/v1/auth/login           登录
POST /api/v1/auth/refresh         刷新 Token
POST /api/v1/auth/send-code       发送邮箱验证码
POST /api/v1/auth/logout          登出（Token 进黑名单）
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import Db, rate_register
from app.core.dependencies import get_current_user
from app.core.security import blacklist_token
from app.models.user import User
from app.schemas.auth import (
    LoginIn,
    RefreshIn,
    RegisterIn,
    SendCodeIn,
    TokenOut,
    UserOut,
)
from app.schemas.common import ApiResponse
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/send-code")
async def send_code(
    payload: SendCodeIn,
    request: Request,
    db: Db,
    _=Depends(rate_register),
) -> ApiResponse:
    code = await auth_service.send_email_code(db, payload.email)
    data = {"sent": True}
    if not request.app.state.settings.is_production:
        data["dev_code"] = code  # 开发期便于联调
    return ApiResponse.ok(data, "验证码已发送")


@router.post("/register", response_model=ApiResponse[UserOut])
async def register(payload: RegisterIn, db: Db) -> ApiResponse:
    user, access, refresh = await auth_service.register(db, payload)
    return ApiResponse.ok(
        {
            "user": UserOut.model_validate(user),
            "token": TokenOut(
                access_token=access,
                refresh_token=refresh,
                expires_in=15 * 60,
            ),
        },
        "注册成功",
    )


@router.post("/login")
async def login(payload: LoginIn, db: Db) -> ApiResponse:
    user, access, refresh = await auth_service.login(db, payload.student_id, payload.password)
    return ApiResponse.ok(
        {
            "user": UserOut.model_validate(user),
            "token": TokenOut(
                access_token=access,
                refresh_token=refresh,
                expires_in=15 * 60,
            ),
        },
        "登录成功",
    )


@router.post("/refresh")
async def refresh(payload: RefreshIn, db: Db) -> ApiResponse:
    access, refresh_token = await auth_service.refresh_tokens(db, payload.refresh_token)
    return ApiResponse.ok(
        TokenOut(access_token=access, refresh_token=refresh_token, expires_in=15 * 60)
    )


@router.post("/logout")
async def logout(
    request: Request,
    user: User = Depends(get_current_user),
    db: Db = None,
) -> ApiResponse:
    auth = request.headers.get("authorization", "")
    token = auth.replace("Bearer ", "").strip()
    if token:
        await blacklist_token(token)
    return ApiResponse.ok({"logged_out": True}, "已退出登录")
