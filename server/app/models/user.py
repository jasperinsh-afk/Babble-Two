"""用户 / 通知 / 推送设备。

技术架构文档 §4.2 users 表 + PRD U-001~U-009。
"""
from __future__ import annotations

from sqlalchemy import Boolean, DateTime, Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.common import Base, PushType, SoftDeleteMixin, TimestampMixin, UserRole


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    nickname: Mapped[str] = mapped_column(String(50), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    bio: Mapped[str | None] = mapped_column(String(200), nullable=True)
    grade: Mapped[str | None] = mapped_column(String(10), nullable=True)  # 10/11/12
    dormitory: Mapped[str | None] = mapped_column(String(20), nullable=True)  # 宿舍号
    dorm_floor: Mapped[str | None] = mapped_column(String(10), nullable=True)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole), default=UserRole.STUDENT, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # 邮箱已验证
    email_verified_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # 推送偏好（PRD §5：用户可在设置中关闭指定类型推送）
    push_daily_poll: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    push_poll_result: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    push_event_remind: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    push_club_update: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    @property
    def role_level(self) -> int:
        from app.models.common import ROLE_LEVEL

        return ROLE_LEVEL.get(self.role, 1)


class Notification(Base):
    """站内消息（技术架构文档 §7.1 双通道之一）。"""

    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    type: Mapped[PushType] = mapped_column(Enum(PushType), default=PushType.SYSTEM, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    ref_type: Mapped[str | None] = mapped_column(String(20), nullable=True)  # vote/club/event
    ref_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)


class PushDevice(Base):
    """极光推送 RegistrationID 绑定（PRD §5）。"""

    __tablename__ = "push_devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    platform: Mapped[str] = mapped_column(String(10), nullable=False)  # ios/android
    registration_id: Mapped[str] = mapped_column(String(200), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)
