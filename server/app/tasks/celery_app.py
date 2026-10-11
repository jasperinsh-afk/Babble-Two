"""Celery 应用（生产环境定时任务）。

开发期用 APScheduler（app/crawler/scheduler.py），生产切 Celery + Redis。
任务：爬虫抓取 / 投票生命周期 / 活动提醒 / 数据导出
"""
from __future__ import annotations

import asyncio
import logging

from celery import Celery
from celery.schedules import crontab

from app.config import settings

logger = logging.getLogger(__name__)

celery_app = Celery(
    "goqd",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.crawler_task", "app.tasks.poll_task", "app.tasks.push_task"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    beat_schedule={
        "crawl-morning": {
            "task": "app.tasks.crawler_task.crawl",
            "schedule": crontab(hour=9, minute=0),
        },
        "crawl-afternoon": {
            "task": "app.tasks.crawler_task.crawl",
            "schedule": crontab(hour=15, minute=0),
        },
        "poll-lifecycle": {
            "task": "app.tasks.poll_task.lifecycle",
            "schedule": 60.0,
        },
        "event-reminder": {
            "task": "app.tasks.push_task.event_reminder",
            "schedule": 600.0,
        },
    },
)


def run_async(coro):
    """在 Celery worker 中安全执行协程。"""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()
