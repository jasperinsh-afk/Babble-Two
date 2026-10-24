"""Celery 任务：爬虫抓取 + 异常告警 + 候选入云。

墨麟书院输入层的落库终点已改为微信云开发数据库：
本地 PostgreSQL 只保存爬虫候选池（crawler_items）与敏感词，
通过审核/生成的草稿经 cloudbase_client 推送到云数据库供小程序端读取。
"""
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


@celery_app.task(name="app.tasks.crawler_task.push_candidates")
def push_candidates(limit: int = 20):
    """把候选池中新抓取的话题同步到云数据库（草稿态，等待运营终审）。"""
    from sqlalchemy import desc, select

    from app import cloudbase_client
    from app.models.common import CrawlerItemStatus
    from app.models.crawler import CrawlerItem

    async def _job():
        async with SessionLocal() as db:
            items = (
                await db.execute(
                    select(CrawlerItem)
                    .where(CrawlerItem.status == CrawlerItemStatus.PENDING)
                    .order_by(desc(CrawlerItem.heat_score))
                    .limit(limit)
                )
            ).scalars().all()
            snapshot = [
                {
                    "crawlerItemId": it.id,
                    "title": it.title,
                    "summary": it.summary or "",
                    "source": it.source.value if hasattr(it.source, "value") else str(it.source),
                    "heatScore": it.heat_score,
                    "riskLevel": it.risk_level,
                }
                for it in items
            ]

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
                print(f"[crawler_task] 候选入云失败: {exc}")
        return {"pushed": pushed, "total": len(snapshot)}

    return run_async(_job())
