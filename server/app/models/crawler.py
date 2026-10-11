"""墨麟书院 · 输入层：爬虫候选话题 + 敏感词库。

技术架构文档 §4.2 crawler_items / sensitive_words + PRD ML-I-001~007。
"""
from __future__ import annotations

from sqlalchemy import Boolean, DateTime, Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.common import Base, CrawlerItemStatus, CrawlerSource


class CrawlerItem(Base):
    __tablename__ = "crawler_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[CrawlerSource] = mapped_column(Enum(CrawlerSource), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    heat_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    raw_data: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON 快照

    status: Mapped[CrawlerItemStatus] = mapped_column(
        Enum(CrawlerItemStatus), default=CrawlerItemStatus.PENDING, nullable=False, index=True
    )
    filter_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    risk_level: Mapped[str | None] = mapped_column(String(20), nullable=True)  # none/low/medium/high
    llm_suggestion: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # 人工终审（ML-I-003 第三层）
    reviewed_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # 去重指纹：标题哈希，24h 内不重复入库
    fingerprint: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    crawled_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)


class SensitiveWord(Base):
    """PRD §4.3 敏感词库，支持运营后台动态增删（Aho-Corasick 热更新）。"""

    __tablename__ = "sensitive_words"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    word: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str] = mapped_column(String(50), default="custom", nullable=False)
    # political / violence / sexual / religious / custom
    severity: Mapped[str] = mapped_column(String(20), default="block", nullable=False)  # block / warn
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)


# ── 基础词库种子（PRD §4.3）──

DEFAULT_SENSITIVE_WORDS = [
    ("测试敏感词A", "custom", "block"),
    ("测试敏感词B", "custom", "block"),
    ("代写论文", "custom", "block"),
    ("代考", "custom", "block"),
    ("校园贷", "custom", "block"),
]
