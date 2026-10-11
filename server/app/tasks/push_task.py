"""Celery 任务：活动提醒推送。"""
from __future__ import annotations

from app.core.database import SessionLocal
from app.tasks.celery_app import celery_app, run_async


@celery_app.task(name="app.tasks.push_task.event_reminder")
def event_reminder():
    from app.crawler.scheduler import job_event_reminder

    return run_async(job_event_reminder())
