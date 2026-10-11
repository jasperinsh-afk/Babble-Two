"""墨麟书院 · 数据输入层调度（技术架构文档 §5.1）。

定时抓取(9:00/15:00) → 多源采集 → 清洗去重 → 敏感词过滤
  → LLM 适龄判断 → 候选话题池(Top20) → 运营选题 → LLM 草稿 → 人工终审发布
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.crawler.ai_selector import judge_topics
from app.crawler.cleaner import dedupe, fingerprint
from app.crawler.sources import build_sources
from app.models.common import CrawlerItemStatus, CrawlerSource
from app.models.crawler import CrawlerItem
from app.services import moderation_service

logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def _existing_fingerprints(db: AsyncSession, hours: int = 24) -> set:
    since = _now() - timedelta(hours=hours)
    rows = (
        await db.execute(select(CrawlerItem.fingerprint).where(CrawlerItem.crawled_at >= since))
    ).scalars().all()
    return {r for r in rows if r}


async def run_once(db: AsyncSession) -> dict:
    """执行一轮完整抓取 + 三层过滤。"""
    if not settings.CRAWLER_ENABLED:
        return {"skipped": True, "reason": "爬虫未启用（CRAWLER_ENABLED=false）"}

    sources = build_sources(settings.crawler_source_list)
    if not sources:
        return {"skipped": True, "reason": "无可用数据源"}

    fetched: List = []
    for s in sources:
        topics = await s.safe_fetch()
        for t in topics:
            t.raw["source"] = s.name
        fetched.extend(topics)
        logger.info("[%s] 抓取到 %s 条", s.name, len(topics))

    existing = await _existing_fingerprints(db)
    candidates = dedupe(fetched, existing)

    stats = {"fetched": len(fetched), "deduped": len(candidates), "blocked_word": 0, "blocked_llm": 0, "saved": 0}

    # 第一层：敏感词过滤
    survivors = []
    for t in candidates:
        res = await moderation_service.filter_crawler_topic(db, t.title, t.summary)
        if not res.passed:
            stats["blocked_word"] += 1
            continue
        survivors.append(t)

    # 第二层：LLM 适龄判断（批量）
    judgments = await judge_topics(survivors)

    pool_size = settings.CANDIDATE_POOL_SIZE
    for t, j in zip(survivors, judgments):
        suitable = j.get("suitable")
        if suitable is False:
            stats["blocked_llm"] += 1
            status = CrawlerItemStatus.FILTERED
        elif suitable is None:
            # LLM 不可用 → 转人工队列，不丢弃
            status = CrawlerItemStatus.PENDING
        else:
            status = CrawlerItemStatus.PENDING

        if status == CrawlerItemStatus.FILTERED and len(judgments) > pool_size:
            # 被过滤的仍入库留痕，便于运营复盘
            pass

        src_name = t.raw.get("source", "weibo")
        try:
            source_enum = CrawlerSource(src_name)
        except ValueError:
            source_enum = CrawlerSource.WEIBO

        db.add(
            CrawlerItem(
                source=source_enum,
                title=t.title[:500],
                url=t.url,
                summary=(t.summary or "")[:500],
                heat_score=int(t.heat_score or 0),
                raw_data=str(t.raw)[:2000],
                status=status,
                filter_reason=j.get("reason", ""),
                risk_level=j.get("risk_level"),
                llm_suggestion=j.get("suggestion", ""),
                fingerprint=fingerprint(t.title),
                crawled_at=_now(),
            )
        )
        stats["saved"] += 1

    await db.flush()
    return stats


async def get_candidate_pool(db: AsyncSession, limit: int = 20) -> List[CrawlerItem]:
    return (
        await db.execute(
            select(CrawlerItem)
            .where(CrawlerItem.status == CrawlerItemStatus.PENDING)
            .order_by(CrawlerItem.heat_score.desc())
            .limit(limit)
        )
    ).scalars().all()


async def check_alerts(db: AsyncSession) -> dict:
    """ML-I-007 爬虫异常告警：连续 2 轮无新候选话题。"""
    since = _now() - timedelta(hours=6)
    n = (
        await db.execute(
            select(CrawlerItem.id).where(CrawlerItem.crawled_at >= since)
        )
    ).scalars().all()
    pending = (
        await db.execute(
            select(CrawlerItem.id).where(
                CrawlerItem.status == CrawlerItemStatus.PENDING, CrawlerItem.crawled_at >= since
            )
        )
    ).scalars().all()
    alert = len(n) == 0 or len(pending) == 0
    return {
        "alert": alert,
        "recent_items": len(n),
        "pending_items": len(pending),
        "message": "连续多轮无新候选话题，请检查爬虫" if alert else "",
    }
