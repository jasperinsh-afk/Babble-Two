"""把云函数种子数据导入网页版本地 SQLite（无微信凭据时的开发数据源）。

用法（在 server 目录下）：
    python scripts/seed_to_sqlite.py                 # 空库时自动导入
    python scripts/seed_to_sqlite.py --reset         # 清空后重新导入
    python scripts/seed_to_sqlite.py --keep-dates    # 保留种子原始日期
    python scripts/seed_to_sqlite.py --db ./data/dev.db --seed ../path/seed.json
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings  # noqa: E402
from app.repository.local_store import DocumentStore  # noqa: E402


async def main() -> None:
    parser = argparse.ArgumentParser(description="叭啦网页版本地种子导入")
    parser.add_argument("--db", default=settings.WEB_LOCAL_DB)
    parser.add_argument("--seed", default=settings.WEB_SEED_FILE)
    parser.add_argument("--reset", action="store_true", help="删除现有本地库后重建")
    parser.add_argument(
        "--keep-dates",
        action="store_true",
        help="保留种子原始日期（默认整体平移，让最新一条落在今天 + 10 天，便于演示进行中的投票）",
    )
    args = parser.parse_args()

    db_path = Path(args.db)
    if args.reset and db_path.exists():
        db_path.unlink()
        print(f"已删除旧库 {db_path}")

    store = DocumentStore(
        str(db_path), seed_file=args.seed, shift_dates=not args.keep_dates
    )
    await store.ensure_ready()
    async with store.conn.execute(
        "SELECT collection, COUNT(*) FROM documents GROUP BY collection ORDER BY collection"
    ) as cur:
        rows = await cur.fetchall()
    for name, count in rows:
        print(f"  {name:<16} {count} 条")
    print(f"本地库就绪：{db_path.resolve()}")
    await store.close()


if __name__ == "__main__":
    asyncio.run(main())
