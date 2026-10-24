"""墨麟书院 · 数据输出层：脱敏导出（PRD ML-O-001 ~ ML-O-005）。

数据来自微信云开发数据库 polls 集合（经 cloudbase_client 读取），
导出内容不含任何 openid / 用户信息。

POST /api/v1/admin/export/votes      导出 CSV / Excel
GET  /api/v1/admin/export/preview    预览聚合统计（不落文件）
"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from app.core.admin_gate import require_super_admin
from app.schemas.common import ApiResponse
from app.schemas.crawler import ExportIn
from app.services import export_service

router = APIRouter(prefix="/admin/export", tags=["墨麟书院·导出"])


@router.post("/votes")
async def export_votes(payload: ExportIn, _=Depends(require_super_admin)) -> Response:
    start = datetime.fromisoformat(payload.start_date)
    end = datetime.fromisoformat(payload.end_date)
    body, media_type, suffix = await export_service.export_votes(
        start, end, payload.category, payload.format
    )
    filename = f"goqd_votes_{payload.start_date}_{payload.end_date}{suffix}"
    return Response(
        content=body,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/preview")
async def preview(
    _=Depends(require_super_admin),
    start_date: str = "",
    end_date: str = "",
    category: str | None = None,
) -> ApiResponse:
    start = datetime.fromisoformat(start_date) if start_date else None
    end = datetime.fromisoformat(end_date) if end_date else None
    rows = await export_service.collect_poll_stats(start, end, category)
    return ApiResponse.ok({"total": len(rows), "rows": rows[:50]})
