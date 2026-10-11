"""投票中心 Schema（PRD §3.1 V-001 ~ V-204）。"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from app.models.common import PollCategory, PollStatus, PollTag, PollType


class OptionIn(BaseModel):
    label: str = Field(..., min_length=1, max_length=200)
    sort_order: int = 0


class OptionOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    label: str
    sort_order: int = 0
    vote_count: int = 0
    percent: float = 0.0
    # 排序题平均名次
    avg_rank: Optional[float] = None


class PollCreateIn(BaseModel):
    title: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    poll_type: PollType = PollType.SINGLE
    category: Optional[PollCategory] = None
    tag: Optional[PollTag] = None
    topic_tags: Optional[str] = Field(None, max_length=300)
    options: List[OptionIn] = Field(default_factory=list)
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    allow_change: bool = True
    anonymous: bool = False
    max_choices: Optional[int] = None
    max_participants: Optional[int] = None  # 接龙
    cover_url: Optional[str] = None
    crawler_item_id: Optional[int] = None
    # 定时发布：draft 保存 / scheduled 定时上线 / active 立即上线
    publish_mode: str = Field("draft", pattern="^(draft|scheduled|active)$")
    scheduled_at: Optional[datetime] = None


class PollOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    title: str
    description: Optional[str] = None
    poll_type: PollType
    status: PollStatus
    category: Optional[PollCategory] = None
    tag: Optional[PollTag] = None
    topic_tags: Optional[str] = None
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    allow_change: bool = True
    anonymous: bool = False
    max_choices: Optional[int] = None
    max_participants: Optional[int] = None
    cover_url: Optional[str] = None
    created_by: Optional[int] = None
    created_at: Optional[datetime] = None
    # 运行时字段（由 service 填充）
    options: List[OptionOut] = []
    total_votes: int = 0
    my_choice: Optional[List[int]] = None  # 已投选项 id
    has_voted: bool = False
    is_changed: bool = False
    remaining_seconds: Optional[int] = None
    participant_count: int = 0  # 接龙已报名人数


class CastVoteIn(BaseModel):
    option_ids: List[int] = Field(..., min_length=1)

    @field_validator("option_ids")
    @classmethod
    def _non_empty(cls, v: List[int]) -> List[int]:
        if not v:
            raise ValueError("至少选择一个选项")
        return v


class VoteResultOut(BaseModel):
    poll_id: int
    title: str
    total_votes: int
    options: List[OptionOut] = []
    # V-006 脱敏分组统计
    breakdown: Optional[dict] = None
    closed: bool = False


class CommentIn(BaseModel):
    content: str = Field(..., min_length=1, max_length=200)


class CommentOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    poll_id: int
    user_id: int
    author_nickname: Optional[str] = None
    content: str
    like_count: int = 0
    created_at: Optional[datetime] = None
    liked_by_me: bool = False


class PollStatsOut(BaseModel):
    """墨麟书院数据沉淀视图（ML-O-001）。"""

    poll_id: int
    title: str
    category: Optional[str] = None
    option_labels: List[str] = []
    vote_counts: List[int] = []
    total_participants: int = 0
    start_at: Optional[str] = None
    end_at: Optional[str] = None
