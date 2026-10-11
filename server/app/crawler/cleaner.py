"""数据清洗与跨平台去重（技术架构文档 §5.2）。"""
from __future__ import annotations

import hashlib
import re
from typing import List

from app.crawler.sources.base import RawTopic


def normalize(title: str) -> str:
    """去除标点符号、空白与话题符号，便于相似话题合并。"""
    t = re.sub(r"[#\[\]【】「」“”\"'’‘]", "", title or "")
    t = re.sub(r"\s+", "", t)
    return t.strip()


def fingerprint(title: str) -> str:
    return hashlib.sha256(normalize(title).encode("utf-8")).hexdigest()


def dedupe(topics: List[RawTopic], existing_fps: set) -> List[RawTopic]:
    """跨平台相似话题合并，保留热度最高来源。"""
    buckets: dict = {}
    for t in topics:
        if not t.title:
            continue
        fp = fingerprint(t.title)
        if fp in existing_fps:
            continue
        if fp not in buckets or t.heat_score > buckets[fp].heat_score:
            buckets[fp] = t
    return sorted(buckets.values(), key=lambda x: x.heat_score, reverse=True)
