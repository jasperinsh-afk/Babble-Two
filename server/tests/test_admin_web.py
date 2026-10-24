"""运营后台活动审核动作测试：approve 必须落到 active 并刷新 updatedAt。

cloudbase_client 用内存假客户端替换（与 test_admin_permissions.py 一致的
monkeypatch 思路），不触达微信云开发 HTTP API。
"""
from __future__ import annotations

from datetime import datetime

import pytest

from app import admin_web


class FakeCloudbase:
    """记录 update 调用并维护一份内存 events 文档。"""

    def __init__(self):
        self.docs = {
            "events": {
                "e001": {
                    "_id": "e001",
                    "status": "pending",
                    "updatedAt": "2020-01-01T00:00:00",
                }
            }
        }
        self.updates = []

    async def update(self, collection, where, patch):
        self.updates.append((collection, where, patch))
        doc = self.docs[collection][where["_id"]]
        doc.update(patch)
        return 1


@pytest.fixture
def cloud(monkeypatch):
    fake = FakeCloudbase()
    monkeypatch.setattr(admin_web, "cloudbase_client", fake)
    return fake


async def test_event_approve_sets_active(cloud):
    result = await admin_web.event_action("e001", "approve", _=None)
    assert result == {"ok": True}

    assert cloud.updates, "approve 必须触发一次云数据库 update"
    collection, where, patch = cloud.updates[0]
    assert collection == "events"
    assert where == {"_id": "e001"}
    assert patch["status"] == "active"

    doc = cloud.docs["events"]["e001"]
    assert doc["status"] == "active"
    assert doc["updatedAt"] != "2020-01-01T00:00:00"
    datetime.fromisoformat(doc["updatedAt"])  # 可解析即刷新成功


async def test_event_approve_rejects_unknown_action(cloud):
    result = await admin_web.event_action("e001", "nuke", _=None)
    assert result == {"ok": True}
    assert cloud.updates == []
    assert cloud.docs["events"]["e001"]["status"] == "pending"
