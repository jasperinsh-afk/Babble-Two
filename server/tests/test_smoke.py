"""冒烟测试：注册登录 → 投票幂等 → 改票限制 → 社团 → 活动 → NFC → 导出脱敏。

运行：
    python -m pytest tests -v
"""
from __future__ import annotations

import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)


def _unique(prefix: str = "u") -> str:
    return f"{prefix}{uuid.uuid4().hex[:8]}"


def _register(role_hint: str = ""):
    """注册一个新用户并返回 (student_id, token, user_id)。"""
    sid = f"{20250000 + int(uuid.uuid4().hex[:4], 16) % 9999}"
    email = f"{_unique('t')}@qd.baoan.edu.cn"
    code_resp = client.post("/api/v1/auth/send-code", json={"email": email})
    assert code_resp.status_code == 200, code_resp.text
    code = code_resp.json()["data"].get("dev_code")

    resp = client.post(
        "/api/v1/auth/register",
        json={
            "student_id": sid,
            "email": email,
            "password": "goqd1234",
            "nickname": _unique("用户"),
            "email_code": code,
            "grade": "11",
            "dormitory": "A305",
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    return sid, data["token"]["access_token"], data["user"]["id"]


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── 系统 ──


def test_healthz():
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json()["code"] == 0


def test_uniform_response_shape():
    r = client.get("/api/v1/votes")
    body = r.json()
    assert set(["code", "message", "data", "timestamp"]).issubset(body.keys())


# ── 认证 ──


def test_register_and_login():
    sid, token, uid = _register()
    r = client.post("/api/v1/auth/login", json={"student_id": sid, "password": "goqd1234"})
    assert r.status_code == 200, r.text
    assert r.json()["data"]["token"]["access_token"]

    # 错误密码
    r2 = client.post("/api/v1/auth/login", json={"student_id": sid, "password": "wrong1234"})
    assert r2.status_code == 401


def test_weak_password_rejected():
    email = f"{_unique('w')}@qd.baoan.edu.cn"
    client.post("/api/v1/auth/send-code", json={"email": email})
    r = client.post(
        "/api/v1/auth/register",
        json={
            "student_id": "20259999",
            "email": email,
            "password": "1234",
            "nickname": "弱密码",
            "email_code": "000000",
        },
    )
    assert r.status_code == 422  # Pydantic 校验拦截


def test_non_school_email_rejected():
    r = client.post("/api/v1/auth/send-code", json={"email": "someone@gmail.com"})
    assert r.status_code == 400


def test_me_requires_auth():
    r = client.get("/api/v1/users/me")
    assert r.status_code == 401


# ── 首页 ──


def test_home_feed():
    r = client.get("/api/v1/home/feed")
    assert r.status_code == 200
    data = r.json()["data"]
    assert "banners" in data
    assert "today_poll" in data
    assert "hot_polls" in data


# ── 投票中心 ──


def test_poll_list_and_detail():
    r = client.get("/api/v1/votes")
    assert r.status_code == 200
    items = r.json()["data"]["items"]
    assert len(items) > 0
    poll = next(p for p in items if len(p["options"]) >= 2)
    d = client.get(f"/api/v1/votes/{poll['id']}")
    assert d.status_code == 200
    assert len(d.json()["data"]["options"]) >= 2


def test_vote_idempotent_and_change_once():
    _, token, _ = _register()
    polls = client.get("/api/v1/votes").json()["data"]["items"]
    poll = next(p for p in polls if p["poll_type"] in ("single", "pk"))
    pid = poll["id"]
    opt = poll["options"][0]["id"]

    r1 = client.post(f"/api/v1/votes/{pid}/cast", json={"option_ids": [opt]}, headers=auth(token))
    assert r1.status_code == 200, r1.text
    assert r1.json()["data"]["has_voted"] is True

    # 幂等：再次提交视为改票，允许一次
    opt2 = poll["options"][1]["id"]
    r2 = client.put(f"/api/v1/votes/{pid}/cast", json={"option_ids": [opt2]}, headers=auth(token))
    assert r2.status_code == 200, r2.text
    assert r2.json()["data"]["is_changed"] is True

    # 第二次修改被拒
    r3 = client.put(f"/api/v1/votes/{pid}/cast", json={"option_ids": [opt]}, headers=auth(token))
    assert r3.status_code == 400
    assert r3.json()["code"] == 3005


def test_vote_requires_login():
    polls = client.get("/api/v1/votes").json()["data"]["items"]
    r = client.post(
        f"/api/v1/votes/{polls[0]['id']}/cast",
        json={"option_ids": [polls[0]["options"][0]["id"]]},
    )
    assert r.status_code == 401


def test_results_and_breakdown():
    polls = client.get("/api/v1/votes").json()["data"]["items"]
    pid = polls[0]["id"]
    r = client.get(f"/api/v1/votes/{pid}/results")
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["total_votes"] >= 0
    assert isinstance(data["options"], list)


def test_comment_requires_vote_first():
    _, token, _ = _register()
    polls = client.get("/api/v1/votes").json()["data"]["items"]
    r = client.post(
        f"/api/v1/votes/{polls[0]['id']}/comments",
        json={"content": "我还没投票就想说话"},
        headers=auth(token),
    )
    assert r.status_code == 400
    assert r.json()["code"] == 3012


def test_comment_after_vote():
    _, token, _ = _register()
    polls = client.get("/api/v1/votes").json()["data"]["items"]
    poll = next(p for p in polls if p["poll_type"] in ("single", "pk"))
    client.post(
        f"/api/v1/votes/{poll['id']}/cast",
        json={"option_ids": [poll["options"][0]["id"]]},
        headers=auth(token),
    )
    r = client.post(
        f"/api/v1/votes/{poll['id']}/comments",
        json={"content": "这是我的立场，理由很充分。"},
        headers=auth(token),
    )
    assert r.status_code == 200, r.text


# ── 社团 ──


def test_club_list_and_join():
    _, token, _ = _register()
    clubs = client.get("/api/v1/clubs").json()["data"]["items"]
    assert len(clubs) > 0
    cid = clubs[0]["id"]
    r = client.post(f"/api/v1/clubs/{cid}/join", headers=auth(token))
    assert r.status_code == 200, r.text
    posts = client.get(f"/api/v1/clubs/{cid}/posts")
    assert posts.status_code == 200


def test_club_post_requires_admin():
    _, token, _ = _register()
    clubs = client.get("/api/v1/clubs").json()["data"]["items"]
    r = client.post(
        f"/api/v1/clubs/{clubs[0]['id']}/posts",
        json={"content": "普通学生不该能发社团帖"},
        headers=auth(token),
    )
    assert r.status_code == 403


# ── 活动 ──


def test_event_list_and_calendar():
    now = datetime.now(timezone.utc)
    r = client.get("/api/v1/events")
    assert r.status_code == 200
    c = client.get(f"/api/v1/events/calendar?year={now.year}&month={now.month}")
    assert c.status_code == 200
    assert isinstance(c.json()["data"], list)


def test_event_register_and_cancel():
    _, token, _ = _register()
    events = client.get("/api/v1/events").json()["data"]["items"]
    if not events:
        pytest.skip("无活动数据")
    eid = events[0]["id"]
    r = client.post(f"/api/v1/events/{eid}/join", headers=auth(token))
    assert r.status_code in (200, 400), r.text
    r2 = client.delete(f"/api/v1/events/{eid}/join", headers=auth(token))
    assert r2.status_code == 200


# ── 住宿生活 ──


def test_living_channels_visibility():
    r = client.get("/api/v1/living/channels")
    assert r.status_code == 200
    # 未登录只能看到全校频道
    assert len(r.json()["data"]) >= 1


def test_lost_found():
    r = client.get("/api/v1/living/lost-found")
    assert r.status_code == 200


# ── OMEGA / NFC ──


def test_nfc_resolve_and_redirect_page():
    r = client.get("/api/v1/nfc/QD-CT-01-A01")
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    assert data["card_id"] == "QD-CT-01-A01"
    assert data["target_type"] in ("vote", "club", "event", "download")

    # 中间页（未装 App）
    page = client.get("/nfc/QD-CT-01-A01")
    assert page.status_code == 200
    assert "七德通" in page.text
    assert "立即下载" in page.text


def test_nfc_unknown_card():
    r = client.get("/api/v1/nfc/NOT-EXIST")
    assert r.status_code == 404


def test_nfc_tap_checkin():
    _, token, _ = _register()
    r = client.post(
        "/api/v1/nfc/tap",
        json={"card_id": "QD-CT-01-A01", "device_type": "android", "app_installed": True},
        headers=auth(token),
    )
    assert r.status_code == 200, r.text
    assert r.json()["data"]["unique_cards"] >= 1


def test_deeplink_verification_files():
    assert client.get("/.well-known/apple-app-site-association").status_code == 200
    assert client.get("/.well-known/assetlinks.json").status_code == 200


# ── 勋章 ──


def test_badges_wall():
    r = client.get("/api/v1/badges")
    assert r.status_code == 200
    items = r.json()["data"]
    assert len(items) >= 9  # PRD §6 定义了 9 个勋章


def test_register_grants_first_badge():
    _, token, _ = _register()
    r = client.get("/api/v1/badges", headers=auth(token))
    earned = [b for b in r.json()["data"] if b["earned_at"]]
    assert len(earned) >= 1


# ── 管理后台权限 ──


def test_admin_requires_operator():
    _, token, _ = _register()
    r = client.get("/api/v1/admin/candidates", headers=auth(token))
    assert r.status_code == 403


def test_admin_web_pages():
    for path in ("", "/candidates", "/polls", "/review", "/nfc", "/export"):
        r = client.get(f"/admin/web{path}")
        assert r.status_code == 200, f"{path} -> {r.status_code}"


# ── 墨麟书院输出层：导出脱敏 ──


def test_export_requires_operator():
    _, token, _ = _register()
    r = client.post(
        "/api/v1/admin/export/votes",
        json={"start_date": "2026-01-01", "end_date": "2026-12-31", "format": "csv"},
        headers=auth(token),
    )
    assert r.status_code == 403


def test_export_desensitized():
    """用管理员账号导出，确认不含任何个人信息字段。"""
    r = client.post(
        "/api/v1/auth/login", json={"student_id": "20240001", "password": "goqd1234"}
    )
    assert r.status_code == 200, "请先运行 python scripts/seed_data.py"
    token = r.json()["data"]["token"]["access_token"]

    resp = client.post(
        "/api/v1/admin/export/votes",
        json={"start_date": "2025-01-01", "end_date": "2027-12-31", "format": "csv"},
        headers=auth(token),
    )
    assert resp.status_code == 200, resp.text
    body = resp.text
    for forbidden in ("user_id", "student_id", "email", "@qd.baoan"):
        assert forbidden not in body, f"导出数据泄露字段：{forbidden}"
    assert "poll_id" in body


# ── 内容审核 ──


def test_sensitive_word_blocks_ugc():
    _, token, _ = _register()
    polls = client.get("/api/v1/votes").json()["data"]["items"]
    poll = next(p for p in polls if p["poll_type"] in ("single", "pk"))
    client.post(
        f"/api/v1/votes/{poll['id']}/cast",
        json={"option_ids": [poll["options"][0]["id"]]},
        headers=auth(token),
    )
    r = client.post(
        f"/api/v1/votes/{poll['id']}/comments",
        json={"content": "测试敏感词A 出现了"},
        headers=auth(token),
    )
    assert r.status_code == 400
    assert r.json()["code"] == 8004
