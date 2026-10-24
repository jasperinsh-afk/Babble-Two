"""可视化站点内容后台，按当前角色限制内容与操作。"""
from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.cloudbase_client import CloudbaseError
from app.config import SERVER_ROOT, settings
from app.core.admin_gate import AdminPrincipal, current_admin, require_super_admin
from app.repository.base import BalaError
from app.services import content_service

router = APIRouter(prefix="/admin/web/content", include_in_schema=False)
templates = Jinja2Templates(directory=str(SERVER_ROOT / "admin-web" / "templates"))


def same_origin(request: Request) -> None:
    origin = request.headers.get("origin")
    if origin and urlparse(origin).netloc != request.url.netloc:
        raise HTTPException(status_code=403, detail="仅允许同源后台操作")


def failure(exc: Exception) -> HTTPException:
    if isinstance(exc, BalaError):
        return HTTPException(status_code=exc.http_status, detail=exc.message)
    if isinstance(exc, CloudbaseError):
        return HTTPException(status_code=502, detail=str(exc))
    return HTTPException(status_code=500, detail="内容保存失败，请稍后重试")


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def content_page(request: Request, principal: AdminPrincipal = Depends(current_admin)):
    schemas = content_service.accessible_collections(principal)
    return templates.TemplateResponse(
        "content.html",
        {
            "request": request,
            "nav": "content",
            "mode": settings.web_data_mode,
            "schemas": schemas,
            "section_types": content_service.SECTION_TYPES,
            "can_create": principal.role != "reviewer",
            # 版主默认进入「我的社团」，避免落在暂无归属数据的活动列表
            "initial_view": (
                "layout"
                if principal.is_admin
                else ("clubs" if principal.role == "club_moderator" else next(iter(schemas)))
            ),
        },
    )


@router.get("/api/layout")
async def read_layout(_=Depends(require_super_admin)):
    try:
        return {"ok": True, "data": await content_service.get_layout()}
    except Exception as exc:
        raise failure(exc) from exc


@router.put("/api/layout", dependencies=[Depends(same_origin)])
async def write_layout(payload: dict[str, Any] = Body(...), _=Depends(require_super_admin)):
    try:
        return {"ok": True, "data": await content_service.save_layout(payload)}
    except Exception as exc:
        raise failure(exc) from exc


@router.get("/api/{collection}")
async def read_documents(collection: str, principal: AdminPrincipal = Depends(current_admin)):
    try:
        schema = content_service.schema_for(collection, principal)
        defaults = content_service.new_document(collection, principal) if schema["canCreate"] else {}
        return {"ok": True, "data": {
            "items": await content_service.list_documents(collection, principal),
            "schema": schema,
            "defaults": defaults,
        }}
    except Exception as exc:
        raise failure(exc) from exc


@router.post("/api/{collection}", dependencies=[Depends(same_origin)])
async def create_document(collection: str, payload: dict[str, Any] = Body(...), principal: AdminPrincipal = Depends(current_admin)):
    try:
        return {"ok": True, "data": await content_service.save_document(collection, payload, principal=principal)}
    except Exception as exc:
        raise failure(exc) from exc


@router.put("/api/{collection}/{doc_id}", dependencies=[Depends(same_origin)])
async def update_document(collection: str, doc_id: str, payload: dict[str, Any] = Body(...), principal: AdminPrincipal = Depends(current_admin)):
    try:
        return {"ok": True, "data": await content_service.save_document(collection, payload, doc_id, principal)}
    except Exception as exc:
        raise failure(exc) from exc


@router.delete("/api/{collection}/{doc_id}", dependencies=[Depends(same_origin)])
async def remove_document(collection: str, doc_id: str, principal: AdminPrincipal = Depends(current_admin)):
    try:
        await content_service.delete_document(collection, doc_id, principal)
        return {"ok": True, "data": {"deleted": doc_id}}
    except Exception as exc:
        raise failure(exc) from exc
