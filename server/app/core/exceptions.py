"""统一业务异常与错误码。

统一响应格式（技术架构文档 §2.3）：
    {"code": 0, "message": "success", "data": {...}, "timestamp": 1696000000}
"""
from __future__ import annotations

from typing import Any, Dict, Optional


# ── 错误码分段 ──
# 0      成功
# 1xxx   通用
# 2xxx   认证 / 用户
# 3xxx   投票
# 4xxx   社团
# 5xxx   活动
# 6xxx   住宿生活
# 7xxx   NFC / OMEGA
# 8xxx   爬虫 / 审核 / 导出
OK = 0

ERR_BAD_REQUEST = 1001
ERR_UNAUTHORIZED = 1002
ERR_FORBIDDEN = 1003
ERR_NOT_FOUND = 1004
ERR_CONFLICT = 1005
ERR_RATE_LIMITED = 1006
ERR_INTERNAL = 1099

ERR_INVALID_CREDENTIALS = 2001
ERR_USER_EXISTS = 2002
ERR_STUDENT_ID_INVALID = 2003
ERR_EMAIL_INVALID = 2004
ERR_EMAIL_CODE_INVALID = 2005
ERR_EMAIL_CODE_EXPIRED = 2006
ERR_USER_INACTIVE = 2007
ERR_WEAK_PASSWORD = 2008

ERR_POLL_CLOSED = 3001
ERR_POLL_NOT_ACTIVE = 3002
ERR_ALREADY_VOTED = 3003
ERR_CHANGE_NOT_ALLOWED = 3004
ERR_ALREADY_CHANGED = 3005
ERR_OPTION_INVALID = 3006
ERR_OPTION_COUNT_INVALID = 3007
ERR_POLL_TYPE_INVALID = 3008
ERR_GROUP_FULL = 3009
ERR_NOT_GROUP_OWNER = 3010
ERR_COMMENT_TOO_LONG = 3011
ERR_NOT_VOTED_YET = 3012

ERR_CLUB_NOT_VERIFIED = 4001
ERR_NOT_CLUB_ADMIN = 4002
ERR_CLUB_APPLY_EXISTS = 4003
ERR_POST_PENDING = 4004
ERR_PIN_LIMIT = 4005

ERR_EVENT_FULL = 5001
ERR_EVENT_CLOSED = 5002
ERR_SIGNUP_DEADLINE_PASSED = 5003
ERR_ALREADY_REGISTERED = 5004

ERR_DORM_CHANNEL_FORBIDDEN = 6001
ERR_REPORT_LIMIT = 6002

ERR_NFC_CARD_NOT_FOUND = 7001
ERR_NFC_CARD_INACTIVE = 7002

ERR_CRAWLER_DISABLED = 8001
ERR_LLM_DISABLED = 8002
ERR_LLM_PARSE_FAILED = 8003
ERR_SENSITIVE_WORD_HIT = 8004
ERR_MANUAL_REVIEW_REQUIRED = 8005
ERR_EXPORT_RANGE_INVALID = 8006

MESSAGES: Dict[int, str] = {
    OK: "success",
    ERR_BAD_REQUEST: "请求参数有误",
    ERR_UNAUTHORIZED: "未登录或登录已过期",
    ERR_FORBIDDEN: "没有权限执行该操作",
    ERR_NOT_FOUND: "资源不存在",
    ERR_CONFLICT: "资源冲突",
    ERR_RATE_LIMITED: "操作过于频繁，请稍后再试",
    ERR_INTERNAL: "服务器内部错误",

    ERR_INVALID_CREDENTIALS: "学号或密码错误",
    ERR_USER_EXISTS: "该学号或邮箱已注册",
    ERR_STUDENT_ID_INVALID: "学号格式不正确",
    ERR_EMAIL_INVALID: "请使用学校邮箱注册",
    ERR_EMAIL_CODE_INVALID: "验证码不正确",
    ERR_EMAIL_CODE_EXPIRED: "验证码已过期",
    ERR_USER_INACTIVE: "账号已被停用",
    ERR_WEAK_PASSWORD: "密码至少 8 位，且包含字母和数字",

    ERR_POLL_CLOSED: "投票已结束",
    ERR_POLL_NOT_ACTIVE: "投票尚未开始",
    ERR_ALREADY_VOTED: "你已经投过票了",
    ERR_CHANGE_NOT_ALLOWED: "该投票不允许修改",
    ERR_ALREADY_CHANGED: "你已修改过一次，无法再次修改",
    ERR_OPTION_INVALID: "选项不存在",
    ERR_OPTION_COUNT_INVALID: "选项数量不符合该投票类型要求",
    ERR_POLL_TYPE_INVALID: "不支持的投票类型",
    ERR_GROUP_FULL: "接龙人数已满",
    ERR_NOT_GROUP_OWNER: "只有发起人可以操作",
    ERR_COMMENT_TOO_LONG: "立场短评不能超过 200 字",
    ERR_NOT_VOTED_YET: "请先参与投票",

    ERR_CLUB_NOT_VERIFIED: "社团尚未通过认证",
    ERR_NOT_CLUB_ADMIN: "你不是该社团管理员",
    ERR_CLUB_APPLY_EXISTS: "已有待审核的入驻申请",
    ERR_POST_PENDING: "内容仍在审核中",
    ERR_PIN_LIMIT: "每个社团最多置顶 1 条",

    ERR_EVENT_FULL: "活动人数已满",
    ERR_EVENT_CLOSED: "活动已关闭",
    ERR_SIGNUP_DEADLINE_PASSED: "报名已截止",
    ERR_ALREADY_REGISTERED: "你已报名该活动",

    ERR_DORM_CHANNEL_FORBIDDEN: "你没有权限访问该频道",
    ERR_REPORT_LIMIT: "举报过于频繁",

    ERR_NFC_CARD_NOT_FOUND: "NFC 卡片不存在",
    ERR_NFC_CARD_INACTIVE: "NFC 卡片已停用",

    ERR_CRAWLER_DISABLED: "爬虫功能未启用",
    ERR_LLM_DISABLED: "LLM 功能未启用",
    ERR_LLM_PARSE_FAILED: "模型输出解析失败",
    ERR_SENSITIVE_WORD_HIT: "内容命中敏感词",
    ERR_MANUAL_REVIEW_REQUIRED: "内容需人工复核",
    ERR_EXPORT_RANGE_INVALID: "导出时间范围无效",
}


class AppError(Exception):
    """业务异常：统一由全局异常处理器转为 {code, message}。"""

    def __init__(
        self,
        code: int = ERR_BAD_REQUEST,
        message: Optional[str] = None,
        http_status: int = 400,
        data: Any = None,
    ):
        self.code = code
        self.message = message or MESSAGES.get(code, "请求失败")
        self.http_status = http_status
        self.data = data
        super().__init__(self.message)


def bad_request(message: str = None, code: int = ERR_BAD_REQUEST) -> AppError:
    return AppError(code, message, 400)


def not_found(message: str = None) -> AppError:
    return AppError(ERR_NOT_FOUND, message, 404)


def forbidden(message: str = None) -> AppError:
    return AppError(ERR_FORBIDDEN, message, 403)


def unauthorized(message: str = None) -> AppError:
    return AppError(ERR_UNAUTHORIZED, message, 401)


def conflict(message: str = None, code: int = ERR_CONFLICT) -> AppError:
    return AppError(code, message, 409)
