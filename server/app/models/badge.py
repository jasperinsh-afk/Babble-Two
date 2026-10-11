"""勋章系统。

PRD §6 勋章定义 + U-006 勋章墙 + N-202 NFC 打卡解锁。
"""
from __future__ import annotations

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.common import Base


class Badge(Base):
    __tablename__ = "badges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(String(200), nullable=True)
    icon_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    rarity: Mapped[str] = mapped_column(String(20), default="normal", nullable=False)
    # normal / rare / legendary
    # 解锁条件以 JSON 描述，由 badge_service 规则引擎解析
    rule: Mapped[str | None] = mapped_column(Text, nullable=True)


class UserBadge(Base):
    __tablename__ = "user_badges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    badge_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    earned_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)


# ── PRD §6 勋章定义 ──

BADGE_DEFS = [
    {
        "code": "first_step",
        "name": "初心",
        "description": "完成注册",
        "rarity": "normal",
        "rule": {"type": "register"},
    },
    {
        "code": "first_vote",
        "name": "首投",
        "description": "参与第一次投票",
        "rarity": "normal",
        "rule": {"type": "vote_count", "count": 1},
    },
    {
        "code": "ten_votes",
        "name": "十连投",
        "description": "连续参与 10 次投票",
        "rarity": "rare",
        "rule": {"type": "vote_count", "count": 10},
    },
    {
        "code": "opinion_leader",
        "name": "意见领袖",
        "description": "单条立场获 50+ 赞",
        "rarity": "rare",
        "rule": {"type": "comment_likes", "count": 50},
    },
    {
        "code": "event_master",
        "name": "活动达人",
        "description": "参加 10 个活动",
        "rarity": "rare",
        "rule": {"type": "event_count", "count": 10},
    },
    {
        "code": "club_pioneer",
        "name": "社团先锋",
        "description": "加入 3 个社团",
        "rarity": "normal",
        "rule": {"type": "club_count", "count": 3},
    },
    {
        "code": "nfc_explorer",
        "name": "NFC 探索者",
        "description": "碰触 5 个不同 NFC 卡片",
        "rarity": "rare",
        "rule": {"type": "nfc_unique", "count": 5},
    },
    {
        "code": "founder",
        "name": "元老",
        "description": "前 100 名注册用户",
        "rarity": "legendary",
        "rule": {"type": "early_user", "count": 100},
    },
    {
        "code": "perfect_attendance",
        "name": "全勤",
        "description": "连续 30 天每日投票",
        "rarity": "legendary",
        "rule": {"type": "vote_streak", "count": 30},
    },
]
