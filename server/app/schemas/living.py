"""住宿生活 Schema（PRD §3.4 L-001 ~ L-103）。"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from app.models.common import DormChannelScope, LostFoundKind


class ChannelOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    name: str
    scope: DormChannelScope
    building: Optional[str] = None
    floor: Optional[str] = None
    room: Optional[str] = None


class DormPostIn(BaseModel):
    channel_id: int
    content: str = Field(..., min_length=1, max_length=2000)
    images: List[str] = Field(default_factory=list)

    @field_validator("images")
    @classmethod
    def _max_three(cls, v: List[str]) -> List[str]:
        if len(v) > 3:
            raise ValueError("图片最多 3 张")
        return v


class DormPostOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    channel_id: int
    author_id: int
    author_nickname: Optional[str] = None
    content: str
    images: Optional[str] = None
    like_count: int = 0
    reply_count: int = 0
    created_at: Optional[datetime] = None
    liked_by_me: bool = False


class DormReplyIn(BaseModel):
    content: str = Field(..., min_length=1, max_length=500)


class DormReplyOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    post_id: int
    user_id: int
    author_nickname: Optional[str] = None
    content: str
    created_at: Optional[datetime] = None


class LostFoundIn(BaseModel):
    kind: LostFoundKind = LostFoundKind.LOST
    title: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = None
    location: Optional[str] = Field(None, max_length=200)
    contact: Optional[str] = Field(None, max_length=100)
    images: List[str] = Field(default_factory=list)


class LostFoundOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    kind: LostFoundKind
    title: str
    description: Optional[str] = None
    location: Optional[str] = None
    contact: Optional[str] = None
    images: Optional[str] = None
    user_id: int
    is_resolved: bool = False
    created_at: Optional[datetime] = None


class SecondHandIn(BaseModel):
    title: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = None
    price: Optional[int] = Field(None, ge=0)
    contact: Optional[str] = Field(None, max_length=100)
    images: List[str] = Field(default_factory=list)


class SecondHandOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    title: str
    description: Optional[str] = None
    price: Optional[int] = None
    images: Optional[str] = None
    contact: Optional[str] = None
    user_id: int
    is_sold: bool = False
    created_at: Optional[datetime] = None
