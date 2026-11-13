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
from app.services import identity_link

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
    "leaderboard": frozenset({"weekly", "my", "setNickname", "track"}),
    "days": frozenset({"list", "save", "remove", "remote"}),
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
    ("leaderboard", "weekly"): 15,
    ("days", "remote"): 60,
}

# 历史写闸门：这些旧云函数未部署 resolveOpenid 版本前会产生 _openid 为空的脏数据。
# 新增的 leaderboard / days 云函数不存在该历史包袱，不纳入闸门。
CLOUD_GATED_WRITES = frozenset(
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

WRITE_ACTIONS = CLOUD_GATED_WRITES | frozenset(
    {
        ("leaderboard", "setNickname"),
        ("leaderboard", "track"),
        ("days", "save"),
        ("days", "remove"),
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
        and (fn, action) in CLOUD_GATED_WRITES
        and not settings.WEB_CLOUD_WRITE_ENABLED
    ):
        raise BalaError(
            "该写入暂未开启：请先部署更新后的 vote/club/event/scan/me/analytics "
            "云函数，再把 WEB_CLOUD_WRITE_ENABLED 设为 true",
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

    # 已绑定小程序账号的网页身份，注入 linked:<openid>，让云函数把数据写到同一微信账号
    resolved_identity = await identity_link.resolve(identity)
    data = await repo.call(fn, action, payload, resolved_identity)

    if ttl and key:
        _cache[key] = (time.monotonic() + ttl, data)
    elif repo.mode == "cloud" and (fn, action) in WRITE_ACTIONS:
        invalidate_cache()  # 写操作后整体失效，避免读到过期计数
    return data


__all__ = ["call", "ALLOWED_ACTIONS", "invalidate_cache"]
