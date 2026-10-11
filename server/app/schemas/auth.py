"""认证与用户相关 Schema（PRD U-001 ~ U-009）。"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.common import UserRole


class SendCodeIn(BaseModel):
    email: EmailStr


class RegisterIn(BaseModel):
    student_id: str = Field(..., min_length=4, max_length=20)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=64)
    nickname: str = Field(..., min_length=1, max_length=50)
    email_code: str = Field(..., min_length=6, max_length=6)
    grade: Optional[str] = Field(None, max_length=10)
    dormitory: Optional[str] = Field(None, max_length=20)

    @field_validator("password")
    @classmethod
    def _strong(cls, v: str) -> str:
        import re

        if len(v) < 8 or not re.search(r"[A-Za-z]", v) or not re.search(r"\d", v):
            raise ValueError("密码至少 8 位，且包含字母和数字")
        return v


class LoginIn(BaseModel):
    student_id: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshIn(BaseModel):
    refresh_token: str


class UserBrief(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    nickname: str
    avatar_url: Optional[str] = None
    grade: Optional[str] = None
    role: UserRole = UserRole.STUDENT


class UserOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    student_id: str
    email: str
    nickname: str
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    grade: Optional[str] = None
    dormitory: Optional[str] = None
    role: UserRole = UserRole.STUDENT
    is_verified: bool = False
    created_at: Optional[datetime] = None


class UserUpdateIn(BaseModel):
    nickname: Optional[str] = Field(None, max_length=50)
    avatar_url: Optional[str] = None
    bio: Optional[str] = Field(None, max_length=200)
    grade: Optional[str] = Field(None, max_length=10)
    dormitory: Optional[str] = Field(None, max_length=20)


class PushPrefIn(BaseModel):
    push_daily_poll: Optional[bool] = None
    push_poll_result: Optional[bool] = None
    push_event_remind: Optional[bool] = None
    push_club_update: Optional[bool] = None


class NotificationOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    type: str
    title: str
    content: Optional[str] = None
    ref_type: Optional[str] = None
    ref_id: Optional[int] = None
    is_read: bool = False
    created_at: Optional[datetime] = None


class BadgeOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    code: str
    name: str
    description: Optional[str] = None
    icon_url: Optional[str] = None
    rarity: str = "normal"


class UserBadgeOut(BaseModel):
    badge: BadgeOut
    earned_at: Optional[datetime] = None
