"""知乎热榜（httpx）。"""
from __future__ import annotations

from typing import List

from app.crawler.sources.base import BaseSource, RawTopic


class ZhihuSource(BaseSource):
    name = "zhihu"
    source_desc = "知乎热榜"

    async def fetch(self) -> List[RawTopic]:
        data = await self._get_json(
            "https://www.zhihu.com/api/v3/feed/topstory/hot-lists/total",
            params={"limit": 50, "desktop": "true"},
        )
        out = []
        for item in data.get("data", [])[:30]:
            target = item.get("target", {}) or {}
            out.append(
                RawTopic(
                    title=item.get("title") or target.get("title", ""),
                    url=f"https://www.zhihu.com/question/{target.get('id')}"
                    if target.get("id")
                    else "",
                    summary=(target.get("excerpt") or "")[:200],
                    heat_score=int(item.get("detail_text", "0").replace("万热度", "0000") or 0),
                    raw=item,
                )
            )
        return [t for t in out if t.title]
