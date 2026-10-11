"""墨麟书院 · 数据输出层：脱敏导出（PRD ML-O-001 ~ ML-O-005）。

POST /api/v1/admin/export/votes      导出 CSV / Excel
GET  /api/v1/admin/export/preview    预览聚合统计（不落文件）
"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter
from fastapi.responses import Response

from app.api.deps import Db, require_operator_dep
from app.models.common import PollCategory
from app.schemas.common import ApiResponse
from app.schemas.crawler import ExportIn
from app.services import export_service

router = APIRouter(prefix="/admin/export", tags=["墨麟书院·导出"])


@router.post("/votes")
async def export_votes(payload: ExportIn, db: Db, _=require_operator_dep) -> Response:
    start = datetime.fromisoformat(payload.start_date)
    end = datetime.fromisoformat(payload.end_date)
    body, media_type, suffix = await export_service.export_votes(
        db, start, end, payload.category, payload.format
    )
    filename = f"goqd_votes_{payload.start_date}_{payload.end_date}{suffix}"
    return Response(
        content=body,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/preview")
async def preview(
    db: Db,
    _=require_operator_dep,
    start_date: str = "",
    end_date: str = "",
    category: str | None = None,
) -> ApiResponse:
    start = datetime.fromisoformat(start_date) if start_date else None
    end = datetime.fromisoformat(end_date) if end_date else None
    cat = PollCategory(category) if category else None
    rows = await export_service.collect_poll_stats(db, start, end, cat)
    return ApiResponse.ok({"total": len(rows), "rows": rows[:50]})
