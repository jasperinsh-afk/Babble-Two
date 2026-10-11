"""Prompt 版本管理（《Prompt 工程文档》§6.1）。

所有 Prompt 集中管理，支持版本追踪与迭代回滚。
"""
from __future__ import annotations

from typing import Dict

from app.prompts.topic_filter import (
    TOPIC_FILTER_BATCH_USER,
    TOPIC_FILTER_SYSTEM,
    TOPIC_FILTER_USER,
)
from app.prompts.draft_generator import (
    CAMPUS_TOPIC_SYSTEM,
    DRAFT_SYSTEM,
    DRAFT_USER,
    DRAFT_USER_MULTI,
)
from app.prompts.poll_classifier import CLASSIFY_SYSTEM, CLASSIFY_USER
from app.prompts.ugc_reviewer import UGC_REVIEW_SYSTEM, UGC_REVIEW_USER

PROMPT_VERSIONS: Dict[str, dict] = {
    "topic_filter": {
        "version": "1.2",
        "system": TOPIC_FILTER_SYSTEM,
        "user_template": TOPIC_FILTER_USER,
        "batch_template": TOPIC_FILTER_BATCH_USER,
        "updated_at": "2026-10-01",
        "changelog": "增加商业营销拦截规则",
        "model": "select",
        "temperature": 0.1,
    },
    "draft_generator": {
        "version": "1.0",
        "system": DRAFT_SYSTEM,
        "user_template": DRAFT_USER,
        "multi_template": DRAFT_USER_MULTI,
        "campus_system": CAMPUS_TOPIC_SYSTEM,
        "updated_at": "2026-09-15",
        "changelog": "初始版本",
        "model": "generate",
        "temperature": 0.7,
    },
    "poll_classifier": {
        "version": "1.0",
        "system": CLASSIFY_SYSTEM,
        "user_template": CLASSIFY_USER,
        "updated_at": "2026-09-15",
        "changelog": "初始版本",
        "model": "generate",
        "temperature": 0.1,
    },
    "ugc_reviewer": {
        "version": "1.0",
        "system": UGC_REVIEW_SYSTEM,
        "user_template": UGC_REVIEW_USER,
        "updated_at": "2026-09-15",
        "changelog": "初始版本",
        "model": "select",
        "temperature": 0.1,
    },
}
