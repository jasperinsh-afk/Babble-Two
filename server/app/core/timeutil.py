"""时间工具：统一使用「朴素 UTC」作为内部时间表示。

原因：SQLite 的 DateTime 往返会丢失时区信息（返回 naive）。
统一成 naive UTC 后，DB 存储、SQL 比较与 Python 比较行为一致；
生产切 PostgreSQL(TIMESTAMPTZ) 时由服务端时区解释为 UTC，语义不变。
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional


def utcnow() -> datetime:
    """当前 UTC 时间（朴素，无 tzinfo）。"""
    return datetime.now(timezone.utc).replace(tzinfo=None).replace(tzinfo=None)


def to_naive_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """任意 datetime（naive 视为 UTC / aware 转换到 UTC）→ 朴素 UTC。"""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def to_aware(dt: Optional[datetime]) -> Optional[datetime]:
    """朴素 UTC → 带时区 UTC（对外输出用）。"""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)
