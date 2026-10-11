"""OMEGA / NFC 业务（OMEGA 文档 §8 + PRD N-001 ~ N-203）。"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import ERR_NFC_CARD_INACTIVE, ERR_NFC_CARD_NOT_FOUND, AppError
from app.models.common import DeviceType, NfcTargetType
from app.models.nfc import NfcCampaign, NfcCard, NfcCheckin, NfcTap
from app.models.user import User


def _now() -> datetime:
    return datetime.now(timezone.utc)


def detect_device(user_agent: str) -> DeviceType:
    ua = (user_agent or "").lower()
    if "iphone" in ua or "ipad" in ua:
        return DeviceType.IOS
    if "android" in ua:
        return DeviceType.ANDROID
    return DeviceType.UNKNOWN


def get_store_url(device: DeviceType) -> str:
    return (
        settings.IOS_APP_STORE_URL
        if device == DeviceType.IOS
        else settings.ANDROID_STORE_URL
    )


async def resolve_card(db: AsyncSession, card_id: str) -> Dict:
    """N-002 / N-005：后端决定跳转目标（卡片不存业务逻辑）。"""
    card = (
        await db.execute(select(NfcCard).where(NfcCard.card_id == card_id))
    ).scalars().first()
    if card is None:
        raise AppError(ERR_NFC_CARD_NOT_FOUND, "NFC 卡片不存在", 404)
    if not card.is_active:
        raise AppError(ERR_NFC_CARD_INACTIVE, "NFC 卡片已停用", 403)

    return {
        "card_id": card.card_id,
        "target_type": card.target_type,
        "target_id": card.target_id,
        "target_url": card.target_path(),
        "location_desc": card.location_desc,
    }


async def record_tap(
    db: AsyncSession,
    card_id: str,
    device_type: DeviceType = DeviceType.UNKNOWN,
    app_installed: bool = False,
    action_result: str = "",
    user: Optional[User] = None,
) -> Dict:
    """N-103 碰触埋点 + N-201 打卡 + N-202 勋章解锁。"""
    card = (
        await db.execute(select(NfcCard).where(NfcCard.card_id == card_id))
    ).scalars().first()
    if card is None:
        raise AppError(ERR_NFC_CARD_NOT_FOUND, "NFC 卡片不存在", 404)

    db.add(
        NfcTap(
            card_id=card_id,
            user_id=user.id if user else None,
            device_type=device_type,
            app_installed=app_installed,
            action_result=action_result,
            tapped_at=_now(),
        )
    )

    newly_unlocked: List[str] = []
    if user:
        existing = await db.get(NfcCheckin, (user.id, card_id))
        if existing:
            existing.tap_count = (existing.tap_count or 0) + 1
        else:
            db.add(
                NfcCheckin(
                    user_id=user.id,
                    card_id=card_id,
                    first_tap_at=_now(),
                    tap_count=1,
                )
            )
        await db.flush()

        from app.services.badge_service import evaluate_user

        newly_unlocked = await evaluate_user(db, user.id)

    unique = (
        await db.execute(
            select(func.count(NfcCheckin.card_id)).where(NfcCheckin.user_id == user.id)
        )
    ).scalar() or 0 if user else 0

    return {"card_id": card_id, "unique_cards": unique, "new_badges": newly_unlocked}


async def register_card(db: AsyncSession, payload) -> NfcCard:
    """N-101 卡片注册。"""
    existing = (
        await db.execute(select(NfcCard).where(NfcCard.card_id == payload.card_id))
    ).scalars().first()
    if existing:
        existing.target_type = payload.target_type
        existing.target_id = payload.target_id
        existing.location_desc = payload.location_desc
        existing.location_type = payload.location_type
        existing.card_uid = payload.card_uid or existing.card_uid
        existing.poster_batch = payload.poster_batch or existing.poster_batch
        existing.updated_at = _now()
        await db.flush()
        return existing

    card = NfcCard(
        card_id=payload.card_id,
        card_uid=payload.card_uid,
        location_desc=payload.location_desc,
        location_type=payload.location_type,
        target_type=payload.target_type,
        target_id=payload.target_id,
        poster_batch=payload.poster_batch,
        is_active=True,
        created_at=_now(),
        updated_at=_now(),
    )
    db.add(card)
    await db.flush()
    return card


async def list_cards(db: AsyncSession, offset: int = 0, limit: int = 100) -> List[dict]:
    rows = (
        await db.execute(select(NfcCard).order_by(NfcCard.created_at.desc()).offset(offset).limit(limit))
    ).scalars().all()
    out = []
    for c in rows:
        taps = (
            await db.execute(select(func.count(NfcTap.id)).where(NfcTap.card_id == c.card_id))
        ).scalar() or 0
        uniq = (
            await db.execute(
                select(func.count(func.distinct(NfcTap.user_id))).where(
                    NfcTap.card_id == c.card_id, NfcTap.user_id.is_not(None)
                )
            )
        ).scalar() or 0
        out.append(
            {
                "id": c.id,
                "card_id": c.card_id,
                "card_uid": c.card_uid,
                "location_desc": c.location_desc,
                "location_type": c.location_type,
                "target_type": c.target_type,
                "target_id": c.target_id,
                "is_active": c.is_active,
                "poster_batch": c.poster_batch,
                "deployed_at": c.deployed_at,
                "created_at": c.created_at,
                "tap_count": taps,
                "unique_user_count": uniq,
            }
        )
    return out


async def card_stats(db: AsyncSession, card_id: Optional[str] = None) -> dict:
    """N-103 碰触统计：总次数、日均、时段分布。"""
    conds = [] if not card_id else [NfcTap.card_id == card_id]
    total = (await db.execute(select(func.count(NfcTap.id)).where(*conds))).scalar() or 0
    rows = (
        await db.execute(select(NfcTap.card_id, func.count(NfcTap.id)).where(*conds).group_by(NfcTap.card_id))
    ).all()
    hourly = (
        await db.execute(
            select(func.strftime("%H", NfcTap.tapped_at).label("h"), func.count(NfcTap.id))
            .where(*conds)
            .group_by("h")
        )
    ).all() if settings.db_is_sqlite else []

    return {
        "total_taps": total,
        "by_card": [{"card_id": c, "count": n} for c, n in rows],
        "hourly": [{"hour": h, "count": n} for h, n in hourly],
    }


def build_redirect_html(
    card_id: str,
    location_desc: str,
    target_url: str,
    store_url: str,
    device: DeviceType,
) -> str:
    """OMEGA §6.4 / §8.3 智能中间页：未装 App 时引导下载。"""
    tips = "正在跳转到应用商店…" if device != DeviceType.UNKNOWN else "正在打开…"
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>七德通 GoQD</title>
<meta http-equiv="refresh" content="2;url={store_url}">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif;
background:linear-gradient(160deg,#6C4BF6,#A878FF);min-height:100vh;display:flex;
align-items:center;justify-content:center;color:#fff;padding:24px}}
.card{{background:rgba(255,255,255,.14);backdrop-filter:blur(12px);border-radius:20px;
padding:32px 28px;max-width:420px;width:100%;text-align:center;
box-shadow:0 12px 40px rgba(0,0,0,.18)}}
.logo{{font-size:30px;font-weight:700;letter-spacing:1px}}
.slogan{{font-size:14px;opacity:.85;margin-top:6px}}
.loc{{font-size:13px;opacity:.8;margin-top:18px}}
.tip{{margin:22px 0 8px;font-size:15px}}
.btn{{display:block;margin:14px 0;padding:13px;border-radius:12px;background:#fff;
color:#6C4BF6;font-weight:600;text-decoration:none;font-size:15px}}
.btn.ghost{{background:transparent;border:1px solid rgba(255,255,255,.55);color:#fff}}
.meta{{font-size:12px;opacity:.7;margin-top:14px}}
</style>
</head>
<body>
<div class="card">
  <div class="logo">七德通 GoQD</div>
  <div class="slogan">碰一碰，发现校园新鲜事</div>
  <div class="loc">点位：{location_desc or card_id}</div>
  <div class="tip">{tips}</div>
  <a class="btn" href="{store_url}">立即下载 App</a>
  <a class="btn ghost" href="{target_url}">在网页中继续查看</a>
  <div class="meta">卡片编号 {card_id}</div>
</div>
</body>
</html>"""
