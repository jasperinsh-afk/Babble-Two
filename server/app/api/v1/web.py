"""网页版（bala-web）REST 入口。

路由形态与小程序 `call(name, action, payload)` 一一对应：
    POST /api/v1/web/vote/cast        {"pollId": "...", "optionIds": [...]}
    POST /api/v1/web/home/feed        {}
身份通过请求头携带：
    X-Bala-Identity: web:<uuid>
    X-Bala-Token:    <HMAC-SHA256(identity, SECRET_KEY)>
两者由 POST /api/v1/web/session 签发，前端存 localStorage。
统一返回 {ok, data, message, code}。
"""
from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Body, Depends, Request
from fastapi.responses import JSONResponse

from app.cloudbase_client import CloudbaseError
from app.config import settings
from app.repository.base import BalaError
from app.services import web_service
from app.services.web_identity import issue_identity, verify_identity

router = APIRouter(prefix="/web", tags=["网页版 bala-web"])


def _ok(data: Any = None, message: str = "ok") -> Dict[str, Any]:
    return {"ok": True, "data": data, "message": message, "code": ""}


def _fail(message: str, code: str = "", status: int = 400) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"ok": False, "data": None, "message": message, "code": code},
    )


async def current_identity(request: Request) -> str:
    identity = request.headers.get("x-bala-identity", "")
    token = request.headers.get("x-bala-token", "")
    if not verify_identity(identity, token):
        raise BalaError("身份无效或已过期，请刷新页面重试", "NO_AUTH", 401)
    return identity


@router.get("/health")
async def health() -> Dict[str, Any]:
    """数据源自检：前端可据此提示当前是云库还是本地演示数据。"""
    return _ok(
        {
            "mode": settings.web_data_mode,
            "cloudReady": bool(settings.WECHAT_APPID and settings.WECHAT_SECRET),
            "cloudEnv": settings.WECHAT_CLOUD_ENV,
            "cloudWriteEnabled": settings.WEB_CLOUD_WRITE_ENABLED,
        }
    )


@router.post("/session")
async def create_session() -> Dict[str, Any]:
    """签发匿名身份（首次访问调用，之后本地复用）。"""
    return _ok(issue_identity())


@router.post("/{fn}/{action}")
async def dispatch(
    fn: str,
    action: str,
    payload: Dict[str, Any] = Body(default={}),
    identity: str = Depends(current_identity),
):
    try:
        data = await web_service.call(fn, action, payload or {}, identity)
        return _ok(data)
    except BalaError as err:
        return _fail(err.message, err.code, err.http_status)
    except CloudbaseError as err:
        return _fail(str(err), "CLOUD_ERROR", 502)


__all__ = ["router", "current_identity"]
