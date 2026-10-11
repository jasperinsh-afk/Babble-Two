"""Celery 任务：爬虫抓取 + 异常告警。"""
from __future__ import annotations

from app.core.database import SessionLocal
from app.tasks.celery_app import celery_app, run_async


@celery_app.task(name="app.tasks.crawler_task.crawl")
def crawl():
    async def _job():
        async with SessionLocal() as db:
            from app.services import crawler_service

            stats = await crawler_service.run_once(db)
            await db.commit()
            return stats

    return run_async(_job())


@celery_app.task(name="app.tasks.crawler_task.alert")
def alert():
    async def _job():
        async with SessionLocal() as db:
            from app.services import crawler_service

            return await crawler_service.check_alerts(db)

    return run_async(_job())
