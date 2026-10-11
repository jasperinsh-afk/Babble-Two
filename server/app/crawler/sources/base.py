"""爬虫数据源基类：重试、UA 轮换、指数退避、单源降级。

技术架构文档 §5.5 爬虫运维。
"""
from __future__ import annotations

import asyncio
import logging
import random
from dataclasses import dataclass, field
from typing import List, Optional

import httpx

logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
]


@dataclass
class RawTopic:
    title: str
    url: str = ""
    summary: str = ""
    heat_score: int = 0
    raw: dict = field(default_factory=dict)


class BaseSource:
    """所有数据源的公共行为。"""

    name: str = "base"
    source_desc: str = ""
    max_retries: int = 3

    def _headers(self) -> dict:
        return {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept-Language": "zh-CN,zh;q=0.9",
        }

    async def fetch(self) -> List[RawTopic]:
        raise NotImplementedError

    async def safe_fetch(self) -> List[RawTopic]:
        """失败自动重试 3 次，指数退避；最终失败返回空列表（不影响其他源）。"""
        delay = 1.0
        for attempt in range(1, self.max_retries + 1):
            try:
                return await self.fetch()
            except Exception as exc:  # noqa: BLE001
                logger.warning("[%s] 第 %s 次抓取失败: %s", self.name, attempt, exc)
                if attempt < self.max_retries:
                    await asyncio.sleep(delay)
                    delay *= 2
        logger.error("[%s] 抓取彻底失败，本次跳过", self.name)
        return []

    async def _get_json(self, url: str, params: dict | None = None, timeout: int = 10):
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            resp = await client.get(url, params=params, headers=self._headers())
            resp.raise_for_status()
            return resp.json()

    async def _get_text(self, url: str, timeout: int = 10) -> str:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            resp = await client.get(url, headers=self._headers())
            resp.raise_for_status()
            return resp.text
