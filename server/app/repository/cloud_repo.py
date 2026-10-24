"""云端仓储：把网页请求转发给微信云函数，与小程序共用同一套业务规则与数据库。"""
from __future__ import annotations

from typing import Any, Dict, Optional

from app import cloudbase_client
from app.repository.base import BalaError


class CloudRepository:
    mode = "cloud"

    async def call(
        self, fn: str, action: str, payload: Dict[str, Any], identity: str
    ) -> Optional[Any]:
        body = dict(payload or {})
        # 云函数 resolveOpenid(payload) 优先读 __openid；identity 云函数用不到，跳过
        if identity and fn != "identity":
            body["__openid"] = identity

        envelope = await cloudbase_client.invoke(fn, action, body)
        if not envelope.get("ok", False):
            raise BalaError(
                envelope.get("message") or "云服务异常",
                envelope.get("code") or "",
            )
        return envelope.get("data")


__all__ = ["CloudRepository"]
