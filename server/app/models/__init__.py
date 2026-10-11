"""ORM 模型汇总（导入本包即注册全部表）。"""
from app.models.common import Base  # noqa: F401
from app.models.user import Notification, PushDevice, User  # noqa: F401
from app.models.vote import Ballot, Comment, Poll, PollOption  # noqa: F401
from app.models.club import Club, ClubMember, Post, PostComment  # noqa: F401
from app.models.event import CasRecord, Event, EventRegistration  # noqa: F401
from app.models.living import (  # noqa: F401
    DormChannel,
    DormPost,
    DormReply,
    LostFound,
    SecondHand,
)
from app.models.nfc import NfcCampaign, NfcCard, NfcCheckin, NfcTap  # noqa: F401
from app.models.badge import BADGE_DEFS, Badge, UserBadge  # noqa: F401
from app.models.crawler import (  # noqa: F401
    DEFAULT_SENSITIVE_WORDS,
    CrawlerItem,
    SensitiveWord,
)

__all__ = [
    "Base",
    "User",
    "Notification",
    "PushDevice",
    "Poll",
    "PollOption",
    "Ballot",
    "Comment",
    "Club",
    "ClubMember",
    "Post",
    "PostComment",
    "Event",
    "EventRegistration",
    "CasRecord",
    "DormChannel",
    "DormPost",
    "DormReply",
    "LostFound",
    "SecondHand",
    "NfcCard",
    "NfcTap",
    "NfcCheckin",
    "NfcCampaign",
    "Badge",
    "UserBadge",
    "BADGE_DEFS",
    "CrawlerItem",
    "SensitiveWord",
    "DEFAULT_SENSITIVE_WORDS",
]
