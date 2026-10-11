"""社团广场：clubs / club_members / posts。

PRD §3.2（C-001 ~ C-204）+ 技术架构文档 §4.2。
"""
from __future__ import annotations

from sqlalchemy import Boolean, DateTime, Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.common import (
    Base,
    ClubCategory,
    ReviewStatus,
    SoftDeleteMixin,
    TimestampMixin,
)


class Club(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "clubs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)  # ≤200字
    logo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    cover_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[ClubCategory] = mapped_column(
        Enum(ClubCategory), default=ClubCategory.OTHER, nullable=False
    )
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # C-005 认证标识
    review_status: Mapped[ReviewStatus] = mapped_column(
        Enum(ReviewStatus), default=ReviewStatus.PENDING, nullable=False
    )
    review_note: Mapped[str | None] = mapped_column(String(200), nullable=True)
    owner_id: Mapped[int | None] = mapped_column(Integer, nullable=False)
    member_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    follower_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    heat_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # C-202 热度榜

    members: Mapped[list["ClubMember"]] = relationship(
        back_populates="club", cascade="all, delete-orphan"
    )
    posts: Mapped[list["Post"]] = relationship(
        back_populates="club", cascade="all, delete-orphan"
    )


class ClubMember(Base):
    __tablename__ = "club_members"
    # 联合主键（技术架构文档 §4.2）

    club_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    role: Mapped[str] = mapped_column(String(20), default="member", nullable=False)  # member/admin
    joined_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)

    club: Mapped["Club"] = relationship(back_populates="members")


class Post(Base):
    """社团图文内容（C-101 ~ C-106）。"""

    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    club_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    author_id: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)  # ≤2000字
    images: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON 数组，≤9张
    status: Mapped[ReviewStatus] = mapped_column(
        Enum(ReviewStatus), default=ReviewStatus.PENDING, nullable=False
    )
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # C-106
    like_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    comment_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)

    club: Mapped["Club"] = relationship(back_populates="posts")


class PostComment(Base):
    __tablename__ = "post_comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    post_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(String(500), nullable=False)
    review_status: Mapped[ReviewStatus] = mapped_column(
        Enum(ReviewStatus), default=ReviewStatus.APPROVED, nullable=False
    )
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)
