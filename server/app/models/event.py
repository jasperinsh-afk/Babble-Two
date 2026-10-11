"""活动日历：events / event_registrations / cas_records。

PRD §3.3（E-001 ~ E-203）+ 技术架构文档 §4.2。
"""
from __future__ import annotations

from sqlalchemy import Boolean, DateTime, Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.common import (
    Base,
    CasType,
    EventStatus,
    OrganizerType,
    ReviewStatus,
    SoftDeleteMixin,
    TimestampMixin,
)


class Event(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    cover_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    organizer_type: Mapped[OrganizerType] = mapped_column(
        Enum(OrganizerType), default=OrganizerType.CLUB, nullable=False
    )  # E-005 颜色区分类别
    organizer_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    start_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    end_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)
    signup_deadline: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    max_participants: Mapped[int | None] = mapped_column(Integer, nullable=True)

    status: Mapped[EventStatus] = mapped_column(
        Enum(EventStatus), default=EventStatus.ACTIVE, nullable=False
    )
    review_status: Mapped[ReviewStatus] = mapped_column(
        Enum(ReviewStatus), default=ReviewStatus.PENDING, nullable=False
    )
    participant_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cas_type: Mapped[CasType | None] = mapped_column(Enum(CasType), nullable=True)  # E-202
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)


class EventRegistration(Base):
    __tablename__ = "event_registrations"

    event_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    is_waitlist: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # E-105
    checked_in: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    registered_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)


class CasRecord(Base):
    """IB CAS 履历（PRD E-201 ~ E-203，Phase 3 导出 PDF）。"""

    __tablename__ = "cas_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    event_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    cas_type: Mapped[CasType] = mapped_column(Enum(CasType), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="participant", nullable=False)
    happened_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)
