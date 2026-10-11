"""模型基类、Mixin 与全局枚举。

命名约定：技术架构文档 §4.2 —— snake_case 字段，TIMESTAMPTZ 时间。
"""
from __future__ import annotations

import enum
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class SoftDeleteMixin:
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


# ── 用户 ──


class UserRole(str, enum.Enum):
    STUDENT = "student"
    CLUB_ADMIN = "club_admin"
    OPERATOR = "operator"
    ADMIN = "admin"


ROLE_LEVEL = {
    UserRole.STUDENT: 1,
    UserRole.CLUB_ADMIN: 2,
    UserRole.OPERATOR: 3,
    UserRole.ADMIN: 4,
}


# ── 投票（PRD §3.1）──


class PollType(str, enum.Enum):
    SINGLE = "single"  # 单选 2-6
    MULTI = "multi"  # 多选 2-8
    PK = "pk"  # 二选一
    RANKING = "ranking"  # 排序 3-6
    GROUP_BUY = "groupbuy"  # 活动接龙（PRD V-101）


POLL_OPTION_RANGE = {
    PollType.SINGLE: (2, 6),
    PollType.MULTI: (2, 8),
    PollType.PK: (2, 2),
    PollType.RANKING: (3, 6),
    PollType.GROUP_BUY: (1, 8),
}


class PollSource(str, enum.Enum):
    CRAWLER = "crawler"
    MANUAL = "manual"


class PollStatus(str, enum.Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    ACTIVE = "active"
    CLOSED = "closed"
    ARCHIVED = "archived"
    WITHDRAWN = "withdrawn"


class PollCategory(str, enum.Enum):
    """墨麟书院五分类标签（技术架构文档 §11.3）。"""

    CURRENT_AFFAIRS = "current_affairs"  # 时事热点
    CAMPUS = "campus"  # 校园生活
    CULTURE = "culture"  # 青少年文化
    VALUES = "values"  # 价值观探讨
    LIFESTYLE = "lifestyle"  # 生活方式


# 投票列表筛选标签（PRD V-202）
class PollTag(str, enum.Enum):
    NEWS = "news"  # 时事
    CAMPUS = "campus"  # 校园
    MEME = "meme"  # 热梗
    GROUP = "group"  # 接龙


# ── 内容审核（PRD §4）──


class ReviewStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_MANUAL = "needs_manual"  # LLM 判为边界，转人工


# ── 社团（PRD §3.2）──


class ClubCategory(str, enum.Enum):
    ACADEMIC = "academic"
    SPORTS = "sports"
    ART = "art"
    CHARITY = "charity"
    INTEREST = "interest"
    OTHER = "other"


# ── 活动（PRD §3.3）──


class OrganizerType(str, enum.Enum):
    CLUB = "club"
    CLASS = "class"
    SCHOOL = "school"


class EventStatus(str, enum.Enum):
    ACTIVE = "active"
    FULL = "full"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class CasType(str, enum.Enum):
    CREATIVITY = "C"
    ACTIVITY = "A"
    SERVICE = "S"


# ── 住宿生活（PRD §3.4）──


class DormChannelScope(str, enum.Enum):
    ROOM = "room"  # 宿舍内部 L-001
    FLOOR = "floor"  # 楼层 L-002
    ALL = "all"  # 全校住宿 L-003


class LostFoundKind(str, enum.Enum):
    LOST = "lost"
    FOUND = "found"


# ── OMEGA / NFC（OMEGA 文档 §8.2）──


class NfcTargetType(str, enum.Enum):
    VOTE = "vote"
    CLUB = "club"
    EVENT = "event"
    DOWNLOAD = "download"


class NfcLocationType(str, enum.Enum):
    """OMEGA §4.2 区域编码表。"""

    CT = "canteen"  # 食堂
    LB = "library"  # 图书馆
    DM = "dormitory"  # 宿舍楼
    BB = "bulletin"  # 公告栏
    CR = "classroom"  # 教室区
    CL = "clubroom"  # 社团活动室
    SP = "sports"  # 体育场馆
    GW = "gateway"  # 校门/入口


class DeviceType(str, enum.Enum):
    IOS = "ios"
    ANDROID = "android"
    UNKNOWN = "unknown"


# ── 爬虫（技术架构文档 §4.2 crawler_items）──


class CrawlerSource(str, enum.Enum):
    WEIBO = "weibo"
    ZHIHU = "zhihu"
    BILIBILI = "bilibili"
    BAIDU = "baidu"
    CCTV = "cctv"


class CrawlerItemStatus(str, enum.Enum):
    PENDING = "pending"
    FILTERED = "filtered"
    APPROVED = "approved"
    REJECTED = "rejected"
    USED = "used"


# ── 推送（PRD §5）──


class PushType(str, enum.Enum):
    DAILY_POLL = "daily_poll"
    POLL_RESULT = "poll_result"
    EVENT_REMIND = "event_remind"
    CLUB_UPDATE = "club_update"
    SYSTEM = "system"


__all__ = [
    "Base",
    "TimestampMixin",
    "SoftDeleteMixin",
    "utcnow",
    "UserRole",
    "ROLE_LEVEL",
    "PollType",
    "POLL_OPTION_RANGE",
    "PollSource",
    "PollStatus",
    "PollCategory",
    "PollTag",
    "ReviewStatus",
    "ClubCategory",
    "OrganizerType",
    "EventStatus",
    "CasType",
    "DormChannelScope",
    "LostFoundKind",
    "NfcTargetType",
    "NfcLocationType",
    "DeviceType",
    "CrawlerSource",
    "CrawlerItemStatus",
    "PushType",
]
