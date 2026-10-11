"""投票核心：polls / poll_options / ballots / comments。

技术架构文档 §4.2 + PRD §3.1（V-001 ~ V-204）。
"""
from __future__ import annotations

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.common import (
    Base,
    PollCategory,
    PollSource,
    PollStatus,
    PollTag,
    PollType,
    ReviewStatus,
    SoftDeleteMixin,
    TimestampMixin,
)


class Poll(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "polls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)  # 引导语 ≤100字
    poll_type: Mapped[PollType] = mapped_column(Enum(PollType), default=PollType.SINGLE, nullable=False)
    source_type: Mapped[PollSource] = mapped_column(
        Enum(PollSource), default=PollSource.MANUAL, nullable=False
    )
    status: Mapped[PollStatus] = mapped_column(
        Enum(PollStatus), default=PollStatus.DRAFT, nullable=False, index=True
    )
    category: Mapped[PollCategory | None] = mapped_column(
        Enum(PollCategory), nullable=True
    )  # 墨麟书院分类标签 ML-O-005
    tag: Mapped[PollTag | None] = mapped_column(Enum(PollTag), nullable=True)  # V-202 筛选标签
    topic_tags: Mapped[str | None] = mapped_column(String(300), nullable=True)  # #校园生活 #热梗

    start_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    allow_change: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)  # V-003
    anonymous: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # 多选上限（V-001：多选可设上限）
    max_choices: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # 接龙：人数上限 / 发起人（V-101 ~ V-104）
    max_participants: Mapped[int | None] = mapped_column(Integer, nullable=True)

    cover_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    review_status: Mapped[ReviewStatus] = mapped_column(
        Enum(ReviewStatus), default=ReviewStatus.PENDING, nullable=False
    )
    review_note: Mapped[str | None] = mapped_column(String(200), nullable=True)

    created_by: Mapped[int | None] = mapped_column(Integer, index=True, nullable=False)
    crawler_item_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    options: Mapped[list["PollOption"]] = relationship(
        back_populates="poll", cascade="all, delete-orphan", order_by="PollOption.sort_order"
    )


class PollOption(Base):
    __tablename__ = "poll_options"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    poll_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("polls.id", ondelete="CASCADE"), index=True, nullable=False
    )
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    poll: Mapped["Poll"] = relationship(back_populates="options")


class Ballot(Base, TimestampMixin):
    """投票记录：UNIQUE(poll_id, user_id) 保证幂等（技术架构文档 §4.2）。"""

    __tablename__ = "ballots"
    __table_args__ = (UniqueConstraint("poll_id", "user_id", name="uq_ballot_poll_user"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    poll_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    # 单选/PK 存单个 option_id；多选/排序存 JSON 数组文本
    option_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    option_ids: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array
    is_changed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # V-003


class Comment(Base):
    """立场短评（PRD V-005，≤200 字，仅投票后可写）。"""

    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    poll_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(String(200), nullable=False)
    like_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_hidden: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # 审核不通过
    review_status: Mapped[ReviewStatus] = mapped_column(
        Enum(ReviewStatus), default=ReviewStatus.APPROVED, nullable=False
    )
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)
