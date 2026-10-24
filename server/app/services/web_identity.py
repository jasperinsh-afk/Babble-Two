"""网页版匿名身份：HMAC 签名，防止客户端随意伪造他人身份。

小程序靠微信上下文注入 openid，网页没有这个可信通道，因此由服务端签发
`web:<uuid>` + HMAC 令牌。身份仍然是匿名的（不注册、不落用户表），但
「知道别人的 identity 字符串」不再等于「能冒充别人」。
"""
from __future__ import annotations

import hashlib
import hmac
import re
import uuid
from typing import Dict

from app.config import settings

IDENTITY_RE = re.compile(r"^web:[0-9a-f]{32}$")


def sign(identity: str) -> str:
    return hmac.new(
        settings.SECRET_KEY.encode("utf-8"), identity.encode("utf-8"), hashlib.sha256
    ).hexdigest()


def issue_identity() -> Dict[str, str]:
    identity = f"web:{uuid.uuid4().hex}"
    return {"identity": identity, "token": sign(identity)}


def verify_identity(identity: str, token: str) -> bool:
    if not identity or not token or not IDENTITY_RE.match(identity):
        return False
    return hmac.compare_digest(sign(identity), token)


__all__ = ["issue_identity", "verify_identity", "sign", "IDENTITY_RE"]
