"""定时任务调度：爬虫抓取 / 投票上线 / 投票关闭 / 活动提醒。

APScheduler（MVP）；生产可切 Celery（见 app/tasks/）。
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import settings
from app.core.database import SessionLocal

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def job_crawl() -> None:
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


async def job_poll_lifecycle() -> None:
    """定时发布已审核投票 + 到期自动关闭。"""
    async with SessionLocal() as db:
        from app.services import vote_service

        try:
            activated = await vote_service.activate_scheduled_polls(db)
            closed = await vote_service.close_expired_polls(db)
            await db.commit()
            if activated or closed:
                logger.info("投票生命周期: 上线 %s，关闭 %s", activated, closed)
        except Exception as exc:  # noqa: BLE001
            logger.error("投票生命周期任务失败: %s", exc)


async def job_event_reminder() -> None:
    """活动开始前 1 小时推送提醒（E-106）。"""
    async with SessionLocal() as db:
        from sqlalchemy import select

        from app.models.common import ReviewStatus
        from app.models.event import Event
        from app.services import push_service

        try:
            target = _now() + timedelta(hours=1)
            rows = (
                await db.execute(
                    select(Event).where(
                        Event.review_status == ReviewStatus.APPROVED,
                        Event.start_at <= target + timedelta(minutes=5),
                        Event.start_at >= target - timedelta(minutes=5),
                    )
                )
            ).scalars().all()
            for ev in rows:
                await push_service.notify_event_reminder(db, ev.id, ev.title)
            await db.commit()
        except Exception as exc:  # noqa: BLE001
            logger.error("活动提醒任务失败: %s", exc)


def start_scheduler() -> None:
    if scheduler.running:
        return
    for hour in settings.crawler_hours:
        scheduler.add_job(job_crawl, "cron", hour=hour, minute=0, id=f"crawl_{hour}")
    scheduler.add_job(job_poll_lifecycle, "interval", minutes=1, id="poll_lifecycle")
    scheduler.add_job(job_event_reminder, "interval", minutes=10, id="event_reminder")
    scheduler.start()
    logger.info("定时任务已启动：爬虫 %s 点，投票生命周期每分钟", settings.crawler_hours)


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
