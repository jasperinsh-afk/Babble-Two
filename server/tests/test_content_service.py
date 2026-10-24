"""站点内容管理与后台访问边界测试。"""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.repository.base import BalaError
from app.repository.local_repo import LocalRepository
from app.repository.local_store import DocumentStore
from app.services import content_service

SEED = Path(__file__).resolve().parent.parent.parent / "cloudfunctions/seedImport/seed_data.json"


@pytest.fixture
async def content_repo(tmp_path, monkeypatch):
    store = DocumentStore(str(tmp_path / "content.db"), seed_file=str(SEED), shift_dates=True)
    repo = LocalRepository(store)
    await store.ensure_ready()
    monkeypatch.setattr(settings, "WEB_DATA_MODE", "local")
    monkeypatch.setattr(content_service, "get_repository", lambda: repo)
    yield repo
    await store.close()


async def test_layout_save_drives_home_feed(content_repo):
    layout = content_service.default_layout()
    layout["sections"] = [layout["sections"][3], layout["sections"][0]]
    layout["sections"][0]["title"] = "大家正在投"
    saved = await content_service.save_layout(layout)
    assert [section["type"] for section in saved["sections"]] == ["hotPolls", "banner"]
    assert saved["sections"][0]["sortOrder"] == 0

    feed = await content_repo.call("home", "feed", {}, "web:" + "a" * 32)
    assert feed["sections"][0]["title"] == "大家正在投"


async def test_content_crud_and_field_validation(content_repo):
    created = await content_service.save_document("banners", {
        "title": "测试 Banner",
        "imageUrl": "/assets/brand/logo-mark.png",
        "targetRoute": "/vote",
        "sort": 3,
        "isActive": True,
    })
    assert created["_id"]
    updated = await content_service.save_document("banners", {**created, "title": "新标题"}, created["_id"])
    assert updated["title"] == "新标题"
    await content_service.delete_document("banners", created["_id"])
    assert await content_service.get_document("banners", created["_id"]) is None

    with pytest.raises(BalaError):
        await content_service.save_document("banners", {"title": "", "imageUrl": "javascript:alert(1)"})


async def test_quick_entries_only_allow_internal_routes(content_repo):
    layout = content_service.default_layout()
    quick = next(section for section in layout["sections"] if section["type"] == "quickEntries")
    quick["config"]["items"][0]["to"] = "https://example.com"
    with pytest.raises(BalaError):
        await content_service.save_layout(layout)


async def test_poll_result_fields_roundtrip(content_repo):
    poll = await content_service.get_document("polls", "p001")
    saved = await content_service.save_document(
        "polls",
        {
            **poll,
            "resultStatus": "published",
            "resultScope": "campus",
            "sampleNote": "样本 32 人",
            "ownerType": "school",
            "ownerName": "学生会",
            "ownerResponse": "已关注食堂改进建议",
        },
        "p001",
    )
    assert saved["resultStatus"] == "published"
    assert saved["resultScope"] == "campus"
    assert saved["sampleNote"] == "样本 32 人"
    assert saved["resultRevision"] == 1
    assert saved["resultPublishedAt"]
    assert saved["responseRevision"] == 1
    assert saved["ownerRespondedAt"]

    reread = await content_service.get_document("polls", "p001")
    assert reread["resultStatus"] == "published"
    assert reread["ownerResponse"] == "已关注食堂改进建议"

    # 重复发布同一状态不重复累计修订号
    again = await content_service.save_document("polls", {**reread}, "p001")
    assert again["resultRevision"] == 1


async def test_event_change_revision(content_repo):
    event = await content_service.get_document("events", "e001")
    assert event["status"] == "active"

    # 改信息不带摘要 → 拒绝
    with pytest.raises(BalaError) as denied:
        await content_service.save_document("events", {**event, "location": "体育馆"}, "e001")
    assert denied.value.code == "REQUIRED_FIELD"

    changed = await content_service.save_document(
        "events", {**event, "location": "体育馆", "changeSummary": "场地调整"}, "e001"
    )
    assert changed["location"] == "体育馆"
    assert changed["changeRevision"] == 1
    assert changed["changedAt"]

    # 取消不带原因 → 拒绝
    with pytest.raises(BalaError) as denied:
        await content_service.save_document("events", {**changed, "status": "cancelled"}, "e001")
    assert denied.value.code == "REQUIRED_FIELD"

    cancelled = await content_service.save_document(
        "events", {**changed, "status": "cancelled", "cancelReason": "恶劣天气"}, "e001"
    )
    assert cancelled["status"] == "cancelled"
    assert cancelled["cancelledAt"]
    assert cancelled["changeRevision"] == 2


async def test_result_backfill_creates_messages(content_repo):
    voter = "web:" + "c" * 32
    waiter = "web:" + "d" * 32
    await content_repo.call("vote", "cast", {"pollId": "p001", "optionIds": ["p001o1"]}, voter)
    await content_repo.call("vote", "cast", {"pollId": "p001", "optionIds": ["p001o1"]}, waiter)

    poll = await content_service.get_document("polls", "p001")
    published = await content_service.save_document("polls", {**poll, "resultStatus": "published"}, "p001")
    assert published["resultRevision"] == 1
    result_messages = [m for m in await content_repo.store.docs("messages") if m.get("refId") == "p001"]
    assert len(result_messages) == 2
    assert {m["_openid"] for m in result_messages} == {voter, waiter}
    assert all(m["type"] == "poll_result" and m["readAt"] is None for m in result_messages)

    responded = await content_service.save_document(
        "polls",
        {**published, "ownerType": "school", "ownerName": "学生会", "ownerResponse": "已关注"},
        "p001",
    )
    assert responded["responseRevision"] == 1
    owner_messages = [m for m in await content_repo.store.docs("messages") if m["type"] == "owner_response"]
    assert len(owner_messages) == 2
    assert {m["_openid"] for m in owner_messages} == {voter, waiter}

    # 活动：只发报名者不发候补；取消则报名 + 候补都发
    event = await content_service.get_document("events", "e001")
    await content_repo.call("event", "join", {"eventId": "e001"}, waiter)
    changed = await content_service.save_document(
        "events", {**event, "location": "体育馆", "changeSummary": "场地调整"}, "e001"
    )
    change_messages = [m for m in await content_repo.store.docs("messages") if m["type"] == "event_change"]
    assert len(change_messages) == 1
    assert change_messages[0]["_openid"] == waiter

    full = await content_repo.store.get("events", "e001")
    capped = {**full, "maxParticipants": full.get("participantCount") or 0}
    await content_repo.store.put("events", capped)
    waitlist_user = "web:" + "e" * 32
    joined = await content_repo.call("event", "join", {"eventId": "e001"}, waitlist_user)
    assert joined["waitlisted"] is True

    cancelled = await content_service.save_document(
        "events", {**capped, "status": "cancelled", "cancelReason": "恶劣天气"}, "e001"
    )
    assert cancelled["status"] == "cancelled"
    cancel_messages = [m for m in await content_repo.store.docs("messages") if m["type"] == "event_cancelled"]
    assert len(cancel_messages) == 2
    assert {m["_openid"] for m in cancel_messages} == {waiter, waitlist_user}


def test_admin_entry_and_content_api_require_password(monkeypatch):
    monkeypatch.setattr(settings, "ADMIN_WEB_TOKEN", "test-password")
    client = TestClient(app)
    response = client.get("/admin", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/admin/web/content"

    protected = client.get("/admin/web/content/api/layout", follow_redirects=False)
    assert protected.status_code == 307
    assert protected.headers["location"] == "/admin/web/login"

    login = client.post("/admin/web/login", data={"token": "test-password"}, follow_redirects=False)
    assert login.status_code == 303
    assert login.headers["location"] == "/admin/web/content"
    assert client.get("/admin/web/content").status_code == 200
