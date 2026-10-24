"""后台三级角色、授权码和社团数据隔离测试。"""
import asyncio
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app import admin_web
from app.config import settings
from app.core import admin_gate
from app.core.admin_gate import AdminPrincipal
from app.core.database import Base
from app.main import app
from app.repository.base import BalaError
from app.repository.local_repo import LocalRepository
from app.repository.local_store import DocumentStore
from app.services import content_service

SEED = Path(__file__).resolve().parent.parent.parent / "cloudfunctions/seedImport/seed_data.json"
MODERATOR = AdminPrincipal(role="club_moderator", nickname="版主", account_id=1, club_id="c001")
REVIEWER = AdminPrincipal(role="reviewer", nickname="审核", account_id=2)


@pytest.fixture
async def content_repo(tmp_path, monkeypatch):
    store = DocumentStore(str(tmp_path / "permissions.db"), seed_file=str(SEED), shift_dates=True)
    repo = LocalRepository(store)
    await store.ensure_ready()
    monkeypatch.setattr(settings, "WEB_DATA_MODE", "local")
    monkeypatch.setattr(content_service, "get_repository", lambda: repo)
    yield repo
    await store.close()


@pytest.fixture
def auth_client(monkeypatch, tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'accounts.db'}")

    async def setup():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(setup())
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(admin_web, "SessionLocal", sessions)
    monkeypatch.setattr(admin_gate, "SessionLocal", sessions)
    monkeypatch.setattr(settings, "CLUB_MODERATOR_AUTH_CODE", "0923")
    monkeypatch.setattr(settings, "REVIEWER_AUTH_CODE", "2012")
    monkeypatch.setattr(settings, "ADMIN_WEB_TOKEN", "test-admin-token")

    async def club_lookup(collection, club_id):
        assert collection == "clubs"
        return {"_id": club_id, "name": "测试社团"} if club_id == "c001" else None

    async def club_list(collection, principal=None):
        return [{"_id": "c001", "name": "测试社团"}]

    monkeypatch.setattr(admin_web.content_service, "get_document", club_lookup)
    monkeypatch.setattr(admin_web.content_service, "list_documents", club_list)
    client = TestClient(app)
    yield client
    client.close()
    asyncio.run(engine.dispose())


def account_form(role, nickname="tester", code="0923"):
    return {
        "role": role,
        "nickname": nickname,
        "password": "testpass123",
        "password_confirm": "testpass123",
        "authorization_code": code,
        "club_id": "c001" if role == "club_moderator" else "",
    }


async def test_moderator_only_reads_and_controls_own_club(content_repo):
    posts = await content_service.list_documents("club_posts", MODERATOR)
    assert posts and {post["clubId"] for post in posts} == {"c001"}
    clubs = await content_service.list_documents("clubs", MODERATOR)
    assert [club["_id"] for club in clubs] == ["c001"]

    with pytest.raises(BalaError) as denied:
        await content_service.get_document("club_posts", "cp003", MODERATOR)
    assert denied.value.http_status == 403
    with pytest.raises(BalaError):
        await content_service.delete_document("club_posts", "cp003", MODERATOR)
    with pytest.raises(BalaError):
        await content_service.list_documents("banners", MODERATOR)


async def test_moderator_cannot_forge_or_transfer_ownership(content_repo):
    created = await content_service.save_document("club_posts", {
        "clubId": "c002",
        "title": "本社团动态",
        "content": "正文",
        "images": ["https://example.com/image.png"],
        "isPinned": False,
        "likeCount": 0,
    }, principal=MODERATOR)
    assert created["clubId"] == "c001"

    updated = await content_service.save_document(
        "club_posts", {**created, "clubId": "c002", "title": "更新标题"}, created["_id"], MODERATOR
    )
    assert updated["clubId"] == "c001"
    assert updated["title"] == "更新标题"
    await content_service.delete_document("club_posts", created["_id"], MODERATOR)


async def test_reviewer_can_edit_and_delete_but_cannot_create(content_repo):
    original = await content_service.get_document("club_posts", "cp003", REVIEWER)
    updated = await content_service.save_document(
        "club_posts", {**original, "title": "审核修改"}, "cp003", REVIEWER
    )
    assert updated["title"] == "审核修改"
    with pytest.raises(BalaError) as denied:
        await content_service.save_document("club_posts", {}, principal=REVIEWER)
    assert denied.value.http_status == 403
    await content_service.delete_document("club_posts", "cp003", REVIEWER)
    assert await content_service.get_document("club_posts", "cp003", REVIEWER) is None


def test_moderator_registration_and_admin_only_routes(auth_client):
    wrong = auth_client.post("/admin/web/register", data=account_form("club_moderator", code="bad"))
    assert wrong.status_code == 200
    assert "授权码不正确" in wrong.text

    registered = auth_client.post(
        "/admin/web/register", data=account_form("club_moderator"), follow_redirects=False
    )
    assert registered.status_code == 303
    content = auth_client.get("/admin/web/content")
    assert content.status_code == 200
    assert "社团版主" in content.text
    assert "爬虫候选池" not in content.text
    assert "数据导出" not in content.text
    assert "点位卡片" not in content.text
    assert "内容审核" not in content.text
    own_club = auth_client.get("/admin/web/content/api/clubs")
    assert own_club.status_code == 200
    assert own_club.json()["data"]["schema"]["canCreate"] is False

    for path in (
        "/admin/web/candidates",
        "/admin/web/nfc",
        "/admin/web/export",
        "/admin/web/review",
        "/api/v1/admin/export/preview",
        "/admin/web/content/api/layout",
        "/admin/web/content/api/banners",
    ):
        assert auth_client.get(path).status_code == 403, path


def test_reviewer_registration_and_content_permissions(auth_client):
    registered = auth_client.post(
        "/admin/web/register", data=account_form("reviewer", code="2012"), follow_redirects=False
    )
    assert registered.status_code == 303
    assert auth_client.get("/admin/web/review").status_code == 200
    content = auth_client.get("/admin/web/content")
    assert content.status_code == 200
    assert "审核员" in content.text
    assert "爬虫候选池" not in content.text

    created = auth_client.post("/admin/web/content/api/banners", json={})
    assert created.status_code == 403
    for path in ("/admin/web/candidates", "/admin/web/nfc", "/admin/web/export", "/api/v1/admin/export/preview"):
        assert auth_client.get(path).status_code == 403, path
