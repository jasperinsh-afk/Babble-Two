"""把云函数种子数据导入网页版本地 SQLite（无微信凭据时的开发数据源）。

用法（任意目录均可，路径按仓库结构解析）：
    python scripts/seed_to_sqlite.py                 # 空库时自动导入
    python scripts/seed_to_sqlite.py --reset         # 清空后重新导入（库文件被服务占用时同样可用）
    python scripts/seed_to_sqlite.py --keep-dates    # 保留种子原始日期
    python scripts/seed_to_sqlite.py --db ./data/dev.db --seed ../path/seed.json
"""
from __future__ import annotations

import argparse
import asyncio
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings  # noqa: E402
from app.repository.local_store import DocumentStore  # noqa: E402


async def main() -> None:
    parser = argparse.ArgumentParser(description="叭啦网页版本地种子导入")
    parser.add_argument("--db", default=settings.web_local_db_path)
    parser.add_argument("--seed", default=settings.web_seed_file_path)
    parser.add_argument("--reset", action="store_true", help="删除现有本地库后重建")
    parser.add_argument(
        "--keep-dates",
        action="store_true",
        help="保留种子原始日期（默认整体平移，让最新一条落在今天 + 10 天，便于演示进行中的投票）",
    )
    args = parser.parse_args()

    db_path = Path(args.db)
    if args.reset and db_path.exists():
        # 直接删文件在服务进程占用时会失败（Windows 共享冲突），改为清空文档表后重灌
        con = sqlite3.connect(str(db_path))
        try:
            con.execute("DELETE FROM documents")
            con.commit()
            print(f"已清空旧数据 {db_path}")
        except sqlite3.OperationalError:
            pass  # 表尚不存在，ensure_ready 会创建
        finally:
            con.close()

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
