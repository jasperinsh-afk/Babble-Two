"""站点内容管理：受后台口令保护的 local/cloud 统一文档读写。"""
from __future__ import annotations

import copy
import uuid
from datetime import datetime, timezone
from typing import Any

from app import cloudbase_client
from app.config import settings
from app.core.admin_gate import (
    ADMIN_PRINCIPAL,
    ROLE_CLUB_MODERATOR,
    ROLE_REVIEWER,
    AdminPrincipal,
)
from app.repository import LocalRepository, get_repository
from app.repository.base import BalaError
from app.services import web_service

COLLECTIONS = {
    "banners": {
        "label": "首页 Banner",
        "titleKey": "title",
        "fields": [
            {"name": "title", "label": "标题", "type": "text", "required": True},
            {"name": "imageUrl", "label": "图片地址", "type": "url", "required": True},
            {"name": "targetRoute", "label": "点击跳转路径", "type": "text", "placeholder": "/vote/p001"},
            {"name": "sort", "label": "排序值（越小越靠前）", "type": "number"},
            {"name": "isActive", "label": "在首页显示", "type": "boolean"},
        ],
    },
    "polls": {
        "label": "投票",
        "titleKey": "title",
        "fields": [
            {"name": "title", "label": "投票标题", "type": "text", "required": True},
            {"name": "description", "label": "投票说明", "type": "textarea"},
            {"name": "pollType", "label": "投票类型", "type": "select", "required": True, "options": [["single", "单选"], ["multi", "多选"], ["pk", "PK"], ["ranking", "排序"], ["groupbuy", "接龙"]]},
            {"name": "status", "label": "状态", "type": "select", "required": True, "options": [["draft", "草稿"], ["active", "上线"], ["closed", "结束"], ["archived", "归档"], ["withdrawn", "撤回"]]},
            {"name": "tag", "label": "分类", "type": "select", "options": [["campus", "校园"], ["life", "生活"], ["club", "社团"], ["other", "其他"]]},
            {"name": "category", "label": "栏目", "type": "text"},
            {"name": "coverUrl", "label": "封面地址", "type": "url"},
            {"name": "startAt", "label": "开始时间", "type": "datetime"},
            {"name": "endAt", "label": "结束时间", "type": "datetime"},
            {"name": "allowChange", "label": "允许改票一次", "type": "boolean"},
            {"name": "maxChoices", "label": "多选上限", "type": "number"},
            {"name": "maxParticipants", "label": "接龙人数上限", "type": "number"},
            {"name": "reviewStatus", "label": "审核状态", "type": "select", "options": [["pending", "待审核"], ["approved", "已通过"], ["rejected", "已驳回"]]},
            {"name": "resultStatus", "label": "结果公示状态", "type": "select", "options": [["draft", "未公示"], ["published", "已公示"], ["withdrawn", "已撤回"]]},
            {"name": "resultScope", "label": "结果范围", "type": "select", "options": [["campus", "全校"], ["club", "社团内"], ["draft", "草稿不可见"]]},
            {"name": "sampleNote", "label": "样本说明", "type": "string"},
            {"name": "resultDueAt", "label": "承诺回应截止", "type": "string"},
            {"name": "ownerType", "label": "负责人类型", "type": "select", "options": [["school", "学校"], ["club", "社团"], ["student", "学生"]]},
            {"name": "ownerName", "label": "负责人名称", "type": "string"},
            {"name": "ownerResponse", "label": "负责人回应", "type": "textarea"},
            {"name": "options", "label": "投票选项", "type": "list", "itemLabel": "选项", "fields": [
                {"name": "optionId", "label": "选项 ID（留空自动生成）", "type": "text"},
                {"name": "label", "label": "选项文字", "type": "text", "required": True},
                {"name": "sortOrder", "label": "排序值", "type": "number"},
            ]},
        ],
    },
    "events": {
        "label": "活动",
        "titleKey": "title",
        "fields": [
            {"name": "title", "label": "活动名称", "type": "text", "required": True},
            {"name": "description", "label": "活动介绍", "type": "textarea"},
            {"name": "coverUrl", "label": "封面地址", "type": "url"},
            {"name": "location", "label": "活动地点", "type": "text"},
            {"name": "organizerType", "label": "主办方类型", "type": "select", "options": [["school", "学校"], ["club", "社团"], ["student", "学生"]]},
            {"name": "organizerId", "label": "主办方 ID", "type": "text"},
            {"name": "startAt", "label": "开始时间", "type": "datetime", "required": True},
            {"name": "endAt", "label": "结束时间", "type": "datetime", "required": True},
            {"name": "signupDeadline", "label": "报名截止", "type": "datetime"},
            {"name": "maxParticipants", "label": "人数上限", "type": "number"},
            {"name": "status", "label": "状态", "type": "select", "options": [["draft", "草稿"], ["active", "报名中"], ["full", "已满员"], ["closed", "已结束"], ["cancelled", "已取消"]]},
            {"name": "casType", "label": "CAS 类型", "type": "select", "options": [["C", "Creativity"], ["A", "Activity"], ["S", "Service"]]},
            {"name": "changeSummary", "label": "变更摘要", "type": "string"},
            {"name": "cancelReason", "label": "取消原因", "type": "string"},
            {"name": "isDeleted", "label": "从用户端隐藏", "type": "boolean"},
        ],
    },
    "clubs": {
        "label": "社团",
        "titleKey": "name",
        "fields": [
            {"name": "name", "label": "社团名称", "type": "text", "required": True},
            {"name": "description", "label": "社团简介", "type": "textarea"},
            {"name": "logoUrl", "label": "Logo 地址", "type": "url"},
            {"name": "coverUrl", "label": "封面地址", "type": "url"},
            {"name": "category", "label": "分类", "type": "text"},
            {"name": "isVerified", "label": "官方认证", "type": "boolean"},
            {"name": "heatScore", "label": "热度值", "type": "number"},
            {"name": "isDeleted", "label": "从用户端隐藏", "type": "boolean"},
        ],
    },
    "club_posts": {
        "label": "社团动态",
        "titleKey": "title",
        "fields": [
            {"name": "clubId", "label": "所属社团 ID", "type": "text", "required": True},
            {"name": "title", "label": "动态标题", "type": "text", "required": True},
            {"name": "content", "label": "动态内容", "type": "textarea", "required": True},
            {"name": "images", "label": "图片地址（每行一个）", "type": "stringList"},
            {"name": "isPinned", "label": "置顶动态", "type": "boolean"},
            {"name": "likeCount", "label": "点赞数", "type": "number"},
            {"name": "publishedAt", "label": "发布时间", "type": "datetime"},
        ],
    },
}

SECTION_TYPES = [
    ["banner", "Banner 轮播"], ["todayPoll", "今日投票"], ["quickEntries", "快捷入口"],
    ["hotPolls", "热门投票"], ["events", "推荐活动"], ["clubs", "社团精选"],
]
DEFAULT_QUICK_ENTRIES = [
    {"key": "vote", "label": "投票", "icon": "✓", "to": "/vote"},
    {"key": "club", "label": "社团", "icon": "⌂", "to": "/club"},
    {"key": "calendar", "label": "日历", "icon": "▦", "to": "/calendar"},
    {"key": "living", "label": "住宿", "icon": "⌂", "to": "/living"},
    {"key": "scan", "label": "扫码", "icon": "◎", "to": "/scan"},
]
DEFAULT_LAYOUT = {
    "_id": "home",
    "sections": [
        {"id": "section-banner", "type": "banner", "title": "Banner 轮播", "enabled": True, "config": {"limit": 5}},
        {"id": "section-today", "type": "todayPoll", "title": "今日投票", "enabled": True, "config": {}},
        {"id": "section-quick", "type": "quickEntries", "title": "快捷入口", "enabled": True, "config": {"items": DEFAULT_QUICK_ENTRIES}},
        {"id": "section-hot", "type": "hotPolls", "title": "热门投票", "enabled": True, "config": {"limit": 5}},
        {"id": "section-events", "type": "events", "title": "推荐活动", "enabled": True, "config": {"limit": 3}},
        {"id": "section-clubs", "type": "clubs", "title": "社团精选", "enabled": True, "config": {"limit": 6}},
    ],
}
NEW_DEFAULTS = {
    "banners": {"isActive": True, "sort": 0},
    "polls": {"pollType": "single", "status": "draft", "tag": "campus", "reviewStatus": "approved", "allowChange": False, "options": [{"optionId": "", "label": "", "sortOrder": 0}, {"optionId": "", "label": "", "sortOrder": 1}], "resultStatus": "draft", "resultScope": "campus", "resultRevision": 0, "responseRevision": 0},
    "events": {"status": "draft", "organizerType": "school", "isDeleted": False, "participantCount": 0, "registeredOpenids": [], "waitlistOpenids": [], "changeRevision": 0},
    "clubs": {"isVerified": False, "isDeleted": False, "heatScore": 0, "memberCount": 0, "memberOpenids": []},
    "club_posts": {"images": [], "isPinned": False, "likeCount": 0},
}


def default_layout() -> dict[str, Any]:
    return copy.deepcopy(DEFAULT_LAYOUT)


def _principal(principal: AdminPrincipal | None) -> AdminPrincipal:
    return principal or ADMIN_PRINCIPAL


def _assert_collection_allowed(collection: str, principal: AdminPrincipal | None, action: str) -> AdminPrincipal:
    actor = _principal(principal)
    _schema(collection)
    if actor.is_admin:
        return actor
    if actor.role == ROLE_REVIEWER:
        if action == "create":
            raise BalaError("审核员只能查看、修改或删除内容", "FORBIDDEN", 403)
        return actor
    if actor.role == ROLE_CLUB_MODERATOR:
        if collection not in {"clubs", "club_posts", "events"} or not actor.club_id:
            raise BalaError("只能管理自己社团的内容", "FORBIDDEN", 403)
        if collection == "clubs" and action == "create":
            raise BalaError("不能创建新的社团账号内容", "FORBIDDEN", 403)
        return actor
    raise BalaError("无权管理内容", "FORBIDDEN", 403)


def _document_in_scope(collection: str, document: dict[str, Any], actor: AdminPrincipal) -> bool:
    if collection == "clubs":
        return document.get("_id") == actor.club_id
    if collection == "club_posts":
        return document.get("clubId") == actor.club_id
    if collection == "events":
        return document.get("organizerType") == "club" and document.get("organizerId") == actor.club_id
    return False


def _assert_document_scope(collection: str, document: dict[str, Any], actor: AdminPrincipal) -> None:
    if actor.role == ROLE_CLUB_MODERATOR and not _document_in_scope(collection, document, actor):
        raise BalaError("不能访问其他社团的内容", "FORBIDDEN", 403)


def accessible_collections(principal: AdminPrincipal) -> dict[str, Any]:
    return {
        key: schema_for(key, principal)
        for key in COLLECTIONS
        if principal.role != ROLE_CLUB_MODERATOR or key in {"clubs", "club_posts", "events"}
    }


def schema_for(collection: str, principal: AdminPrincipal | None = None) -> dict[str, Any]:
    actor = _principal(principal)
    schema = copy.deepcopy(_schema(collection))
    schema["canCreate"] = actor.role != ROLE_REVIEWER and not (
        actor.role == ROLE_CLUB_MODERATOR and collection == "clubs"
    )
    if actor.role == ROLE_CLUB_MODERATOR:
        ownership_fields = {"club_posts": {"clubId"}, "events": {"organizerType", "organizerId"}}
        hidden = ownership_fields.get(collection, set())
        schema["fields"] = [field for field in schema["fields"] if field["name"] not in hidden]
    return schema


def new_document(collection: str, principal: AdminPrincipal | None = None) -> dict[str, Any]:
    actor = _assert_collection_allowed(collection, principal, "create")
    doc = copy.deepcopy(NEW_DEFAULTS.get(collection, {}))
    if actor.role == ROLE_CLUB_MODERATOR:
        if collection == "club_posts":
            doc["clubId"] = actor.club_id
        elif collection == "events":
            doc.update({"organizerType": "club", "organizerId": actor.club_id})
    return doc


def _schema(collection: str) -> dict[str, Any]:
    if collection not in COLLECTIONS:
        raise BalaError("不支持的内容类型", "INVALID_COLLECTION", 404)
    return COLLECTIONS[collection]


def _text(value: Any) -> str:
    return str(value or "").strip()


def _clean_field(field: dict[str, Any], value: Any) -> Any:
    kind = field["type"]
    if kind == "boolean":
        return bool(value)
    if kind == "number":
        if value in (None, ""):
            return None
        try:
            number = float(value)
        except (TypeError, ValueError) as exc:
            raise BalaError(f"{field['label']}必须是数字", "INVALID_FIELD") from exc
        return int(number) if number.is_integer() else number
    if kind == "stringList":
        if not isinstance(value, list):
            raise BalaError(f"{field['label']}格式不正确", "INVALID_FIELD")
        rows = [_text(item) for item in value[:50] if _text(item)]
        if any(not item.startswith(("https://", "http://", "/assets/")) for item in rows):
            raise BalaError(f"{field['label']}需为 http(s) 地址或 /assets/ 本地路径", "INVALID_FIELD")
        return rows
    if kind == "list":
        if not isinstance(value, list):
            raise BalaError(f"{field['label']}格式不正确", "INVALID_FIELD")
        rows = []
        for item in value[:100]:
            if not isinstance(item, dict):
                raise BalaError(f"{field['label']}格式不正确", "INVALID_FIELD")
            rows.append({sub["name"]: _clean_field(sub, item.get(sub["name"])) for sub in field["fields"]})
        return rows
    value = _text(value)
    if field.get("required") and not value:
        raise BalaError(f"请填写{field['label']}", "REQUIRED_FIELD")
    if len(value) > 10000:
        raise BalaError(f"{field['label']}内容过长", "INVALID_FIELD")
    if kind == "select" and value and value not in {str(option[0]) for option in field.get("options", [])}:
        raise BalaError(f"{field['label']}选项不合法", "INVALID_FIELD")
    if kind == "url" and value and not value.startswith(("https://", "http://", "/assets/")):
        raise BalaError(f"{field['label']}需为 http(s) 地址或 /assets/ 本地路径", "INVALID_FIELD")
    return value or None


def clean_document(collection: str, payload: dict[str, Any], existing: dict[str, Any] | None = None) -> dict[str, Any]:
    schema = _schema(collection)
    doc = dict(existing or NEW_DEFAULTS.get(collection, {}))
    for field in schema["fields"]:
        doc[field["name"]] = _clean_field(field, payload.get(field["name"]))
    doc["updatedAt"] = datetime.now(timezone.utc).isoformat()
    if not existing:
        doc["createdAt"] = doc["updatedAt"]
    if collection == "polls":
        options = doc.get("options") or []
        if len(options) < 2:
            raise BalaError("投票至少需要两个选项", "INVALID_FIELD")
        used = set()
        for index, option in enumerate(options):
            option["optionId"] = option.get("optionId") or f"opt-{uuid.uuid4().hex[:10]}"
            option["sortOrder"] = option.get("sortOrder") if option.get("sortOrder") is not None else index
            option.setdefault("count", 0)
            if option["optionId"] in used:
                raise BalaError("选项 ID 不能重复", "INVALID_FIELD")
            used.add(option["optionId"])
        if existing:
            _track_poll_result(doc, existing)
    if collection == "events" and existing:
        _track_event_change(doc, existing)
    return doc


def _track_poll_result(doc: dict[str, Any], existing: dict[str, Any]) -> None:
    """结果公示 / 负责人回应的修订号由服务端托管，端上不可伪造。"""
    now_iso = datetime.now(timezone.utc).isoformat()
    if doc.get("resultStatus") != (existing.get("resultStatus") or "draft"):
        doc["resultRevision"] = (existing.get("resultRevision") or 0) + 1
        if doc.get("resultStatus") == "published":
            doc["resultPublishedAt"] = now_iso
    if not _text(existing.get("ownerResponse")) and _text(doc.get("ownerResponse")):
        doc["responseRevision"] = (existing.get("responseRevision") or 0) + 1
        doc["ownerRespondedAt"] = now_iso


def _track_event_change(doc: dict[str, Any], existing: dict[str, Any]) -> None:
    """活动变更追踪：取消必填原因，信息变更必填摘要，修订号服务端托管。"""
    now_iso = datetime.now(timezone.utc).isoformat()
    if existing.get("status") in ("active", "full") and doc.get("status") == "cancelled":
        if not _text(doc.get("cancelReason")):
            raise BalaError("取消活动需填写原因", "REQUIRED_FIELD")
        doc["cancelledAt"] = now_iso
        doc["changeRevision"] = (existing.get("changeRevision") or 0) + 1
        return
    changed = any(
        doc.get(field) != existing.get(field)
        for field in ("startAt", "endAt", "location", "description")
    )
    if changed:
        if not _text(doc.get("changeSummary")):
            raise BalaError("修改活动信息需填写变更摘要", "REQUIRED_FIELD")
        doc["changeRevision"] = (existing.get("changeRevision") or 0) + 1
        doc["changedAt"] = now_iso


def clean_layout(payload: dict[str, Any]) -> dict[str, Any]:
    sections = payload.get("sections")
    if not isinstance(sections, list) or len(sections) > 20:
        raise BalaError("首页版块格式不正确", "INVALID_LAYOUT")
    allowed = {item[0] for item in SECTION_TYPES}
    ids = set()
    cleaned = []
    for index, section in enumerate(sections):
        if not isinstance(section, dict) or section.get("type") not in allowed:
            raise BalaError("存在不支持的版块类型", "INVALID_LAYOUT")
        section_id = _text(section.get("id")) or f"section-{uuid.uuid4().hex[:10]}"
        if section_id in ids:
            raise BalaError("版块 ID 不能重复", "INVALID_LAYOUT")
        ids.add(section_id)
        config = section.get("config") if isinstance(section.get("config"), dict) else {}
        limit = config.get("limit")
        clean_config: dict[str, Any] = {"limit": min(20, max(1, int(limit or 5)))}
        if section["type"] == "quickEntries":
            items = config.get("items") or []
            clean_config["items"] = []
            for item_index, item in enumerate(items[:20]):
                route = _text(item.get("to"))
                label = _text(item.get("label"))
                if not label or not route.startswith("/") or route.startswith("//"):
                    raise BalaError("快捷入口需填写名称和以 / 开头的站内路径", "INVALID_LAYOUT")
                clean_config["items"].append({"key": _text(item.get("key")) or f"entry-{item_index}", "label": label, "icon": _text(item.get("icon")) or "•", "to": route})
        cleaned.append({"id": section_id, "type": section["type"], "title": _text(section.get("title")) or dict(SECTION_TYPES)[section["type"]], "enabled": bool(section.get("enabled", True)), "sortOrder": index, "config": clean_config})
    return {"_id": "home", "sections": cleaned, "updatedAt": datetime.now(timezone.utc).isoformat()}


async def _get_document_raw(collection: str, doc_id: str) -> dict[str, Any] | None:
    _schema(collection)
    if settings.web_data_mode == "local":
        repo = get_repository()
        assert isinstance(repo, LocalRepository)
        return await repo.store.get(collection, doc_id)
    rows = await cloudbase_client.query(collection, where={"_id": doc_id}, limit=1)
    return rows[0] if rows else None


async def list_documents(collection: str, principal: AdminPrincipal | None = None) -> list[dict[str, Any]]:
    actor = _assert_collection_allowed(collection, principal, "read")
    if settings.web_data_mode == "local":
        repo = get_repository()
        assert isinstance(repo, LocalRepository)
        documents = await repo.store.docs(collection)
    else:
        where = None
        if actor.role == ROLE_CLUB_MODERATOR:
            where = {
                "clubs": {"_id": actor.club_id},
                "club_posts": {"clubId": actor.club_id},
                "events": {"organizerType": "club", "organizerId": actor.club_id},
            }[collection]
        documents = await cloudbase_client.query(collection, where=where, limit=100)
    if actor.role == ROLE_CLUB_MODERATOR:
        documents = [doc for doc in documents if _document_in_scope(collection, doc, actor)]
    return documents


async def get_document(collection: str, doc_id: str, principal: AdminPrincipal | None = None) -> dict[str, Any] | None:
    actor = _assert_collection_allowed(collection, principal, "read")
    document = await _get_document_raw(collection, doc_id)
    if document:
        _assert_document_scope(collection, document, actor)
    return document


_FLOWBACK_LIMIT = 200


async def _poll_voters(poll_id: str) -> list[str]:
    """投过该投票的全部 openid（去重，按 _FLOWBACK_LIMIT 截断）。"""
    if settings.web_data_mode == "local":
        repo = get_repository()
        assert isinstance(repo, LocalRepository)
        ballots = await repo.store.docs("ballots")
        voters = [b.get("_openid") for b in ballots if b.get("pollId") == poll_id and b.get("_openid")]
    else:
        voters = []
        skip = 0
        while len(voters) < _FLOWBACK_LIMIT:
            rows = await cloudbase_client.query("ballots", where={"pollId": poll_id}, limit=100, skip=skip)
            if not rows:
                break
            voters.extend(row.get("_openid") for row in rows if row.get("_openid"))
            if len(rows) < 100:
                break
            skip += 100
    return list(dict.fromkeys(voters))


async def _flowback_messages(collection: str, existing: dict[str, Any] | None, saved: dict[str, Any]) -> None:
    """结果回流：运营侧发布结果 / 回应 / 活动变更时，给相关用户写消息中心文档。新建文档不触发。"""
    if not existing:
        return
    now_iso = datetime.now(timezone.utc).isoformat()
    recipients: list[str] = []
    if collection == "polls":
        if existing.get("resultStatus") != saved.get("resultStatus") and saved.get("resultStatus") == "published":
            recipients = await _poll_voters(saved.get("_id") or "")
            message = {"type": "poll_result", "refType": "poll", "refId": saved.get("_id"), "title": "投票结果已公示", "content": saved.get("title") or ""}
        elif existing.get("ownerResponse") != saved.get("ownerResponse") and saved.get("ownerResponse"):
            recipients = await _poll_voters(saved.get("_id") or "")
            message = {"type": "owner_response", "refType": "poll", "refId": saved.get("_id"), "title": "负责人已回应", "content": saved.get("title") or ""}
        else:
            return
    elif collection == "events":
        if existing.get("changeRevision") != saved.get("changeRevision") and saved.get("status") != "cancelled":
            recipients = saved.get("registeredOpenids") or []
            message = {"type": "event_change", "refType": "event", "refId": saved.get("_id"), "title": "活动信息有变更", "content": saved.get("changeSummary") or saved.get("title") or ""}
        elif existing.get("status") != "cancelled" and saved.get("status") == "cancelled":
            recipients = list(saved.get("registeredOpenids") or []) + list(saved.get("waitlistOpenids") or [])
            message = {"type": "event_cancelled", "refType": "event", "refId": saved.get("_id"), "title": "活动已取消", "content": saved.get("cancelReason") or ""}
        else:
            return
    else:
        return

    if len(recipients) > _FLOWBACK_LIMIT:
        print(f"[flowback] 单次回流超过 {_FLOWBACK_LIMIT} 人，已跳过：{collection}/{saved.get('_id')}")
        return

    if settings.web_data_mode == "local":
        repo = get_repository()
        assert isinstance(repo, LocalRepository)
        for openid in recipients:
            await repo.store.insert("messages", {"_openid": openid, **message, "createdAt": now_iso, "readAt": None})
    else:
        for openid in recipients:
            await cloudbase_client.add("messages", {"_openid": openid, **message, "createdAt": now_iso, "readAt": None})


async def save_document(
    collection: str,
    payload: dict[str, Any],
    doc_id: str = "",
    principal: AdminPrincipal | None = None,
) -> dict[str, Any]:
    actor = _assert_collection_allowed(collection, principal, "update" if doc_id else "create")
    existing = await _get_document_raw(collection, doc_id) if doc_id else None
    if doc_id and not existing:
        raise BalaError("内容不存在，可能已被删除", "NOT_FOUND", 404)
    if existing:
        _assert_document_scope(collection, existing, actor)
    doc = clean_document(collection, payload, existing)
    if actor.role == ROLE_CLUB_MODERATOR:
        if collection == "club_posts":
            doc["clubId"] = actor.club_id
        elif collection == "events":
            doc.update({"organizerType": "club", "organizerId": actor.club_id})
    if settings.web_data_mode == "local":
        repo = get_repository()
        assert isinstance(repo, LocalRepository)
        if doc_id:
            doc["_id"] = doc_id
        saved = await repo.store.put(collection, doc)
    else:
        data = {key: value for key, value in doc.items() if key != "_id"}
        if doc_id:
            await cloudbase_client.update(collection, {"_id": doc_id}, data)
            saved = {**doc, "_id": doc_id}
        else:
            new_id = await cloudbase_client.add(collection, data)
            saved = {**doc, "_id": new_id}
    await _flowback_messages(collection, existing, saved)
    web_service.invalidate_cache()
    return saved


async def delete_document(collection: str, doc_id: str, principal: AdminPrincipal | None = None) -> None:
    actor = _assert_collection_allowed(collection, principal, "delete")
    existing = await _get_document_raw(collection, doc_id)
    if not existing:
        raise BalaError("内容不存在，可能已被删除", "NOT_FOUND", 404)
    _assert_document_scope(collection, existing, actor)
    if settings.web_data_mode == "local":
        repo = get_repository()
        assert isinstance(repo, LocalRepository)
        await repo.store.delete(collection, doc_id)
    else:
        await cloudbase_client.delete(collection, {"_id": doc_id})
    web_service.invalidate_cache()


async def get_layout() -> dict[str, Any]:
    if settings.web_data_mode == "local":
        repo = get_repository()
        assert isinstance(repo, LocalRepository)
        return await repo.store.get("site_pages", "home") or default_layout()
    rows = await cloudbase_client.query("site_pages", where={"_id": "home"}, limit=1)
    return rows[0] if rows else default_layout()


async def save_layout(payload: dict[str, Any]) -> dict[str, Any]:
    doc = clean_layout(payload)
    if settings.web_data_mode == "local":
        repo = get_repository()
        assert isinstance(repo, LocalRepository)
        saved = await repo.store.put("site_pages", doc)
    else:
        existing = await cloudbase_client.query("site_pages", where={"_id": "home"}, limit=1)
        if existing:
            await cloudbase_client.update("site_pages", {"_id": "home"}, {"sections": doc["sections"], "updatedAt": doc["updatedAt"]})
        else:
            await cloudbase_client.add("site_pages", doc)
        saved = doc
    web_service.invalidate_cache()
    return saved


__all__ = ["COLLECTIONS", "SECTION_TYPES", "DEFAULT_LAYOUT", "default_layout", "new_document", "clean_document", "clean_layout", "list_documents", "get_document", "save_document", "delete_document", "get_layout", "save_layout"]
