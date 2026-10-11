"""墨麟书院 Schema：爬虫候选池 + 审核 + 数据导出。

PRD §3.6（ML-I-001~007 / ML-O-001~005）。
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.common import CrawlerSource, PollCategory


class CrawlerItemOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    source: CrawlerSource
    title: str
    url: Optional[str] = None
    summary: Optional[str] = None
    heat_score: int = 0
    status: Optional[str] = None
    filter_reason: Optional[str] = None
    risk_level: Optional[str] = None
    llm_suggestion: Optional[str] = None
    crawled_at: Optional[datetime] = None


class CandidateReviewIn(BaseModel):
    status: str = Field(..., pattern="^(approved|rejected)$")
    note: Optional[str] = Field(None, max_length=200)


class DraftGenerateIn(BaseModel):
    crawler_item_id: int
    operator_note: Optional[str] = Field(None, max_length=200)
    variants: int = Field(3, ge=1, le=3)


class DraftOut(BaseModel):
    title: str
    poll_type: str
    options: List[str] = []
    description: Optional[str] = None
    design_note: Optional[str] = None
    recommend: bool = False
    category: Optional[PollCategory] = None


class PollReviewIn(BaseModel):
    status: str = Field(..., pattern="^(approved|rejected)$")
    note: Optional[str] = Field(None, max_length=200)


class SensitiveWordIn(BaseModel):
    word: str = Field(..., min_length=1, max_length=100)
    category: str = Field("custom", max_length=50)
    severity: str = Field("block", pattern="^(block|warn)$")


class ExportIn(BaseModel):
    start_date: str
    end_date: str
    category: Optional[PollCategory] = None
    format: str = Field("csv", pattern="^(csv|excel)$")


class ExportRowOut(BaseModel):
    poll_id: int
    title: str
    category: Optional[str] = None
    option_labels: List[str] = []
    vote_counts: List[int] = []
    total_participants: int = 0
    start_at: Optional[str] = None
    end_at: Optional[str] = None
