"""社团广场 Schema（PRD §3.2 C-001 ~ C-204）。"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from app.models.common import ClubCategory


class ClubApplyIn(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=200)
    logo_url: Optional[str] = None
    category: ClubCategory = ClubCategory.OTHER
    contact: Optional[str] = Field(None, max_length=100)


class ClubOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    name: str
    description: Optional[str] = None
    logo_url: Optional[str] = None
    cover_url: Optional[str] = None
    category: ClubCategory
    is_verified: bool = False
    member_count: int = 0
    follower_count: int = 0
    heat_score: int = 0
    is_member: bool = False
    is_following: bool = False


class ClubDetailOut(ClubOut):
    review_status: Optional[str] = None
    my_role: Optional[str] = None
    created_at: Optional[datetime] = None


class PostCreateIn(BaseModel):
    title: Optional[str] = Field(None, max_length=200)
    content: str = Field(..., min_length=1, max_length=2000)
    images: List[str] = Field(default_factory=list)
    is_pinned: bool = False

    @field_validator("images")
    @classmethod
    def _max_nine(cls, v: List[str]) -> List[str]:
        if len(v) > 9:
            raise ValueError("图片最多 9 张")
        return v


class PostOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    club_id: int
    club_name: Optional[str] = None
    author_id: int
    author_nickname: Optional[str] = None
    title: Optional[str] = None
    content: str
    images: Optional[str] = None
    status: Optional[str] = None
    is_pinned: bool = False
    like_count: int = 0
    comment_count: int = 0
    created_at: Optional[datetime] = None
    liked_by_me: bool = False
