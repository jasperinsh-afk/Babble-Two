"""OMEGA：NFC 卡片 / 碰触记录 / 打卡 / 打卡活动。

OMEGA 技术实现文档 §8.2 + §9.2。
"""
from __future__ import annotations

from sqlalchemy import Boolean, DateTime, Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.common import (
    Base,
    DeviceType,
    NfcLocationType,
    NfcTargetType,
    TimestampMixin,
)


class NfcCard(Base, TimestampMixin):
    """N-101 ~ N-104：卡片注册 / 状态 / 位置。

    card_id 编码规则（OMEGA §4.2）：{学校}-{区域}-{楼层/位置}-{序号}
    例：QD-CT-01-A01 → 七德-食堂-1楼-A区-01号
    """

    __tablename__ = "nfc_cards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    card_uid: Mapped[str | None] = mapped_column(String(50), nullable=True)  # NFC 物理 UID（可选）
    card_id: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    location_desc: Mapped[str | None] = mapped_column(String(200), nullable=True)
    location_type: Mapped[NfcLocationType | None] = mapped_column(
        Enum(NfcLocationType), nullable=True
    )
    target_type: Mapped[NfcTargetType] = mapped_column(
        Enum(NfcTargetType), default=NfcTargetType.DOWNLOAD, nullable=False
    )
    target_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    poster_batch: Mapped[str | None] = mapped_column(String(50), nullable=True)
    deployed_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def target_path(self) -> str:
        """返回 App 内路由路径。"""
        if self.target_type == NfcTargetType.DOWNLOAD:
            return "/download"
        return f"/{self.target_type.value}/{self.target_id}"


class NfcTap(Base):
    """N-103 碰触埋点（未登录时 user_id 可空）。"""

    __tablename__ = "nfc_taps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    card_id: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    device_type: Mapped[DeviceType] = mapped_column(
        Enum(DeviceType), default=DeviceType.UNKNOWN, nullable=False
    )
    app_installed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    action_result: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # app_open/clip_open/store_redirect/error
    tapped_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)


class NfcCheckin(Base):
    """N-201 打卡进度：同一卡片不重复计数。"""

    __tablename__ = "nfc_checkins"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    card_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    first_tap_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)
    tap_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


class NfcCampaign(Base, TimestampMixin):
    """N-202 / N-203 打卡活动与勋章解锁。"""

    __tablename__ = "nfc_campaigns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_count: Mapped[int] = mapped_column(Integer, nullable=False)
    badge_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    start_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
