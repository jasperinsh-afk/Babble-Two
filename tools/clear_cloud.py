"""清空微信云数据库中的演示数据（只删文档，不删集合）。

放在 tools/ 下运行，避免落在 server/ 目录触发 uvicorn --reload 热重载。
运行方式（工作目录必须是 server，以便加载 .env）：
    cd server
    .venv\\Scripts\\python.exe ..\\tools\\clear_cloud.py
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + os.sep + "server")

from app.cloudbase_client import delete, query  # noqa: E402

COLLECTIONS = [
    "banners",
    "polls",
    "clubs",
    "club_posts",
    "events",
    "dorm_channels",
    "dorm_posts",
    "lost_found",
    "second_hand",
    "nfc_cards",
    "badges",
]


async def main():
    for collection in COLLECTIONS:
        try:
            rows = await query(collection, {}, limit=100)
        except Exception:
            print(f"{collection:14s} 集合不存在，跳过")
            continue
        removed = 0
        for row in rows:
            try:
                await delete(collection, {"_id": row["_id"]})
                removed += 1
            except Exception as exc:
                print(f"   ! {collection}/{row.get('_id')} 删除失败: {str(exc)[:80]}")
        print(f"{collection:14s} 删除 {removed}/{len(rows)}")

    print()
    print("清空完成（集合保留，文档已删除）")


if __name__ == "__main__":
    asyncio.run(main())
