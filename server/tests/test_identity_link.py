"""网页端 ↔ 小程序账号绑定：绑定码校验、身份解析与业务注入。

运行：pytest tests/test_identity_link.py
绑定码由小程序 identity.issueBindCode 生成（云端），这里直接写入本地文档库，
模拟「小程序已签发」的状态，验证服务端校验与身份归属链路。
"""
from __future__ import annotations

import time

import pytest

from app.repository.base import BalaError
from app.repository.local_repo import LocalRepository
from app.repository.local_store import DocumentStore
from app.services import identity_link, web_service

IDENTITY = "web:" + "a" * 32
OTHER_IDENTITY = "web:" + "b" * 32
OPENID = "oTestOpenId1234567890"
CODE = "123456"


@pytest.fixture
async def repo(tmp_path, monkeypatch):
    store = DocumentStore(str(tmp_path / "link.db"), seed_file="", shift_dates=False)
    repository = LocalRepository(store)
    await store.ensure_ready()
    identity_link.invalidate_cache()
    monkeypatch.setattr(identity_link, "get_repository", lambda: repository)
    yield repository
    identity_link.invalidate_cache()
    await store.close()


async def issue_code(repo, **overrides):
    now = int(time.time() * 1000)
    doc = {
        "_id": CODE,
        "openid": OPENID,
        "createdAt": now,
        "expiresAt": now + 600_000,
        "used": False,
        **overrides,
    }
    await repo.store.put(identity_link.BIND_CODES, doc)
    return doc


async def test_resolve_unbound_identity(repo):
    assert await identity_link.resolve(IDENTITY) == IDENTITY
    status = await identity_link.link_status(IDENTITY)
    assert status["bound"] is False
    assert status["mode"] == "local"


async def test_bind_links_web_identity_to_openid(repo):
    await issue_code(repo)
    result = await identity_link.bind(IDENTITY, CODE)
    assert result["bound"] is True
    assert OPENID not in result["openid"]  # 不回显完整 openid
    assert await identity_link.resolve(IDENTITY) == f"linked:{OPENID}"

    link = await repo.store.get(identity_link.IDENTITY_LINKS, IDENTITY)
    assert link["openid"] == OPENID
    used = await repo.store.get(identity_link.BIND_CODES, CODE)
    assert used["used"] is True  # 一次性


async def test_bind_does_not_leak_to_other_web_identity(repo):
    await issue_code(repo)
    await identity_link.bind(IDENTITY, CODE)
    assert await identity_link.resolve(OTHER_IDENTITY) == OTHER_IDENTITY


async def test_bind_rejects_used_and_expired_codes(repo):
    await issue_code(repo, used=True)
    with pytest.raises(BalaError) as used_error:
        await identity_link.bind(IDENTITY, CODE)
    assert used_error.value.code == "BAD_CODE"

    await issue_code(repo, used=False, expiresAt=int(time.time() * 1000) - 1000)
    with pytest.raises(BalaError) as expired_error:
        await identity_link.bind(IDENTITY, CODE)
    assert expired_error.value.code == "CODE_EXPIRED"


async def test_bind_rejects_malformed_or_unknown_code(repo):
    with pytest.raises(BalaError):
        await identity_link.bind(IDENTITY, "12")
    with pytest.raises(BalaError) as unknown:
        await identity_link.bind(IDENTITY, "000000")
    assert unknown.value.code == "BAD_CODE"
    # 非数字输入会被归一化，纯字母无法凑够 6 位
    with pytest.raises(BalaError):
        await identity_link.bind(IDENTITY, "abcdef")


async def test_unbind_restores_anonymous_identity(repo):
    await issue_code(repo)
    await identity_link.bind(IDENTITY, CODE)
    await identity_link.unbind(IDENTITY)
    assert await identity_link.resolve(IDENTITY) == IDENTITY
    assert (await identity_link.link_status(IDENTITY))["bound"] is False


async def test_web_service_injects_resolved_identity(repo, monkeypatch):
    await issue_code(repo)
    await identity_link.bind(IDENTITY, CODE)
    seen = []

    class RecordingRepo:
        mode = "local"
        store = repo.store

        async def call(self, fn, action, payload, identity):
            seen.append(identity)
            return {"identity": identity}

    monkeypatch.setattr(web_service, "get_repository", lambda: RecordingRepo())
    data = await web_service.call("me", "messages", {}, IDENTITY)
    assert data["identity"] == f"linked:{OPENID}"
    assert seen == [f"linked:{OPENID}"]


async def test_local_repo_writes_bound_openid_without_prefix(repo):
    """绑定后的网页写入，本地库与云端一样归属真实 openid，不带 linked: 前缀。"""
    await repo.call(
        "me",
        "messagePrefs",
        {"prefs": {"deadline": False}},
        f"linked:{OPENID}",
    )
    prefs = await repo.store.docs("message_prefs")
    assert prefs and all(doc["_openid"] == OPENID for doc in prefs)


async def test_resolve_degrades_when_link_collection_unreadable(repo, monkeypatch):
    """云库查询失败时不得阻断业务，按未绑定处理。"""

    class BrokenRepo:
        mode = "local"

        @property
        def store(self):
            raise RuntimeError("store unavailable")

    monkeypatch.setattr(identity_link, "get_repository", lambda: BrokenRepo())
    assert await identity_link.resolve(IDENTITY) == IDENTITY
