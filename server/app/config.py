"""全局配置（Pydantic Settings，环境变量 / .env 驱动）。

技术架构文档 §3.1 —— app/config.py
"""
from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ── 应用 ──
    APP_NAME: str = "七德通 GoQD"
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

    # ── OMEGA / NFC ──
    NFC_BASE_URL: str = "https://goqd.com/nfc"
    IOS_APP_STORE_URL: str = "https://apps.apple.com/app/goqd/idXXXXXXXX"
    ANDROID_STORE_URL: str = "https://www.coolapk.com/apk/com.goqd.app"

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


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
