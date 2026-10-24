"""三端互通回归：云端日期类型、读取格式与云函数查询必需字段。

背景：小程序云函数用 `endAt: _.gt(new Date())` 筛选进行中的投票/活动，
且 `vote.list` / `home.feed` 要求 `isDeleted: false`。后台若写入字符串日期
或缺少这些字段，内容就不会出现在小程序与网页客户端。
"""
from __future__ import annotations

from datetime import datetime, timezone

from app import cloudbase_client
from app.services import content_service


def test_js_serializes_iso_string_as_cloud_date():
    assert cloudbase_client._js("2026-10-25T02:00:00.000Z") == 'new Date("2026-10-25T02:00:00.000Z")'


def test_js_serializes_datetime_as_cloud_date():
    value = datetime(2026, 10, 25, 2, 0, tzinfo=timezone.utc)
    assert cloudbase_client._js(value) == 'new Date("2026-10-25T02:00:00.000Z")'


def test_js_recurses_into_documents_and_keeps_plain_fields():
    expr = cloudbase_client._js({
        "title": "秋季运动会",
        "endAt": "2026-10-25T02:00:00.000Z",
        "isDeleted": False,
        "options": [{"label": "A", "sortOrder": 0}],
    })
    assert 'new Date("2026-10-25T02:00:00.000Z")' in expr
    assert '"title":"秋季运动会"' in expr
    assert '"isDeleted":false' in expr
    assert '"options":[{"label":"A","sortOrder":0}]' in expr


def test_js_does_not_treat_ids_or_text_as_dates():
    assert cloudbase_client._js({"_id": "c001"}) == '{"_id":"c001"}'
    assert cloudbase_client._js("2026 年 10 月活动") == '"2026 年 10 月活动"'


def test_js_where_clause_uses_date_objects_for_time_filters():
    expr = cloudbase_client._js({"endAt": {"$gt": "2026-10-25T02:00:00.000Z"}})
    assert 'new Date("2026-10-25T02:00:00.000Z")' in expr


def test_normalize_dates_restores_iso_from_mongo_extended_json():
    stamp = int(datetime(2026, 10, 25, 2, 0, tzinfo=timezone.utc).timestamp() * 1000)
    rows = cloudbase_client._normalize_dates({
        "items": [{"endAt": {"$date": stamp}, "title": "投票"}]
    })
    assert rows["items"][0]["endAt"] == "2026-10-25T02:00:00.000Z"
    assert rows["items"][0]["title"] == "投票"


def test_new_poll_contains_fields_required_by_cloud_queries():
    doc = content_service.new_document("polls")
    # vote.list / home.feed 都带 where({isDeleted: false})，缺失字段不会命中
    assert doc["isDeleted"] is False
    assert doc["totalVotes"] == 0
    assert doc["participantCount"] == 0
    assert doc["reviewStatus"] == "approved"


def test_new_event_contains_fields_required_by_cloud_queries():
    doc = content_service.new_document("events")
    assert doc["isDeleted"] is False
    assert doc["registeredOpenids"] == []
    assert doc["waitlistOpenids"] == []


def test_new_club_contains_fields_required_by_cloud_queries():
    doc = content_service.new_document("clubs")
    assert doc["isDeleted"] is False
    assert doc["memberOpenids"] == []


def test_cleaned_poll_keeps_visibility_defaults():
    doc = content_service.clean_document("polls", {
        "title": "三端互通验证",
        "pollType": "single",
        "status": "active",
        "startAt": "2026-10-25T02:00:00.000Z",
        "endAt": "2026-10-26T02:00:00.000Z",
        "options": [{"label": "同意"}, {"label": "不同意"}],
    })
    assert doc["isDeleted"] is False
    assert len(doc["options"]) == 2
    assert all(option["optionId"] for option in doc["options"])
    # 保存到云端时，起止时间必须是 Date 类型表达式
    expr = cloudbase_client._js({"startAt": doc["startAt"], "endAt": doc["endAt"]})
    assert expr.count("new Date(") == 2
