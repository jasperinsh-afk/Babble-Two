"""Prompt-3：投票自动分类（墨麟书院数据沉淀标签）。

《Prompt 工程文档》§4 —— 低置信度转人工确认。
"""
from __future__ import annotations

import logging
from typing import List, Optional

from app.config import settings
from app.models.common import PollCategory
from app.prompts.poll_classifier import CLASSIFY_SYSTEM, CLASSIFY_USER
from app.services.llm_service import safe_llm_call

logger = logging.getLogger(__name__)

VALID = {c.value for c in PollCategory}


async def classify_poll(
    db, title: str, options: List[str], description: str = ""
) -> Optional[str]:
    """返回分类值字符串；LLM 不可用或解析失败返回 None。"""
    if not settings.LLM_ENABLED:
        return None

    prompt = CLASSIFY_USER.format(
        poll_title=title,
        options_list="、".join(options),
        description=description,
    )
    fallback = {"category": None, "confidence": 0.0, "reason": "LLM 不可用"}
    parsed = await safe_llm_call(
        prompt=prompt,
        system=CLASSIFY_SYSTEM,
        fallback=fallback,
        model=settings.QWEN_MODEL_GENERATE,
        temperature=0.1,
    )
    category = parsed.get("category")
    confidence = float(parsed.get("confidence", 0) or 0)
    if category not in VALID:
        return None
    # 低置信度仍返回建议值，但调用方可标记 needs_confirm
    logger.info("classify title=%s -> %s (conf=%.2f)", title[:20], category, confidence)
    return category
