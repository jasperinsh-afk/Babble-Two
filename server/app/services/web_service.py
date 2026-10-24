"""网页版请求编排：action 白名单 + 云端读缓存。

白名单是安全边界：/web/{fn}/{action} 是通用转发入口，绝不能借此调到
adminIngest / seedImport 等运营云函数。
"""
from __future__ import annotations

import json
import time
from typing import Any, Dict, Tuple

from app.config import settings
from app.repository import get_repository
from app.repository.base import BalaError

ALLOWED_ACTIONS: Dict[str, frozenset] = {
    "identity": frozenset({"get"}),
    "home": frozenset({"feed"}),
    "vote": frozenset({"list", "detail", "results", "cast", "joinChain", "leaveChain"}),
    "club": frozenset({"list", "rank", "detail", "posts", "join", "leave"}),
    "event": frozenset({"list", "calendar", "detail", "join", "myCas"}),
    "living": frozenset({"channels", "channelPosts", "lostFound", "secondHand"}),
    "scan": frozenset({"cardByCode", "checkin"}),
    "me": frozenset({"overview", "messages", "markRead", "messagePrefs"}),
    "analytics": frozenset({"track"}),
}

# 只缓存与身份无关的读操作，云开发 HTTP API 有日配额，缓存可显著省调用
READ_TTL: Dict[Tuple[str, str], int] = {
    ("home", "feed"): 60,
    ("vote", "list"): 30,
    ("club", "list"): 30,
    ("club", "rank"): 60,
    ("event", "calendar"): 60,
    ("living", "channels"): 300,
    ("living", "channelPosts"): 60,
    ("living", "lostFound"): 60,
    ("living", "secondHand"): 60,
}

WRITE_ACTIONS = frozenset(
    {
        ("vote", "cast"),
        ("vote", "joinChain"),
        ("vote", "leaveChain"),
        ("club", "join"),
        ("club", "leave"),
        ("event", "join"),
        ("scan", "checkin"),
        ("me", "markRead"),
        ("me", "messagePrefs"),
        ("analytics", "track"),
    }
)

_cache: Dict[str, Tuple[float, Any]] = {}


def invalidate_cache() -> None:
    _cache.clear()


async def call(fn: str, action: str, payload: Dict[str, Any], identity: str) -> Any:
    if action not in ALLOWED_ACTIONS.get(fn, frozenset()):
        raise BalaError(f"未知操作：{fn}.{action}", "UNKNOWN_ACTION", 404)

    repo = get_repository()
    if (
        repo.mode == "cloud"
        and (fn, action) in WRITE_ACTIONS
        and not settings.WEB_CLOUD_WRITE_ENABLED
    ):
        raise BalaError(
            "网页写入暂未开启：请先在微信开发者工具部署更新后的 "
            "vote/club/event/scan/me/analytics 云函数，再把 WEB_CLOUD_WRITE_ENABLED 设为 true",
            "WRITE_DISABLED",
            409,
        )

    ttl = READ_TTL.get((fn, action), 0) if settings.WEB_CACHE_ENABLED else 0
    if repo.mode != "cloud":
        ttl = 0  # 本地模式无需缓存，保持写入立即可见

    key = ""
    if ttl:
        key = f"{fn}.{action}:{json.dumps(payload, sort_keys=True, ensure_ascii=False)}"
        hit = _cache.get(key)
        if hit and hit[0] > time.monotonic():
            return hit[1]

    data = await repo.call(fn, action, payload, identity)

    if ttl and key:
        _cache[key] = (time.monotonic() + ttl, data)
    elif repo.mode == "cloud" and (fn, action) in WRITE_ACTIONS:
        invalidate_cache()  # 写操作后整体失效，避免读到过期计数
    return data


__all__ = ["call", "ALLOWED_ACTIONS", "invalidate_cache"]
