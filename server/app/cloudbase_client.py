"""微信云开发 HTTP API 客户端（运营侧 → 云数据库桥接）。

小程序端的业务数据全部存放在微信云开发数据库中，Python 侧没有官方 SDK，
因此运营侧服务（墨麟书院爬虫写入、导出层读取、运营后台看板）统一经
微信云开发 HTTP API 访问。

文档要点：
  1. access_token：GET  https://api.weixin.qq.com/cgi-bin/token
  2. 数据库操作：POST  https://api.weixin.qq.com/tcb/database{query,add,update,delete,count}
     请求体 {"env": "...", "query": "db.collection('x').where({...}).get()"}
     query 支持 JS 语法子集，返回 data 为 JSON 字符串数组。
  3. 调用云函数：POST https://api.weixin.qq.com/tcb/invokecloudfunction

红线：AppSecret 只存在于服务端环境变量，绝不下发到小程序端。
"""
from __future__ import annotations

import json
import logging
import re
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

WX_API = "https://api.weixin.qq.com"

_TOKEN_CACHE: Dict[str, Any] = {"token": "", "expires_at": 0.0}


class CloudbaseError(RuntimeError):
    """云开发 HTTP API 调用失败。"""


# ── access_token ──


async def get_access_token(force: bool = False) -> str:
    """获取小程序全局 access_token，进程内缓存，提前 5 分钟过期。"""
    now = time.time()
    if not force and _TOKEN_CACHE["token"] and _TOKEN_CACHE["expires_at"] > now + 300:
        return _TOKEN_CACHE["token"]

    if not settings.WECHAT_APPID or not settings.WECHAT_SECRET:
        raise CloudbaseError("未配置 WECHAT_APPID / WECHAT_SECRET，无法访问云开发数据库")

    url = f"{WX_API}/cgi-bin/token"
    params = {
        "grant_type": "client_credential",
        "appid": settings.WECHAT_APPID,
        "secret": settings.WECHAT_SECRET,
    }
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, params=params)
    data = resp.json()
    if "access_token" not in data:
        raise CloudbaseError(f"获取 access_token 失败: {data}")

    _TOKEN_CACHE["token"] = data["access_token"]
    _TOKEN_CACHE["expires_at"] = now + int(data.get("expires_in", 7200))
    return _TOKEN_CACHE["token"]


async def _post(path: str, body: Dict[str, Any]) -> Dict[str, Any]:
    """统一 POST 云开发接口，自动重试一次（token 失效场景）。"""
    token = await get_access_token()
    url = f"{WX_API}/tcb/{path}"

    for attempt in (0, 1):
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(url, params={"access_token": token}, json=body)
        data = resp.json()
        errcode = data.get("errcode", 0)
        # 40001 / 42001 / 40014：token 失效，强制刷新后重试
        if errcode in (40001, 42001, 40014) and attempt == 0:
            token = await get_access_token(force=True)
            continue
        if errcode:
            raise CloudbaseError(f"{path} 失败[{errcode}]: {data.get('errmsg')}")
        return data

    raise CloudbaseError(f"{path} 重试后仍失败")


def _env() -> str:
    if not settings.WECHAT_CLOUD_ENV:
        raise CloudbaseError("未配置 WECHAT_CLOUD_ENV")
    return settings.WECHAT_CLOUD_ENV


ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}")


def _as_utc_iso(value: Any) -> Optional[str]:
    """把 datetime / ISO 字符串规范化为云函数 new Date().toISOString() 的格式。"""
    if isinstance(value, datetime):
        dt = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    if isinstance(value, str) and ISO_DATE_RE.match(value.strip()):
        try:
            parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError:
            return None
        return _as_utc_iso(parsed)
    return None


def _js(value: Any) -> str:
    """把 Python 值序列化成云开发 query 能识别的 JS 字面量。

    日期必须写成 new Date(...)：小程序云函数用 endAt/startAt 与 new Date() 做比较，
    若存成普通字符串，后台新建的投票/活动不会出现在小程序与网页首页。
    """
    iso_value = _as_utc_iso(value)
    if iso_value:
        return f'new Date("{iso_value}")'
    if isinstance(value, dict):
        return "{" + ",".join(
            f"{json.dumps(str(key), ensure_ascii=False)}:{_js(item)}"
            for key, item in value.items()
        ) + "}"
    if isinstance(value, (list, tuple)):
        return "[" + ",".join(_js(item) for item in value) + "]"
    return json.dumps(value, ensure_ascii=False)


def _normalize_dates(value: Any) -> Any:
    """云开发 HTTP API 可能把 Date 返回为 {"$date": 毫秒}，统一还原为 ISO 字符串。"""
    if isinstance(value, dict):
        if set(value) == {"$date"}:
            raw = value["$date"]
            if isinstance(raw, (int, float)):
                return _as_utc_iso(datetime.fromtimestamp(raw / 1000, tz=timezone.utc))
            return _as_utc_iso(raw) or raw
        return {key: _normalize_dates(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalize_dates(item) for item in value]
    return value


def _parse_rows(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for raw in data.get("data", []):
        if isinstance(raw, str):
            rows.append(_normalize_dates(json.loads(raw)))
        elif isinstance(raw, dict):
            rows.append(_normalize_dates(raw))
    return rows


# ── 数据库 CRUD ──


async def query(
    collection: str,
    where: Optional[Dict[str, Any]] = None,
    order_by: Optional[str] = None,
    order: str = "desc",
    limit: int = 20,
    skip: int = 0,
) -> List[Dict[str, Any]]:
    """查询集合（强制 limit，禁止全表扫描）。"""
    limit = max(1, min(int(limit), 100))
    expr = f"db.collection('{collection}')"
    if where:
        expr += f".where({_js(where)})"
    if order_by:
        expr += f".orderBy('{order_by}', '{order}')"
    expr += f".skip({int(skip)}).limit({limit}).get()"

    data = await _post("databasequery", {"env": _env(), "query": expr})
    return _parse_rows(data)


async def count(collection: str, where: Optional[Dict[str, Any]] = None) -> int:
    expr = f"db.collection('{collection}')"
    if where:
        expr += f".where({_js(where)})"
    expr += ".count()"
    data = await _post("databasecount", {"env": _env(), "query": expr})
    return int(data.get("count", 0))


async def add(collection: str, doc: Dict[str, Any]) -> str:
    expr = f"db.collection('{collection}').add({{data: {_js(doc)}}})"
    data = await _post("databaseadd", {"env": _env(), "query": expr})
    ids = data.get("id_list") or data.get("_id") or []
    return ids[0] if isinstance(ids, list) and ids else str(ids)


async def update(collection: str, where: Dict[str, Any], patch: Dict[str, Any]) -> int:
    expr = (
        f"db.collection('{collection}').where({_js(where)})"
        f".update({{data: {_js(patch)}}})"
    )
    data = await _post("databaseupdate", {"env": _env(), "query": expr})
    return int(data.get("modified", 0))


async def delete(collection: str, where: Dict[str, Any]) -> int:
    expr = f"db.collection('{collection}').where({_js(where)}).remove()"
    data = await _post("databasedelete", {"env": _env(), "query": expr})
    return int(data.get("deleted", 0))


# ── 云函数调用 ──


async def invoke(
    name: str, action: str, payload: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """通用云函数调用，返回云函数的 {ok, data, message} 原始信封。

    网页版（bala-web）经此复用 vote / club / event / living / scan / me 云函数，
    从而原样保留云函数内的 _.inc 原子自增与业务校验。
    调用方负责在 payload 里注入 __openid（云函数 resolveOpenid 优先读它）。
    """
    token = await get_access_token()
    url = f"{WX_API}/tcb/invokecloudfunction"
    body = {"action": action, "payload": payload or {}}

    for attempt in (0, 1):
        params = {"access_token": token, "env": _env(), "name": name}
        async with httpx.AsyncClient(timeout=25) as client:
            resp = await client.post(url, params=params, json=body)
        data = resp.json()
        errcode = data.get("errcode", 0)
        if errcode in (40001, 42001, 40014) and attempt == 0:
            token = await get_access_token(force=True)
            continue
        if errcode:
            raise CloudbaseError(
                f"invokecloudfunction({name}) 失败[{errcode}]: {data.get('errmsg')}"
            )

        raw = data.get("resp_data")
        if isinstance(raw, str):
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                return {"ok": False, "data": None, "message": raw}
            return _normalize_dates(parsed) if isinstance(parsed, dict) else {"ok": True, "data": parsed}
        if isinstance(raw, dict):
            return _normalize_dates(raw)
        raise CloudbaseError(f"invokecloudfunction({name}) 返回为空: {data}")

    raise CloudbaseError(f"invokecloudfunction({name}) 重试后仍失败")


async def ingest(action: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """调用 adminIngest 云函数写入云数据库的唯一入口。

    云函数侧会校验 payload.token 与环境变量 INGEST_TOKEN 是否一致，
    因此运营侧的写操作不会绕过鉴权。
    """
    return await invoke(
        "adminIngest", action, {**(payload or {}), "token": settings.INGEST_TOKEN}
    )


async def upsert_draft(draft: Dict[str, Any]) -> Dict[str, Any]:
    """墨麟书院：爬虫草稿写入云数据库（运营审核前为 pending 状态）。"""
    return await ingest("upsertDraft", {"draft": draft})


async def publish_poll(poll: Dict[str, Any]) -> Dict[str, Any]:
    """墨麟书院：运营审核通过后发布投票到云数据库。"""
    return await ingest("publishPoll", {"poll": poll})
