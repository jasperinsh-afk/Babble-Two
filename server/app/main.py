"""叭啦 Babble · FastAPI 入口。"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api.v1 import router as api_v1_router
from app.config import settings
from app.core.exceptions import AppError, MESSAGES, OK

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s | %(message)s",
)
logger = logging.getLogger("goqd")

app = FastAPI(
    title=settings.APP_NAME,
    description="叭啦 Babble 校园生活入口 · Project Y",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ──
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.settings = settings


# ── 统一响应包装 + 异常处理 ──


def _payload(code: int, message: str, data=None) -> dict:
    return {
        "code": code,
        "message": message,
        "data": data,
        "timestamp": int(datetime.now(timezone.utc).replace(tzinfo=None).timestamp()),
    }


@app.middleware("http")
async def wrap_response(request: Request, call_next):
    """把裸 dict/列表响应统一包装成 {code, message, data, timestamp}。"""
    if not hasattr(request.state, "principal"):
        # 后台模板依赖 principal，先置空，避免未走鉴权依赖的页面渲染时报属性错误
        request.state.principal = None
    response = await call_next(request)
    return response


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(
        status_code=exc.http_status,
        content=_payload(exc.code, exc.message, exc.data),
    )


@app.exception_handler(Exception)
async def unhandled_handler(request: Request, exc: Exception):
    logger.exception("未处理异常: %s", exc)
    return JSONResponse(
        status_code=500,
        content=_payload(1099, MESSAGES.get(1099, "服务器内部错误")),
    )


# ── 路由 ──

app.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)


@app.get("/healthz", tags=["系统"])
async def healthz() -> dict:
    return _payload(OK, "ok", {"env": settings.APP_ENV, "time": datetime.now(timezone.utc).replace(tzinfo=None).isoformat()})


# ── 运营后台（FastAPI + Jinja2，零 Node 依赖）──

try:
    ADMIN_WEB_DIR = Path(__file__).resolve().parent.parent / "admin-web"
    templates = Jinja2Templates(directory=str(ADMIN_WEB_DIR / "templates"))
    app.mount("/static", StaticFiles(directory=str(ADMIN_WEB_DIR / "static")), name="static")
    from app.admin_web import router as admin_web_router  # noqa: E402
    from app.admin_content import router as admin_content_router  # noqa: E402

    app.include_router(admin_web_router)
    app.include_router(admin_content_router)

    @app.get("/admin", include_in_schema=False)
    async def admin_entry():
        return RedirectResponse(url="/admin/web/content", status_code=307)

    logger.info("运营后台已挂载: /admin")
except Exception as exc:  # noqa: BLE001
    logger.warning("运营后台未挂载（模板目录缺失）: %s", exc)


# ── 同域网页版：构建后由 FastAPI 提供 assets 与 SPA history fallback ──
# 网页客户端构建产物：优先仓库内 bala-web/dist，兼容旧的同级目录布局
_WEB_DIST_CANDIDATES = [
    Path(__file__).resolve().parents[2] / "bala-web" / "dist",
    Path(__file__).resolve().parents[3] / "bala-web" / "dist",
]
FRONTEND_DIST = next(
    (path for path in _WEB_DIST_CANDIDATES if (path / "index.html").is_file()),
    _WEB_DIST_CANDIDATES[0],
)
if (FRONTEND_DIST / "index.html").is_file():
    if (FRONTEND_DIST / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="web-assets")

    @app.get("/{path:path}", include_in_schema=False)
    async def web_spa(path: str):
        if path.startswith("api/"):
            return JSONResponse(status_code=404, content={"ok": False, "message": "接口不存在"})
        return FileResponse(FRONTEND_DIST / "index.html")
    logger.info("网页版已挂载: / （%s）", FRONTEND_DIST)


# ── 生命周期 ──


@app.on_event("startup")
async def on_startup() -> None:
    from app.core.database import init_db
    from app.services import moderation_service

    await init_db()
    logger.info("数据库已就绪")

    async with __import__("app.core.database", fromlist=["SessionLocal"]).SessionLocal() as db:
        await moderation_service.load_word_bank(db)
        await db.commit()
    logger.info("敏感词库已初始化（勋章与业务数据由云开发数据库承载）")

    if settings.CRAWLER_ENABLED:
        try:
            from app.crawler.scheduler import start_scheduler

            start_scheduler()
        except Exception as exc:  # noqa: BLE001
            logger.warning("定时任务未启动: %s", exc)


@app.on_event("shutdown")
async def on_shutdown() -> None:
    from app.core.database import close_db

    try:
        from app.crawler.scheduler import stop_scheduler

        stop_scheduler()
    except Exception:  # noqa: BLE001
        pass
    await close_db()
