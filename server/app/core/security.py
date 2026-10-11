"""认证与密码安全。

技术架构文档 §3.3 —— JWT access 15min / refresh 30d，bcrypt 哈希。
"""
from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import bcrypt
from jose import JWTError, jwt

from app.config import settings


# ── 密码 ──


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, AttributeError):
        return False


def validate_password_strength(password: str) -> bool:
    """至少 8 位且同时含字母与数字。"""
    if len(password) < 8:
        return False
    return bool(re.search(r"[A-Za-z]", password)) and bool(re.search(r"\d", password))


# ── JWT ──


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def create_access_token(
    subject: str,
    role: str = "student",
    extra: Optional[Dict[str, Any]] = None,
) -> str:
    expire = _now() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload: Dict[str, Any] = {
        "sub": str(subject),
        "role": role,
        "type": "access",
        "exp": expire,
        "iat": _now(),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(subject: str, role: str = "student") -> str:
    expire = _now() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": str(subject),
        "role": role,
        "type": "refresh",
        "exp": expire,
        "iat": _now(),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str, expect_type: Optional[str] = None) -> Dict[str, Any]:
    """解码并校验类型；失败抛 AppError(1002)。"""
    from app.core.exceptions import unauthorized

    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
    except JWTError:
        raise unauthorized("登录已过期，请重新登录")

    if expect_type and payload.get("type") != expect_type:
        raise unauthorized("凭证类型错误")
    return payload


# ── Token 黑名单（注销 / 强制下线）──


async def blacklist_token(token: str) -> None:
    from app.core.redis import cache

    # 以 token 摘要为 key，避免明文存储
    digest = hashlib.sha256(token.encode()).hexdigest()
    ttl = settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400
    await cache.set(f"bl:{digest}", "1", ex=ttl)


async def is_token_blacklisted(token: str) -> bool:
    from app.core.redis import cache

    digest = hashlib.sha256(token.encode()).hexdigest()
    return await cache.get(f"bl:{digest}") is not None


# ── 邮箱验证码 ──


def generate_email_code() -> str:
    return f"{secrets.randbelow(900000) + 100000:06d}"


# ── NFC 卡片签名（防伪造/防盗用，产品策划 §9 风险表）──


def sign_card_id(card_id: str) -> str:
    return hmac.new(
        settings.SECRET_KEY.encode(), card_id.encode(), hashlib.sha256
    ).hexdigest()[:16]


def verify_card_signature(card_id: str, signature: str) -> bool:
    return hmac.compare_digest(sign_card_id(card_id), signature or "")


# ── 脱敏（墨麟书院输出层要求：移除一切可关联到个人的信息）──


def mask_student_id(student_id: Optional[str]) -> Optional[str]:
    if not student_id or len(student_id) < 4:
        return None
    return f"{student_id[:2]}{'*' * (len(student_id) - 4)}{student_id[-2:]}"


def mask_email(email: Optional[str]) -> Optional[str]:
    if not email or "@" not in email:
        return None
    name, domain = email.split("@", 1)
    keep = name[:1] if len(name) <= 3 else name[:2]
    return f"{keep}{'*' * max(1, len(name) - len(keep))}@{domain}"
