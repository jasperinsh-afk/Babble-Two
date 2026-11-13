"""网页端 ↔ 小程序账号绑定：绑定码校验与身份解析。

网页端身份是服务端签发的 `web:<uuid>`，小程序身份是微信 `OPENID`，两者原本
互不相干。用户主动在小程序里生成一次性绑定码、在网页端输入后，服务端把两者
关联；此后所有网页请求注入 `linked:<openid>`，云函数据此把数据写到同一个
微信账号下，实现投票 / 积分 / 日程 / 消息跨端共享。

安全边界：`__openid` 由服务端覆盖注入（见 cloud_repo / local_repo），客户端
无法自行指定；`linked:` 前缀只能由本模块签发。绑定码 6 位、10 分钟有效、一次性。
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Tuple

from app import cloudbase_client
from app.repository import get_repository
from app.repository.base import BalaError

BIND_CODES = "bind_codes"
IDENTITY_LINKS = "identity_links"
LINKED_PREFIX = "linked:"
CODE_TTL_MS = 10 * 60 * 1000
RESOLVE_TTL = 300.0

# identity -> (过期时间, 解析后的身份)。云库查询是 HTTP 调用，必须缓存。
_cache: Dict[str, Tuple[float, str]] = {}


def invalidate_cache(identity: str = "") -> None:
    if identity:
        _cache.pop(identity, None)
    else:
        _cache.clear()


def mask_openid(openid: str) -> str:
    if len(openid) <= 8:
        return "***"
    return f"{openid[:4]}…{openid[-4:]}"


async def ensure_collections() -> None:
    """云模式下确保绑定码与身份关联集合存在，避免小程序首次签发绑定码失败。"""
    if get_repository().mode != "cloud":
        return
    await cloudbase_client.ensure_collection(BIND_CODES)
    await cloudbase_client.ensure_collection(IDENTITY_LINKS)


async def _query(collection: str, where: Dict[str, Any], limit: int = 1) -> List[Dict[str, Any]]:
    repo = get_repository()
    if repo.mode == "cloud":
        return await cloudbase_client.query(collection, where=where, limit=limit)
    matched: List[Dict[str, Any]] = []
    for doc in await repo.store.docs(collection):
        if all(doc.get(key) == value for key, value in where.items()):
            matched.append(doc)
            if len(matched) >= limit:
                break
    return matched


async def _upsert(collection: str, doc_id: str, doc: Dict[str, Any]) -> None:
    repo = get_repository()
    if repo.mode == "cloud":
        modified = await cloudbase_client.update(collection, {"_id": doc_id}, doc)
        if not modified:
            await cloudbase_client.add(collection, {"_id": doc_id, **doc})
    else:
        await repo.store.put(collection, {"_id": doc_id, **doc})


async def _delete(collection: str, doc_id: str) -> None:
    repo = get_repository()
    if repo.mode == "cloud":
        await cloudbase_client.delete(collection, {"_id": doc_id})
    else:
        await repo.store.delete(collection, doc_id)


async def _find_link(identity: str) -> Optional[Dict[str, Any]]:
    try:
        rows = await _query(IDENTITY_LINKS, {"_id": identity}, limit=1)
    except Exception:
        # 集合尚未创建 / 云库暂时不可用：降级为「未绑定」，绝不阻断正常业务
        return None
    return rows[0] if rows else None


async def resolve(identity: str) -> str:
    """把 web:<uuid> 解析成云函数可识别的身份；未绑定则原样返回。"""
    if not identity.startswith("web:"):
        return identity
    hit = _cache.get(identity)
    if hit and hit[0] > time.monotonic():
        return hit[1]
    link = await _find_link(identity)
    resolved = (
        f"{LINKED_PREFIX}{link['openid']}" if link and link.get("openid") else identity
    )
    _cache[identity] = (time.monotonic() + RESOLVE_TTL, resolved)
    return resolved


async def link_status(identity: str) -> Dict[str, Any]:
    link = await _find_link(identity)
    openid = str(link.get("openid") or "") if link else ""
    return {
        "bound": bool(openid),
        "openid": mask_openid(openid) if openid else "",
        "mode": get_repository().mode,
    }


async def bind(identity: str, code: str) -> Dict[str, Any]:
    digits = "".join(ch for ch in str(code or "") if ch.isdigit())
    if len(digits) != 6:
        raise BalaError("请输入小程序里显示的 6 位绑定码", "BAD_CODE")

    try:
        rows = await _query(BIND_CODES, {"_id": digits}, limit=1)
    except Exception as err:
        raise BalaError(
            "绑定码校验失败：请确认已按 cloud 模式配置 AppSecret 并部署 identity 云函数",
            "BIND_UNAVAILABLE",
            502,
        ) from err

    doc = rows[0] if rows else None
    if not doc or doc.get("used"):
        raise BalaError("绑定码无效或已被使用", "BAD_CODE")
    expires_at = doc.get("expiresAt")
    if isinstance(expires_at, (int, float)) and expires_at < int(time.time() * 1000):
        raise BalaError("绑定码已过期，请在小程序里重新生成", "CODE_EXPIRED")
    openid = str(doc.get("openid") or "")
    if not openid:
        raise BalaError("绑定码数据异常，请重新生成", "BAD_CODE")

    await _upsert(
        IDENTITY_LINKS,
        identity,
        {"openid": openid, "boundAt": int(time.time() * 1000)},
    )
    # 标记一次性；失败也不回滚绑定，过期时间仍会兜底
    try:
        repo = get_repository()
        if repo.mode == "cloud":
            await cloudbase_client.update(BIND_CODES, {"_id": digits}, {"used": True})
        else:
            await repo.store.put(BIND_CODES, {"_id": digits, **doc, "used": True})
    except Exception:
        pass

    invalidate_cache(identity)
    return {"bound": True, "openid": mask_openid(openid)}


async def unbind(identity: str) -> Dict[str, Any]:
    try:
        await _delete(IDENTITY_LINKS, identity)
    except Exception as err:
        raise BalaError("解绑失败，请稍后重试", "UNBIND_FAILED", 502) from err
    invalidate_cache(identity)
    return {"bound": False}


__all__ = [
    "BIND_CODES",
    "IDENTITY_LINKS",
    "LINKED_PREFIX",
    "bind",
    "unbind",
    "link_status",
    "resolve",
    "invalidate_cache",
    "mask_openid",
    "ensure_collections",
]
