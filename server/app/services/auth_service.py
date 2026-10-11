"""认证与用户服务（PRD U-001 ~ U-009）。"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import (
    ERR_EMAIL_CODE_INVALID,
    ERR_EMAIL_INVALID,
    ERR_EMAIL_CODE_EXPIRED,
    ERR_STUDENT_ID_INVALID,
    ERR_USER_EXISTS,
    ERR_USER_INACTIVE,
    ERR_WEAK_PASSWORD,
    AppError,
    conflict,
    not_found,
    unauthorized,
)
from app.core.redis import cache
from app.core.security import (
    create_access_token,
    create_refresh_token,
    generate_email_code,
    hash_password,
    verify_password,
)
from app.models.common import UserRole
from app.models.user import User


def _now() -> datetime:
    return datetime.now(timezone.utc)


def validate_student_id(student_id: str) -> bool:
    return bool(re.match(settings.STUDENT_ID_PATTERN, student_id or ""))


def validate_school_email(email: str) -> bool:
    domain = settings.SCHOOL_EMAIL_DOMAIN
    return email.lower().endswith(domain.lower())


# ── 邮箱验证码 ──

_EMAIL_CODE_TTL = 300  # 5 分钟


async def send_email_code(db: AsyncSession, email: str) -> str:
    """生产环境接 SMTP/阿里云邮件推送；开发期返回验证码便于联调。"""
    if not validate_school_email(email):
        raise AppError(ERR_EMAIL_INVALID, f"请使用学校邮箱（{settings.SCHOOL_EMAIL_DOMAIN}）")

    code = generate_email_code()
    await cache.set(f"emailcode:{email.lower()}", code, ex=_EMAIL_CODE_TTL)
    # TODO(生产): 接入邮件服务发送 code
    return code


async def verify_email_code(email: str, code: str) -> bool:
    stored = await cache.get(f"emailcode:{email.lower()}")
    if stored is None:
        raise AppError(ERR_EMAIL_CODE_EXPIRED, "验证码已过期，请重新获取")
    if stored != code:
        raise AppError(ERR_EMAIL_CODE_INVALID, "验证码不正确")
    await cache.delete(f"emailcode:{email.lower()}")
    return True


# ── 注册 / 登录 ──


async def register(db: AsyncSession, payload) -> Tuple[User, str, str]:
    if not validate_student_id(payload.student_id):
        raise AppError(ERR_STUDENT_ID_INVALID, "学号格式不正确")
    if not validate_school_email(payload.email):
        raise AppError(ERR_EMAIL_INVALID, f"请使用学校邮箱（{settings.SCHOOL_EMAIL_DOMAIN}）")

    await verify_email_code(payload.email, payload.email_code)

    exists = (
        await db.execute(
            select(User).where(
                (User.student_id == payload.student_id) | (User.email == payload.email.lower())
            )
        )
    ).scalars().first()
    if exists:
        raise conflict("该学号或邮箱已注册", ERR_USER_EXISTS)

    user = User(
        student_id=payload.student_id,
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        nickname=payload.nickname,
        grade=payload.grade,
        dormitory=payload.dormitory,
        role=UserRole.STUDENT,
        is_verified=True,
        email_verified_at=_now(),
        created_at=_now(),
        updated_at=_now(),
    )
    db.add(user)
    await db.flush()

    # U-006 勋章墙：注册即解锁「初心」
    from app.services.badge_service import evaluate_user

    await evaluate_user(db, user.id)

    return user, create_access_token(str(user.id), user.role.value), create_refresh_token(
        str(user.id), user.role.value
    )


async def login(db: AsyncSession, student_id: str, password: str) -> Tuple[User, str, str]:
    user = (
        await db.execute(select(User).where(User.student_id == student_id))
    ).scalars().first()

    if user is None or not verify_password(password, user.password_hash):
        raise unauthorized("学号或密码错误")
    if not user.is_active:
        raise AppError(ERR_USER_INACTIVE, "账号已被停用", 403)

    return (
        user,
        create_access_token(str(user.id), user.role.value),
        create_refresh_token(str(user.id), user.role.value),
    )


async def refresh_tokens(db: AsyncSession, refresh_token: str) -> Tuple[str, str]:
    from app.core.security import decode_token

    payload = decode_token(refresh_token, expect_type="refresh")
    user = await db.get(User, int(payload["sub"]))
    if user is None or not user.is_active:
        raise unauthorized()
    return (
        create_access_token(str(user.id), user.role.value),
        create_refresh_token(str(user.id), user.role.value),
    )


# ── U-009 注销账号（合规硬要求）──


async def delete_account(db: AsyncSession, user: User) -> None:
    """清除个人数据，保留匿名化投票统计。

    ballots / cas_records 等聚合数据保留 user_id 但用户主记录匿名化，
    保证 ML-O-001「投票数据不因注销而丢失」。
    """
    from sqlalchemy import delete

    from app.models.club import ClubMember
    from app.models.event import EventRegistration
    from app.models.user import Notification, PushDevice

    await db.execute(delete(PushDevice).where(PushDevice.user_id == user.id))
    await db.execute(delete(Notification).where(Notification.user_id == user.id))
    await db.execute(delete(ClubMember).where(ClubMember.user_id == user.id))
    await db.execute(delete(EventRegistration).where(EventRegistration.user_id == user.id))

    user.is_active = False
    user.email = f"deleted_{user.id}@invalid.local"
    user.student_id = f"deleted_{user.id}"
    user.nickname = "已注销用户"
    user.avatar_url = None
    user.bio = None
    user.dormitory = None
    user.password_hash = hash_password("deleted-account-no-login")
    user.updated_at = _now()
    await db.flush()
