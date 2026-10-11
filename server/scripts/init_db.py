"""初始化数据库（建表 + 勋章 + 敏感词库）。

用法：
    python scripts/init_db.py
    python scripts/init_db.py --drop    # 先删表再建
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import SessionLocal, engine, init_db  # noqa: E402
from app.models.common import Base  # noqa: E402
from app.services import badge_service, moderation_service  # noqa: E402


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--drop", action="store_true")
    args = ap.parse_args()

    if args.drop:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        print("✓ 已删除全部数据表")

    await init_db()
    print("✓ 数据表已创建")

    async with SessionLocal() as db:
        await badge_service.seed_badges(db)
        await moderation_service.load_word_bank(db)
        await db.commit()
    print("✓ 勋章与敏感词库已初始化")


if __name__ == "__main__":
    asyncio.run(main())
