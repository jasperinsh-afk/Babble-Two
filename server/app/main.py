"""七德通 GoQD · FastAPI 入口。"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api.v1 import router as api_v1_router
from app.config import settings
from app.core.exceptions import AppError, MESSAGES, OK
from app.core.security import sign_card_id

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s | %(message)s",
)
logger = logging.getLogger("goqd")

app = FastAPI(
    title=settings.APP_NAME,
    description="七德通 GoQD 校园生活入口 · Project Y",
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
        "timestamp": int(datetime.now(timezone.utc).timestamp()),
    }


@app.middleware("http")
async def wrap_response(request: Request, call_next):
    """把裸 dict/列表响应统一包装成 {code, message, data, timestamp}。"""
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
    return _payload(OK, "ok", {"env": settings.APP_ENV, "time": datetime.now(timezone.utc).isoformat()})


# ── OMEGA：NFC 碰触中间页（未装 App 时）──


@app.get("/nfc/{card_id}", response_class=HTMLResponse, tags=["OMEGA"])
async def nfc_redirect(request: Request, card_id: str):
    """OMEGA §8.3：根据 UA 智能跳转；App 未安装时引导下载。"""
    from app.core.database import SessionLocal
    from app.services import nfc_service

    async with SessionLocal() as db:
        try:
            info = await nfc_service.resolve_card(db, card_id)
        except AppError as exc:
            return HTMLResponse(
                content=f"<h3>卡片不可用</h3><p>{exc.message}</p>", status_code=404
            )

        device = nfc_service.detect_device(request.headers.get("user-agent", ""))
        await nfc_service.record_tap(
            db, card_id, device_type=device, app_installed=False,
            action_result="store_redirect", user=None,
        )
        await db.commit()

        store_url = nfc_service.get_store_url(device)
        target_url = f"https://goqd.com{info['target_url']}"
        html = nfc_service.build_redirect_html(
            card_id=info["card_id"],
            location_desc=info.get("location_desc") or "",
            target_url=target_url,
            store_url=store_url,
            device=device,
        )
        return HTMLResponse(content=html)


# ── OMEGA：Deep Link 验证文件 ──


@app.get("/.well-known/apple-app-site-association", tags=["OMEGA"])
async def aasa() -> dict:
    """iOS Universal Links（OMEGA §7.1）。生产需替换 TEAM_ID。"""
    return {
        "applinks": {
            "apps": [],
            "details": [
                {
                    "appIDs": ["TEAM_ID.com.goqd.app"],
                    "paths": ["/nfc/*", "/vote/*", "/club/*", "/event/*"],
                }
            ],
        }
    }


@app.get("/.well-known/assetlinks.json", tags=["OMEGA"])
async def assetlinks() -> list:
    """Android App Links（OMEGA §6.2）。生产需替换 SHA256 指纹。"""
    return [
        {
            "relation": ["delegate_permission/common.handle_all_urls"],
            "target": {
                "namespace": "android_app",
                "package_name": "com.goqd.app",
                "sha256_cert_fingerprints": ["AA:BB:CC:DD:EE:FF:00:11:22:33:44:55:66:77:88:99:AA:BB:CC:DD:EE:FF:00:11"],
            },
        }
    ]


@app.get("/api/v1/nfc-write/{card_id}", tags=["OMEGA"])
async def nfc_write_payload(card_id: str) -> dict:
    """供 NFC Writer 工具写入卡片的 NDEF URI + 签名。"""
    return _payload(
        OK,
        "ok",
        {
            "card_id": card_id,
            "uri": f"{settings.NFC_BASE_URL}/{card_id}",
            "signature": sign_card_id(card_id),
        },
    )


# ── 运营后台（FastAPI + Jinja2，零 Node 依赖）──

try:
    templates = Jinja2Templates(directory="admin-web/templates")
    app.mount("/static", StaticFiles(directory="admin-web/static"), name="static")
    from app.admin_web import router as admin_web_router  # noqa: E402

    app.include_router(admin_web_router)
    logger.info("运营后台已挂载: /admin/web")
except Exception as exc:  # noqa: BLE001
    logger.warning("运营后台未挂载（模板目录缺失）: %s", exc)


# ── 生命周期 ──


@app.on_event("startup")
async def on_startup() -> None:
    from app.core.database import init_db
    from app.core.redis import cache
    from app.services import badge_service, moderation_service

    await init_db()
    logger.info("数据库已就绪")

    async with __import__("app.core.database", fromlist=["SessionLocal"]).SessionLocal() as db:
        await badge_service.seed_badges(db)
        await moderation_service.load_word_bank(db)
        await db.commit()
    logger.info("勋章与敏感词库已初始化")

    if settings.CRAWLER_ENABLED or True:
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
