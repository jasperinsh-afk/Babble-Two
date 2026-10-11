"""央视新闻 RSS Feed（httpx）。"""
from __future__ import annotations

import re
from typing import List

from app.crawler.sources.base import BaseSource, RawTopic


class CctvSource(BaseSource):
    name = "cctv"
    source_desc = "央视新闻"

    async def fetch(self) -> List[RawTopic]:
        text = await self._get_text("https://news.cctv.com/rss/china.xml")
        out: List[RawTopic] = []
        for m in re.finditer(r"<item>(.*?)</item>", text, re.DOTALL):
            block = m.group(1)
            title_m = re.search(r"<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>", block, re.DOTALL)
            link_m = re.search(r"<link>(.*?)</link>", block, re.DOTALL)
            desc_m = re.search(
                r"<description>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</description>", block, re.DOTALL
            )
            if not title_m:
                continue
            out.append(
                RawTopic(
                    title=title_m.group(1).strip(),
                    url=(link_m.group(1).strip() if link_m else ""),
                    summary=(desc_m.group(1).strip()[:200] if desc_m else ""),
                    heat_score=0,
                )
            )
            if len(out) >= 30:
                break
        return [t for t in out if t.title]
