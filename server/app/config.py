"""全局配置（Pydantic Settings，环境变量 / .env 驱动）。

技术架构文档 §3.1 —— app/config.py
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict

# 固定目录：无论从哪里启动服务，路径都按仓库结构解析，不跟随工作目录
SERVER_ROOT = Path(__file__).resolve().parents[1]  # .../bala-miniapp/server
PROJECT_ROOT = Path(__file__).resolve().parents[2]  # .../bala-miniapp


def resolve_path(value: str) -> str:
    """相对路径统一按 server 根目录解析（等价于此前的「在 server 目录下启动」）。"""
    path = Path(value)
    if path.is_absolute():
        return path.as_posix()
    return (SERVER_ROOT / path).resolve().as_posix()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ── 应用 ──
    APP_NAME: str = "叭啦 Babble"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # ── 数据库 ──
    # 开发默认 SQLite，生产切 PostgreSQL: postgresql+asyncpg://user:pwd@host:5432/goqd
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/goqd.db"
    DB_ECHO: bool = False

    # ── 安全 ──
    SECRET_KEY: str = "dev-only-secret-change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # ── Redis ──
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_ENABLED: bool = False

    # ── CORS ──
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173,http://localhost:8000"

    # ── 学校身份校验 ──
    SCHOOL_EMAIL_DOMAIN: str = "@qd.baoan.edu.cn"
    STUDENT_ID_PATTERN: str = r"^\d{8}$"

    # ── 墨麟书院 · 输入层（爬虫）──
    CRAWLER_ENABLED: bool = False
    CRAWLER_SCHEDULE_HOURS: str = "9,15"
    CRAWLER_SOURCES: str = "weibo,zhihu,bilibili,baidu,cctv"
    CANDIDATE_POOL_SIZE: int = 20

    # ── 通义千问 LLM ──
    DASHSCOPE_API_KEY: str = ""
    QWEN_MODEL_SELECT: str = "qwen-max"
    QWEN_MODEL_GENERATE: str = "qwen-plus"
    LLM_TIMEOUT: int = 10
    LLM_ENABLED: bool = False
    LLM_CACHE_TTL: int = 86400  # 相同话题 24h 内不重复调用

    # ── 微信云开发（小程序端数据在此，运营侧经 HTTP API 读写）──
    WECHAT_APPID: str = ""
    WECHAT_SECRET: str = ""
    WECHAT_CLOUD_ENV: str = ""
    # 与云函数 adminIngest 的环境变量保持一致，用于运营侧写库鉴权
    INGEST_TOKEN: str = ""
    # 运营后台访问口令（C 端已无登录，运营后台独立口令保护）
    ADMIN_WEB_TOKEN: str = "change-me-admin-token"
    ADMIN_SESSION_MINUTES: int = 480
    CLUB_MODERATOR_AUTH_CODE: str = "0923"
    REVIEWER_AUTH_CODE: str = "2012"

    # ── 网页版 bala-web ──
    # auto：配置了 WECHAT_SECRET 就走云数据库，否则回落本地 SQLite
    WEB_DATA_MODE: str = "auto"  # auto / cloud / local
    WEB_LOCAL_DB: str = "./data/bala_web.db"
    WEB_SEED_FILE: str = "../cloudfunctions/seedImport/seed_data.json"
    # 本地种子日期整体平移，让最新一条落在「今天 + 10 天」，保证演示时投票/活动仍在进行
    WEB_SEED_SHIFT_DATES: bool = True
    WEB_CACHE_ENABLED: bool = True
    # 云模式写入闸门：云函数未部署 resolveOpenid 版本前，网页写入会产生 _openid 为空
    # 的脏数据。部署 vote/club/event/scan/me 五个云函数后再置为 true。
    WEB_CLOUD_WRITE_ENABLED: bool = False

    # ── 推送 ──
    JPUSH_APP_KEY: str = ""
    JPUSH_MASTER_SECRET: str = ""
    PUSH_ENABLED: bool = False
    PUSH_QUIET_HOURS_START: int = 22
    PUSH_QUIET_HOURS_END: int = 7
    PUSH_DAILY_LIMIT: int = 5

    # ── 对象存储 ──
    OSS_ENDPOINT: str = ""
    OSS_BUCKET: str = ""
    OSS_ACCESS_KEY_ID: str = ""
    OSS_ACCESS_KEY_SECRET: str = ""

    # ── 内容安全 ──
    MODERATION_AUTO_APPROVE: bool = False

    # ── 限流开关（开发/测试环境建议关闭）──
    RATE_LIMIT_ENABLED: bool = False

    # ── 分页 ──
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 50

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def crawler_hours(self) -> List[int]:
        return [int(h.strip()) for h in self.CRAWLER_SCHEDULE_HOURS.split(",") if h.strip()]

    @property
    def crawler_source_list(self) -> List[str]:
        return [s.strip() for s in self.CRAWLER_SOURCES.split(",") if s.strip()]

    @property
    def is_production(self) -> bool:
        return self.APP_ENV.lower() == "production"

    @property
    def db_is_sqlite(self) -> bool:
        return self.DATABASE_URL.startswith("sqlite")

    @property
    def web_data_mode(self) -> str:
        """网页版实际数据源：cloud（微信云数据库）或 local（SQLite 种子）。"""
        mode = (self.WEB_DATA_MODE or "auto").lower()
        if mode in ("cloud", "local"):
            return mode
        return "cloud" if self.WECHAT_SECRET and self.WECHAT_CLOUD_ENV else "local"

    @property
    def database_url(self) -> str:
        """SQLite 相对路径按 server 根目录解析：换启动目录也不会连到空库。"""
        url = self.DATABASE_URL
        if url.startswith("sqlite") and "///" in url:
            prefix, _, rest = url.partition("///")
            if rest and rest != ":memory:" and not Path(rest).is_absolute():
                return f"{prefix}///{resolve_path(rest)}"
        return url

    @property
    def web_local_db_path(self) -> str:
        """网页版本地库绝对路径。"""
        return resolve_path(self.WEB_LOCAL_DB)

    @property
    def web_seed_file_path(self) -> str:
        """网页版种子数据绝对路径。"""
        return resolve_path(self.WEB_SEED_FILE)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
