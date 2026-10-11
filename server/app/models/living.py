"""住宿生活：宿舍频道 / 帖子 / 失物招领 / 二手交换。

PRD §3.4（L-001 ~ L-103）。
"""
from __future__ import annotations

from sqlalchemy import Boolean, DateTime, Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.common import (
    Base,
    DormChannelScope,
    LostFoundKind,
    ReviewStatus,
    SoftDeleteMixin,
    TimestampMixin,
)


class DormChannel(Base, TimestampMixin):
    """L-001 ~ L-003 三级频道：宿舍 / 楼层 / 全校住宿。"""

    __tablename__ = "dorm_channels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    scope: Mapped[DormChannelScope] = mapped_column(
        Enum(DormChannelScope), default=DormChannelScope.ALL, nullable=False
    )
    building: Mapped[str | None] = mapped_column(String(50), nullable=True)
    floor: Mapped[str | None] = mapped_column(String(10), nullable=True)
    room: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class DormPost(Base, SoftDeleteMixin):
    """L-004 ~ L-006 发帖（文字 + 图片 ≤3 张）、点赞回复举报。"""

    __tablename__ = "dorm_posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    channel_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    author_id: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    images: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON 数组 ≤3
    like_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reply_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    report_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    review_status: Mapped[ReviewStatus] = mapped_column(
        Enum(ReviewStatus), default=ReviewStatus.APPROVED, nullable=False
    )
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)


class DormReply(Base):
    __tablename__ = "dorm_replies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    post_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)


class LostFound(Base, TimestampMixin, SoftDeleteMixin):
    """L-101 失物招领。"""

    __tablename__ = "lost_found"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kind: Mapped[LostFoundKind] = mapped_column(
        Enum(LostFoundKind), default=LostFoundKind.LOST, nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    contact: Mapped[str | None] = mapped_column(String(100), nullable=True)
    images: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class SecondHand(Base, TimestampMixin, SoftDeleteMixin):
    """L-102 二手交换。"""

    __tablename__ = "second_hand"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 单位：分
    images: Mapped[str | None] = mapped_column(Text, nullable=True)
    contact: Mapped[str | None] = mapped_column(String(100), nullable=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    is_sold: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
