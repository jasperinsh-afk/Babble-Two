"""微博热搜（动态渲染，优先 Playwright，缺失时降级为 httpx 抓移动端接口）。"""
from __future__ import annotations

import logging
from typing import List

from app.crawler.sources.base import BaseSource, RawTopic

logger = logging.getLogger(__name__)


class WeiboSource(BaseSource):
    name = "weibo"
    source_desc = "微博热搜"

    async def fetch(self) -> List[RawTopic]:
        try:
            return await self._fetch_playwright()
        except Exception as exc:  # noqa: BLE001
            logger.info("Playwright 不可用，降级为 httpx: %s", exc)
            return await self._fetch_httpx()

    async def _fetch_httpx(self) -> List[RawTopic]:
        data = await self._get_json("https://weibo.com/ajax/side/hotSearch")
        out = []
        for item in (data.get("data") or {}).get("realtime", [])[:30]:
            out.append(
                RawTopic(
                    title=item.get("word", ""),
                    url=f"https://s.weibo.com/weibo?q=%23{item.get('word', '')}%23",
                    summary=item.get("note", ""),
                    heat_score=int(item.get("num", 0) or 0),
                    raw=item,
                )
            )
        return [t for t in out if t.title]

    async def _fetch_playwright(self) -> List[RawTopic]:
        from playwright.async_api import async_playwright  # type: ignore

        out: List[RawTopic] = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto("https://s.weibo.com/top/summary", timeout=30000)
            await page.wait_for_timeout(2000)
            items = await page.query_selector_all("tbody tr")
            for row in items[:30]:
                title_el = await row.query_selector("td.td-02 a")
                if not title_el:
                    continue
                title = (await title_el.inner_text()).strip()
                num_el = await row.query_selector("td.td-02 span")
                num = (await num_el.inner_text()).strip() if num_el else "0"
                out.append(
                    RawTopic(
                        title=title,
                        url=f"https://s.weibo.com/weibo?q=%23{title}%23",
                        heat_score=int(num) if num.isdigit() else 0,
                    )
                )
            await browser.close()
        return [t for t in out if t.title]
