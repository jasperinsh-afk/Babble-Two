"""Prompt-2：投票草稿生成 + Prompt-3 自动分类。

《Prompt 工程文档》§3 / §4
"""
from __future__ import annotations

import json
import logging
from typing import List

from app.config import settings
from app.crawler.classifier import classify_poll
from app.models.crawler import CrawlerItem
from app.prompts.draft_generator import (
    CAMPUS_TOPIC_SYSTEM,
    CAMPUS_TOPIC_USER,
    DRAFT_SYSTEM,
    DRAFT_USER,
    DRAFT_USER_MULTI,
)
from app.services.llm_service import safe_llm_call

logger = logging.getLogger(__name__)

VALID_TYPES = {"single", "multi", "pk", "ranking"}


def _fallback_draft(item: CrawlerItem) -> dict:
    """LLM 不可用时给出保守草稿，交由人工修改。"""
    return {
        "title": item.title[:50],
        "poll_type": "single",
        "options": ["支持", "反对"],
        "description": (item.summary or "")[:100],
        "design_note": "LLM 不可用，请人工完善草稿",
        "recommend": True,
        "category": None,
    }


async def generate_drafts(
    db, item: CrawlerItem, operator_note: str = "", variants: int = 3
) -> List[dict]:
    """生成 1~3 个不同角度的投票方案。"""
    if not settings.LLM_ENABLED:
        return [_fallback_draft(item)]

    if variants > 1:
        prompt = DRAFT_USER_MULTI.format(
            title=item.title,
            source=item.source.value,
            summary=(item.summary or "")[:200],
        )
        fallback = [_fallback_draft(item)]
        parsed = await safe_llm_call(
            prompt=prompt,
            system=DRAFT_SYSTEM,
            fallback={"items": fallback},
            model=settings.QWEN_MODEL_GENERATE,
            temperature=0.7,
        )
        items = parsed.get("items") if isinstance(parsed, dict) else parsed
        if not isinstance(items, list):
            items = fallback
    else:
        prompt = DRAFT_USER.format(
            title=item.title,
            source=item.source.value,
            summary=(item.summary or "")[:200],
            heat_score=item.heat_score,
            operator_note=operator_note or "",
        )
        parsed = await safe_llm_call(
            prompt=prompt,
            system=DRAFT_SYSTEM,
            fallback=_fallback_draft(item),
            model=settings.QWEN_MODEL_GENERATE,
            temperature=0.7,
        )
        items = [parsed]

    drafts: List[dict] = []
    for d in items[:3]:
        ptype = str(d.get("poll_type", "single")).lower()
        if ptype not in VALID_TYPES:
            ptype = "single"
        options = [str(o) for o in d.get("options", [])][:8]
        if len(options) < 2:
            options = ["支持", "反对"]
        title = str(d.get("title", item.title))[:50]
        category = await classify_poll(db, title, options, str(d.get("description", ""))[:100])
        drafts.append(
            {
                "title": title,
                "poll_type": ptype,
                "options": options,
                "description": str(d.get("description", ""))[:200],
                "design_note": str(d.get("design_note", ""))[:100],
                "recommend": bool(d.get("recommend", False)),
                "category": category,
            }
        )
    if drafts and not any(d["recommend"] for d in drafts):
        drafts[0]["recommend"] = True
    return drafts


async def generate_campus_draft(topic_direction: str, preferred_type: str = "") -> dict:
    """§3.7 人工非时事话题辅助生成。"""
    prompt = CAMPUS_TOPIC_USER.format(
        topic_direction=topic_direction, preferred_type=preferred_type or "自选"
    )
    fallback = {
        "title": topic_direction[:30],
        "poll_type": preferred_type or "single",
        "options": ["选项1", "选项2"],
        "description": "",
        "design_note": "LLM 不可用，请人工完善",
    }
    return await safe_llm_call(
        prompt=prompt,
        system=CAMPUS_TOPIC_SYSTEM,
        fallback=fallback,
        model=settings.QWEN_MODEL_GENERATE,
        temperature=0.7,
    )
