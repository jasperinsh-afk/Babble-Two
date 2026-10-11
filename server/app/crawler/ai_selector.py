"""AI 选题：Prompt-1 话题适合度判断（批量模式）。

《Prompt 工程文档》§2.7 —— 每次 5-10 个话题一起判断，节省 token。
"""
from __future__ import annotations

import json
import logging
from typing import List

from app.config import settings
from app.crawler.sources.base import RawTopic
from app.prompts.topic_filter import TOPIC_FILTER_BATCH_USER, TOPIC_FILTER_SYSTEM
from app.services.llm_service import safe_llm_call

logger = logging.getLogger(__name__)

BATCH_SIZE = 8


async def judge_topics(topics: List[RawTopic]) -> List[dict]:
    """返回与输入一一对应的判断结果。

    LLM 不可用时全部标记 needs_manual_review（降级而非丢弃，Prompt 文档 §1 通用约定）。
    """
    results: List[dict] = []
    for i in range(0, len(topics), BATCH_SIZE):
        batch = topics[i : i + BATCH_SIZE]
        results.extend(await _judge_batch(batch))
    return results


async def _judge_batch(batch: List[RawTopic]) -> List[dict]:
    payload = [
        {"id": idx + 1, "title": t.title, "source": t.__class__.__name__, "summary": t.summary}
        for idx, t in enumerate(batch)
    ]
    prompt = TOPIC_FILTER_BATCH_USER.format(
        topics_json=json.dumps(payload, ensure_ascii=False)
    )
    fallback = [
        {
            "id": idx + 1,
            "suitable": None,
            "reason": "LLM 不可用，需人工审核",
            "risk_level": "unknown",
            "suggestion": "",
        }
        for idx in range(len(batch))
    ]

    parsed = await safe_llm_call(
        prompt=prompt,
        system=TOPIC_FILTER_SYSTEM,
        fallback={"items": fallback},
        model=settings.QWEN_MODEL_SELECT,
        temperature=0.1,
    )

    items = parsed.get("items") if isinstance(parsed, dict) else parsed
    if not isinstance(items, list) or len(items) != len(batch):
        return fallback

    normalized = []
    for idx, item in enumerate(items):
        normalized.append(
            {
                "id": idx + 1,
                "suitable": item.get("suitable"),
                "reason": str(item.get("reason", ""))[:40],
                "risk_level": item.get("risk_level", "unknown"),
                "suggestion": str(item.get("suggestion", ""))[:60],
            }
        )
    return normalized
