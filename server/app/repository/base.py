"""网页版数据访问契约：一层接口，两个数据源（微信云 / 本地 SQLite）。"""
from __future__ import annotations

from typing import Any, Dict, Optional, Protocol


class BalaError(Exception):
    """业务错误，对齐云函数 {ok: false, message, code} 的语义。"""

    def __init__(self, message: str, code: str = "", http_status: int = 400):
        super().__init__(message)
        self.message = message
        self.code = code
        self.http_status = http_status


class BalaRepository(Protocol):
    """对前端暴露的唯一数据入口。

    fn / action / payload 与小程序 `call(name, action, payload)` 一一对应，
    identity 为网页端匿名身份（web:<uuid>），云端实现会注入 payload.__openid。
    """

    mode: str

    async def call(
        self, fn: str, action: str, payload: Dict[str, Any], identity: str
    ) -> Optional[Any]:
        ...


__all__ = ["BalaError", "BalaRepository"]
