"""百度热点（httpx）。"""
from __future__ import annotations

from typing import List

from app.crawler.sources.base import BaseSource, RawTopic


class BaiduSource(BaseSource):
    name = "baidu"
    source_desc = "百度热点"

    async def fetch(self) -> List[RawTopic]:
        text = await self._get_text("https://top.baidu.com/board?tab=realtime")
        out: List[RawTopic] = []
        # 页面内嵌 JSON，取标题与热度
        import json
        import re

        for m in re.finditer(r'"word"\s*:\s*"(.*?)"', text):
            title = m.group(1)
            if title and len(out) < 30:
                out.append(RawTopic(title=title, url="https://top.baidu.com/board?tab=realtime"))
        return out
