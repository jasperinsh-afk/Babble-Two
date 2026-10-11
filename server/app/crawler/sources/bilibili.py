"""B 站热门（httpx）。"""
from __future__ import annotations

from typing import List

from app.crawler.sources.base import BaseSource, RawTopic


class BilibiliSource(BaseSource):
    name = "bilibili"
    source_desc = "B站热门"

    async def fetch(self) -> List[RawTopic]:
        data = await self._get_json(
            "https://api.bilibili.com/x/web-interface/popular",
            params={"ps": 30, "pn": 1},
        )
        out = []
        for item in (data.get("data") or {}).get("list", [])[:30]:
            out.append(
                RawTopic(
                    title=item.get("title", ""),
                    url=f"https://www.bilibili.com/video/{item.get('bvid', '')}",
                    summary=(item.get("desc") or "")[:200],
                    heat_score=int(item.get("view", 0) or 0),
                    raw=item,
                )
            )
        return [t for t in out if t.title]
