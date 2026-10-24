"""墨麟书院 · 数据输出层：投票数据沉淀与脱敏导出。

数据源已由本地 PostgreSQL 切换为**微信云开发数据库**（云开发 HTTP API）。
投票票数由云函数用原子自增维护在 `polls.options[].count` 与 `polls.totalVotes`，
本模块只做聚合与脱敏，不触碰任何 `_openid` 等可关联到个人的字段。

PRD §3.6.2（ML-O-001 ~ ML-O-005）
红线：导出必须脱敏，移除一切可关联到个人的信息。
"""
from __future__ import annotations

import csv
import io
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from app import cloudbase_client
from app.core.exceptions import ERR_EXPORT_RANGE_INVALID, AppError

logger = logging.getLogger(__name__)

EXPORT_FIELDS = [
    "poll_id",
    "title",
    "category",
    "poll_type",
    "option_labels",
    "vote_counts",
    "total_participants",
    "start_at",
    "end_at",
]

POLLS = "polls"


def _iso(value: Any) -> str:
    return value if isinstance(value, str) else ""


def _parse_dt(value: Any) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


async def collect_poll_stats(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    category: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """聚合云开发数据库中的投票数据（仅统计口径，不读取 _openid）。"""
    if start_date and end_date and start_date > end_date:
        raise AppError(ERR_EXPORT_RANGE_INVALID, "开始时间不能晚于结束时间")

    where: Dict[str, Any] = {"isDeleted": False}
    if category:
        where["tag"] = category

    polls = await cloudbase_client.query(
        POLLS, where=where, order_by="createdAt", order="desc", limit=100
    )

    rows: List[Dict[str, Any]] = []
    for p in polls:
        created = _parse_dt(p.get("createdAt"))
        if start_date and created and created < start_date:
            continue
        if end_date and created and created > end_date:
            continue

        options = p.get("options") or []
        labels = [o.get("label", "") for o in options]
        counts = [int(o.get("count", 0)) for o in options]

        rows.append(
            {
                "poll_id": p.get("_id", ""),
                "title": p.get("title", ""),
                "category": p.get("tag", ""),
                "poll_type": p.get("pollType", ""),
                "option_labels": labels,
                "vote_counts": counts,
                "total_participants": int(p.get("totalVotes", 0)),
                "start_at": _iso(p.get("startAt")),
                "end_at": _iso(p.get("endAt")),
            }
        )
    return rows


def to_csv(rows: List[Dict[str, Any]]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(EXPORT_FIELDS)
    for r in rows:
        writer.writerow(
            [
                r["poll_id"],
                r["title"],
                r["category"],
                r["poll_type"],
                " | ".join(r["option_labels"]),
                " | ".join(str(c) for c in r["vote_counts"]),
                r["total_participants"],
                r["start_at"],
                r["end_at"],
            ]
        )
    return buf.getvalue()


def to_excel_bytes(rows: List[Dict[str, Any]]) -> bytes:
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "投票数据"
    ws.append(["投票ID", "题干", "分类", "类型", "选项", "各选项票数", "参与人数", "开始时间", "结束时间"])
    for r in rows:
        ws.append(
            [
                r["poll_id"],
                r["title"],
                r["category"],
                r["poll_type"],
                " | ".join(r["option_labels"]),
                " | ".join(str(c) for c in r["vote_counts"]),
                r["total_participants"],
                r["start_at"],
                r["end_at"],
            ]
        )
    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()


async def export_votes(
    start_date: datetime,
    end_date: datetime,
    category: Optional[str] = None,
    fmt: str = "csv",
) -> tuple[bytes, str, str]:
    rows = await collect_poll_stats(start_date, end_date, category)
    if fmt == "excel":
        return (
            to_excel_bytes(rows),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ".xlsx",
        )
    return to_csv(rows).encode("utf-8-sig"), "text/csv; charset=utf-8", ".csv"
