"""缓存层：Redis 优先，缺失时自动降级为进程内 LRU。

技术架构文档 §4.4 —— Redis 缓存设计
    vote:{id}:counts     投票选项实时计数 (Hash)
    vote:{id}:result     投票结果缓存 5min
    nfc:{card_uid}       NFC 卡片信息缓存 1h
    rate:{ip}            IP 限流计数器 1min
    user:{id}:push:{date} 每日推送计数
"""
from __future__ import annotations

import json
import time
from collections import OrderedDict
from typing import Any, Dict, List, Optional

from app.config import settings


class MemoryCache:
    """进程内 LRU + TTL 缓存（Redis 不可用时的降级实现）。"""

    def __init__(self, max_size: int = 2000):
        self._store: "OrderedDict[str, tuple[float, Any]]" = OrderedDict()
        self._hashes: Dict[str, Dict[str, str]] = {}
        self.max_size = max_size

    def _purge(self) -> None:
        now = time.time()
        for k in [k for k, (exp, _) in self._store.items() if exp and exp < now]:
            self._store.pop(k, None)
        while len(self._store) > self.max_size:
            self._store.popitem(last=False)

    async def get(self, key: str) -> Optional[str]:
        item = self._store.get(key)
        if item is None:
            return None
        exp, val = item
        if exp and exp < time.time():
            self._store.pop(key, None)
            return None
        self._store.move_to_end(key)
        return val

    async def set(self, key: str, value: Any, ex: int = 0) -> None:
        self._store[key] = (time.time() + ex if ex else 0, str(value))
        self._purge()

    async def delete(self, key: str) -> None:
        self._store.pop(key, None)
        self._hashes.pop(key, None)

    async def incr(self, key: str, amount: int = 1) -> int:
        cur = int(await self.get(key) or 0) + amount
        await self.set(key, cur)
        return cur

    async def expire(self, key: str, ex: int) -> None:
        item = self._store.get(key)
        if item:
            self._store[key] = (time.time() + ex, item[1])

    async def hincrby(self, key: str, field: str, amount: int = 1) -> int:
        h = self._hashes.setdefault(key, {})
        cur = int(h.get(field, 0)) + amount
        h[field] = str(cur)
        return cur

    async def hgetall(self, key: str) -> Dict[str, str]:
        return dict(self._hashes.get(key, {}))

    async def hset(self, key: str, field: str, value: Any) -> None:
        self._hashes.setdefault(key, {})[field] = str(value)

    async def keys(self, pattern: str) -> List[str]:
        prefix = pattern.rstrip("*")
        return [k for k in list(self._store) + list(self._hashes) if k.startswith(prefix)]


class RedisCache:
    """Redis 实现（与 MemoryCache 同接口）。"""

    def __init__(self, url: str):
        import redis.asyncio as aioredis  # 延迟导入，未安装也不影响启动

        self._client = aioredis.from_url(url, decode_responses=True, encoding="utf-8")

    async def get(self, key: str) -> Optional[str]:
        return await self._client.get(key)

    async def set(self, key: str, value: Any, ex: int = 0) -> None:
        await self._client.set(key, value, ex=ex or None)

    async def delete(self, key: str) -> None:
        await self._client.delete(key)

    async def incr(self, key: str, amount: int = 1) -> int:
        return await self._client.incrby(key, amount)

    async def expire(self, key: str, ex: int) -> None:
        await self._client.expire(key, ex)

    async def hincrby(self, key: str, field: str, amount: int = 1) -> int:
        return await self._client.hincrby(key, field, amount)

    async def hgetall(self, key: str) -> Dict[str, str]:
        return await self._client.hgetall(key)

    async def hset(self, key: str, field: str, value: Any) -> None:
        await self._client.hset(key, field, value)

    async def keys(self, pattern: str) -> List[str]:
        return await self._client.keys(pattern)


def _build_cache():
    if settings.REDIS_ENABLED:
        try:
            return RedisCache(settings.REDIS_URL)
        except Exception:
            pass
    return MemoryCache()


cache = _build_cache()


# ── 语义化封装 ──


async def cache_get_json(key: str) -> Optional[Any]:
    raw = await cache.get(key)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return None


async def cache_set_json(key: str, value: Any, ex: int = 0) -> None:
    await cache.set(key, json.dumps(value, ensure_ascii=False, default=str), ex=ex)


async def bump_vote_count(poll_id: int, option_id: int, amount: int = 1) -> int:
    """投票计数 Redis INCR（技术架构文档 §4.4）。"""
    return await cache.hincrby(f"vote:{poll_id}:counts", str(option_id), amount)


async def read_vote_counts(poll_id: int) -> Dict[str, int]:
    raw = await cache.hgetall(f"vote:{poll_id}:counts")
    return {k: int(v) for k, v in raw.items() if str(v).lstrip("-").isdigit()}


async def clear_vote_counts(poll_id: int) -> None:
    await cache.delete(f"vote:{poll_id}:counts")
    await cache.delete(f"vote:{poll_id}:result")


async def rate_limit(key: str, limit: int, window: int) -> bool:
    """简单限流计数器：返回 True 表示放行。"""
    cur = await cache.incr(key, 1)
    if cur == 1:
        await cache.expire(key, window)
    return cur <= limit
