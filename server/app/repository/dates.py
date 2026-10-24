"""云数据库日期（ISO 字符串 / 时间戳）与 Python datetime 的互转工具。"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Optional

ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    """与云函数 new Date().toISOString() 保持一致的毫秒级 UTC 字符串。"""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace(
        "+00:00", "Z"
    )


def parse_dt(value: Any) -> Optional[datetime]:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, (int, float)):
        # 云开发 Date 导出可能是毫秒时间戳
        return datetime.fromtimestamp(value / 1000, tz=timezone.utc)
    if isinstance(value, dict) and "$date" in value:
        return parse_dt(value["$date"])
    if isinstance(value, str):
        text = value.strip()
        if not ISO_RE.match(text):
            return None
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    return None


def is_iso_string(value: Any) -> bool:
    return isinstance(value, str) and parse_dt(value) is not None


__all__ = ["utcnow", "iso", "parse_dt", "is_iso_string", "ISO_RE"]
