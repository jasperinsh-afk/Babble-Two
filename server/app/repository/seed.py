"""种子数据加载与归一化。

cloudfunctions/seedImport/seed_data.json 是早期夹具，部分字段与现行云函数
不一致（例如 dorm_channels 用 type 而云函数读 scope、events.status 为 published
而云函数只认 active/full、nfc_cards 缺 code）。这里在导入本地 SQLite 时统一
补齐，保证本地模式与云端模式查出来的数据形态一致。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from datetime import timedelta

from app.repository.dates import ISO_RE, iso, parse_dt, utcnow

Documents = Dict[str, List[Dict[str, Any]]]

# 平移目标：让种子里最新的一条时间落在「今天 + 10 天」。
# 若直接对齐到今天，所有投票/活动在演示时都会立刻过期，无法体验投票流程。
SEED_FUTURE_DAYS = 10

# 云函数 where({isDeleted: false}) 过滤的集合，缺失字段必须补 False
_SOFT_DELETE_COLLECTIONS = (
    "polls",
    "clubs",
    "events",
    "dorm_posts",
    "lost_found",
    "second_hand",
)

_EVENT_STATUS_MAP = {"published": "active", "open": "active"}


def _normalize(collection: str, doc: Dict[str, Any]) -> Dict[str, Any]:
    item = dict(doc)
    if collection in _SOFT_DELETE_COLLECTIONS:
        item.setdefault("isDeleted", False)

    if collection == "polls":
        # 种子 p005 自相矛盾：participantCount=20/maxParticipants=20 却标 isFull=false，
        # 原样导入会让接龙永远满员。以 isFull 标志为准，留出最后一个名额。
        max_participants = item.get("maxParticipants")
        if max_participants and item.get("isFull") is False:
            item["participantCount"] = min(
                item.get("participantCount") or 0, max_participants - 1
            )

    elif collection == "clubs":
        item.setdefault("memberOpenids", [])
        item.setdefault("followerCount", 0)
        item.setdefault("isVerified", False)

    elif collection == "dorm_channels":
        item["scope"] = item.get("scope") or item.get("type") or "ALL"
        item.setdefault("isActive", True)

    elif collection == "dorm_posts":
        item.setdefault("reviewStatus", "approved")

    elif collection == "events":
        item["status"] = _EVENT_STATUS_MAP.get(item.get("status"), item.get("status") or "active")
        item["registeredOpenids"] = (
            item.get("registeredOpenids") or item.get("registered") or []
        )
        item["waitlistOpenids"] = item.get("waitlistOpenids") or item.get("waitlist") or []

    elif collection == "nfc_cards":
        item.setdefault("isActive", True)
        if item.get("cardId"):
            item.setdefault("code", item["cardId"])
        target = item.get("target") or {}
        if isinstance(target, dict):
            item.setdefault("targetType", target.get("type"))
            item.setdefault("targetId", target.get("id"))

    elif collection == "lost_found":
        item.setdefault("isResolved", item.get("status") == "resolved")

    elif collection == "second_hand":
        item.setdefault("isSold", item.get("status") == "sold")

    return item


def _walk_dates(node: Any, fn):
    """深度遍历，对所有 ISO 日期字符串应用 fn。"""
    if isinstance(node, dict):
        return {k: _walk_dates(v, fn) for k, v in node.items()}
    if isinstance(node, list):
        return [_walk_dates(v, fn) for v in node]
    if isinstance(node, str) and ISO_RE.match(node) and parse_dt(node):
        return fn(node)
    return node


def _iter_dates(node: Any):
    if isinstance(node, dict):
        for value in node.values():
            yield from _iter_dates(value)
    elif isinstance(node, list):
        for value in node:
            yield from _iter_dates(value)
    else:
        parsed = parse_dt(node)
        if parsed:
            yield parsed


def load_seed_documents(path: str | Path, shift_dates: bool = True) -> Documents:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    seed: Documents = {
        name: [_normalize(name, doc) for doc in docs]
        for name, docs in raw.items()
        if isinstance(docs, list)
    }

    if not shift_dates:
        return seed

    latest = None
    for docs in seed.values():
        for doc in docs:
            for parsed in _iter_dates(doc):
                if latest is None or parsed > latest:
                    latest = parsed

    if latest is None:
        return seed

    delta = (utcnow() + timedelta(days=SEED_FUTURE_DAYS)) - latest
    if abs(delta.total_seconds()) < 3600:
        return seed

    def shift(value: str) -> str:
        return iso(parse_dt(value) + delta)  # type: ignore[operator]

    shifted: Documents = {
        name: [_walk_dates(doc, shift) for doc in docs] for name, docs in seed.items()
    }
    return shifted


__all__ = ["load_seed_documents", "Documents"]
