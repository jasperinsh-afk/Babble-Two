"""网页版编排层（web_service）测试：白名单、写入门禁与身份读缓存。"""
from __future__ import annotations

import pytest

from app.config import settings
from app.repository.base import BalaError
from app.services import web_service

IDENTITY_A = "web:" + "a" * 32
IDENTITY_B = "web:" + "b" * 32


def test_allowed_actions_contains_new_entries():
    for action in ("messages", "markRead", "messagePrefs"):
        assert action in web_service.ALLOWED_ACTIONS["me"]
    assert "track" in web_service.ALLOWED_ACTIONS["analytics"]
    assert "adminIngest" not in web_service.ALLOWED_ACTIONS
    assert "seedImport" not in web_service.ALLOWED_ACTIONS

    for action in ("markRead", "messagePrefs"):
        assert ("me", action) in web_service.WRITE_ACTIONS
    assert ("analytics", "track") in web_service.WRITE_ACTIONS


def test_read_ttl_excludes_identity_scoped_actions():
    """个人数据（me.* / analytics.*）严禁进读缓存：缓存键不含身份，会串用户。"""
    for fn, action in web_service.READ_TTL:
        assert fn not in ("me", "analytics"), (fn, action)


async def test_unknown_action_rejected():
    with pytest.raises(BalaError) as exc:
        await web_service.call("adminIngest", "run", {}, IDENTITY_A)
    assert exc.value.code == "UNKNOWN_ACTION"
    assert exc.value.http_status == 404


async def test_write_gate_cloud_mode(monkeypatch):
    class FakeRepo:
        mode = "cloud"

        async def call(self, fn, action, payload, identity):
            return {"ok": True}

    monkeypatch.setattr(web_service, "get_repository", lambda: FakeRepo())
    monkeypatch.setattr(settings, "WEB_CLOUD_WRITE_ENABLED", False)

    with pytest.raises(BalaError) as denied:
        await web_service.call("me", "markRead", {"all": True}, IDENTITY_A)
    assert denied.value.code == "WRITE_DISABLED"
    assert denied.value.http_status == 409

    monkeypatch.setattr(settings, "WEB_CLOUD_WRITE_ENABLED", True)
    allowed = await web_service.call("me", "markRead", {"all": True}, IDENTITY_A)
    assert allowed == {"ok": True}


async def test_identity_reads_not_cached(monkeypatch):
    calls = []

    class RecordingRepo:
        mode = "local"

        async def call(self, fn, action, payload, identity):
            calls.append(identity)
            return {"identity": identity, "list": [], "hasMore": False, "unread": 0}

    monkeypatch.setattr(web_service, "get_repository", lambda: RecordingRepo())
    monkeypatch.setattr(settings, "WEB_CACHE_ENABLED", True)

    first = await web_service.call("me", "messages", {}, IDENTITY_A)
    second = await web_service.call("me", "messages", {}, IDENTITY_B)
    assert first["identity"] == IDENTITY_A
    assert second["identity"] == IDENTITY_B
    assert calls == [IDENTITY_A, IDENTITY_B]  # 每次都真打到仓储，没有命中缓存
