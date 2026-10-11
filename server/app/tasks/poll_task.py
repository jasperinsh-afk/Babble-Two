"""Celery 任务：投票定时上线 + 到期关闭。"""
from __future__ import annotations

from app.core.database import SessionLocal
from app.tasks.celery_app import celery_app, run_async


@celery_app.task(name="app.tasks.poll_task.lifecycle")
def lifecycle():
    async def _job():
        async with SessionLocal() as db:
            from app.services import vote_service

            activated = await vote_service.activate_scheduled_polls(db)
            closed = await vote_service.close_expired_polls(db)
            await db.commit()
            return {"activated": activated, "closed": closed}

    return run_async(_job())
