"""墨麟书院 · 数据输出层：投票数据沉淀与脱敏导出。

PRD §3.6.2（ML-O-001 ~ ML-O-005）+ 技术架构文档 §11
红线：导出必须脱敏，移除一切可关联到个人的信息。
"""
from __future__ import annotations

import csv
import io
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ERR_EXPORT_RANGE_INVALID, AppError
from app.models.common import PollCategory, PollStatus
from app.models.vote import Ballot, Poll, PollOption

logger = logging.getLogger(__name__)

EXPORT_FIELDS = [
    "poll_id",
    "title",
    "category",
    "option_labels",
    "vote_counts",
    "total_participants",
    "start_at",
    "end_at",
]


async def collect_poll_stats(
    db: AsyncSession,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    category: Optional[PollCategory] = None,
) -> List[Dict[str, Any]]:
    """聚合投票数据（仅统计口径，不触碰 user_id）。"""
    if start_date and end_date and start_date > end_date:
        raise AppError(ERR_EXPORT_RANGE_INVALID, "开始时间不能晚于结束时间")

    conds = [Poll.is_deleted.is_(False)]
    if start_date:
        conds.append(Poll.created_at >= start_date)
    if end_date:
        conds.append(Poll.created_at <= end_date)
    if category:
        conds.append(Poll.category == category)

    polls = (
        await db.execute(select(Poll).where(*conds).order_by(Poll.created_at.desc()))
    ).scalars().all()

    rows: List[Dict[str, Any]] = []
    for p in polls:
        options = (
            await db.execute(
                select(PollOption).where(PollOption.poll_id == p.id).order_by(PollOption.sort_order)
            )
        ).scalars().all()
        counts_res = (
            await db.execute(
                select(Ballot.option_id, Ballot.id).where(Ballot.poll_id == p.id)
            )
        ).all()
        counter: Dict[int, int] = {}
        for oid, _ in counts_res:
            if oid:
                counter[oid] = counter.get(oid, 0) + 1

        labels = [o.label for o in options]
        counts = [counter.get(o.id, 0) for o in options]
        total = (
            await db.execute(select(Ballot.id).where(Ballot.poll_id == p.id))
        ).scalars().all()

        rows.append(
            {
                "poll_id": p.id,
                "title": p.title,
                "category": p.category.value if p.category else "",
                "option_labels": labels,
                "vote_counts": counts,
                "total_participants": len(total),
                "start_at": p.start_at.isoformat() if p.start_at else "",
                "end_at": p.end_at.isoformat() if p.end_at else "",
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
    ws.append(["投票ID", "题干", "分类", "选项", "各选项票数", "参与人数", "开始时间", "结束时间"])
    for r in rows:
        ws.append(
            [
                r["poll_id"],
                r["title"],
                r["category"],
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
    db: AsyncSession,
    start_date: datetime,
    end_date: datetime,
    category: Optional[PollCategory] = None,
    fmt: str = "csv",
) -> tuple[bytes, str, str]:
    rows = await collect_poll_stats(db, start_date, end_date, category)
    if fmt == "excel":
        return to_excel_bytes(rows), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", ".xlsx"
    return to_csv(rows).encode("utf-8-sig"), "text/csv; charset=utf-8", ".csv"
