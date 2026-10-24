"""定时任务调度：爬虫抓取 / 候选入云 / 投票生命周期。

APScheduler（MVP）；生产可切 Celery（见 app/tasks/）。
改造后：投票与活动数据位于微信云开发数据库，生命周期由本服务经
cloudbase_client 维护；本地库只保留爬虫候选池与敏感词。
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app import cloudbase_client
from app.config import settings
from app.core.database import SessionLocal

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _parse_dt(value) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=None)
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


async def job_crawl() -> None:
    """墨麟书院输入层：抓取候选话题到本地候选池。"""
    if not settings.CRAWLER_ENABLED:
        return
    async with SessionLocal() as db:
        from app.services import crawler_service

        try:
            stats = await crawler_service.run_once(db)
            await db.commit()
            logger.info("爬虫任务完成: %s", stats)
        except Exception as exc:  # noqa: BLE001
            logger.error("爬虫任务失败: %s", exc)


async def job_push_candidates() -> None:
    """把候选池中的新话题同步到云数据库（草稿态，待运营终审）。"""
    if not settings.CRAWLER_ENABLED:
        return
    from sqlalchemy import desc, select

    from app.models.common import CrawlerItemStatus
    from app.models.crawler import CrawlerItem

    try:
        async with SessionLocal() as db:
            items = (
                await db.execute(
                    select(CrawlerItem)
                    .where(CrawlerItem.status == CrawlerItemStatus.PENDING)
                    .order_by(desc(CrawlerItem.heat_score))
                    .limit(20)
                )
            ).scalars().all()
            snapshot = [
                {
                    "crawlerItemId": it.id,
                    "title": it.title,
                    "summary": it.summary or "",
                    "heatScore": it.heat_score,
                    "riskLevel": it.risk_level,
                }
                for it in items
            ]
    except Exception as exc:  # noqa: BLE001
        logger.error("候选池读取失败: %s", exc)
        return

    pushed = 0
    for row in snapshot:
        try:
            await cloudbase_client.upsert_draft(
                {
                    "source": "crawler",
                    "title": row["title"],
                    "description": row["summary"],
                    "tag": "news",
                    "pollType": "single",
                    "options": [],
                    "crawlerItemId": row["crawlerItemId"],
                    "heatScore": row["heatScore"],
                    "riskLevel": row["riskLevel"],
                    "reviewStatus": "pending",
                    "status": "draft",
                }
            )
            pushed += 1
        except Exception as exc:  # noqa: BLE001
            logger.error("候选入云失败: %s", exc)
    if pushed:
        logger.info("候选入云完成: %s 条", pushed)


async def job_poll_lifecycle() -> None:
    """云数据库投票生命周期：到点上线 + 到期关闭（服务端时间为准）。"""
    now = _now()

    try:
        polls = await cloudbase_client.query("polls", order_by="createdAt", limit=100)
    except Exception as exc:  # noqa: BLE001
        logger.error("投票生命周期：读取失败 %s", exc)
        return

    activated = closed = 0
    for p in polls:
        pid = p.get("_id")
        status = p.get("status")
        start = _parse_dt(p.get("startAt"))
        end = _parse_dt(p.get("endAt"))
        try:
            if status == "scheduled" and start and start <= now:
                await cloudbase_client.update(
                    "polls", {"_id": pid}, {"status": "active", "updatedAt": now.isoformat()}
                )
                activated += 1
            elif status == "active" and end and end <= now:
                await cloudbase_client.update(
                    "polls", {"_id": pid}, {"status": "closed", "updatedAt": now.isoformat()}
                )
                closed += 1
        except Exception as exc:  # noqa: BLE001
            logger.error("投票生命周期：更新 %s 失败 %s", pid, exc)

    if activated or closed:
        logger.info("投票生命周期: 上线 %s，关闭 %s", activated, closed)


def start_scheduler() -> None:
    if scheduler.running:
        return
    for hour in settings.crawler_hours:
        scheduler.add_job(job_crawl, "cron", hour=hour, minute=0, id=f"crawl_{hour}")
        scheduler.add_job(
            job_push_candidates, "cron", hour=hour, minute=30, id=f"push_candidates_{hour}"
        )
    scheduler.add_job(job_poll_lifecycle, "interval", minutes=5, id="poll_lifecycle")
    scheduler.start()
    logger.info("定时任务已启动：爬虫 %s 点，投票生命周期每 5 分钟", settings.crawler_hours)


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
