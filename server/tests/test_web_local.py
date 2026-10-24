"""网页版本地数据源（LocalRepository）行为测试。

云端规则以 cloudfunctions/*.js 为准，这里验证本地回落实现与之对齐。
运行：pytest tests/test_web_local.py
"""
from __future__ import annotations

from datetime import timedelta

from pathlib import Path

import pytest

from app.repository.base import BalaError
from app.repository.dates import iso, parse_dt, utcnow
from app.repository.local_repo import LocalRepository
from app.repository.local_store import DocumentStore

SEED = Path(__file__).resolve().parent.parent.parent / "cloudfunctions/seedImport/seed_data.json"
IDENTITY = "web:" + "a" * 32
OTHER = "web:" + "b" * 32


@pytest.fixture
async def repo(tmp_path):
    store = DocumentStore(str(tmp_path / "test.db"), seed_file=str(SEED), shift_dates=True)
    repository = LocalRepository(store)
    await store.ensure_ready()
    yield repository
    await store.close()


async def test_home_feed(repo):
    feed = await repo.call("home", "feed", {}, IDENTITY)
    assert len(feed["banners"]) == 2
    assert feed["hotPolls"] and feed["clubs"]
    assert feed["todayPoll"] is not None  # 日期平移后必有进行中的投票


async def test_vote_list_and_detail(repo):
    page = await repo.call("vote", "list", {"tag": "all", "page": 0}, IDENTITY)
    assert len(page["list"]) == 5
    campus = await repo.call("vote", "list", {"tag": "campus", "page": 0}, IDENTITY)
    assert all(p["tag"] == "campus" for p in campus["list"])

    detail = await repo.call("vote", "detail", {"pollId": "p004"}, IDENTITY)
    assert detail["hasVoted"] is False and detail["myChoice"] == []
    assert detail["pollType"] == "ranking"


async def test_vote_cast_updates_counts_and_results(repo):
    before = await repo.call("vote", "results", {"pollId": "p004"}, IDENTITY)
    total_before = before["total"]

    cast = await repo.call(
        "vote", "cast", {"pollId": "p004", "optionIds": ["p004o1", "p004o2"]}, IDENTITY
    )
    assert cast["voted"] is True and cast["changed"] is False

    after = await repo.call("vote", "results", {"pollId": "p004"}, IDENTITY)
    assert after["total"] == total_before + 1
    assert after["options"][0]["count"] == before["options"][0]["count"] + 1

    detail = await repo.call("vote", "detail", {"pollId": "p004"}, IDENTITY)
    assert detail["hasVoted"] is True
    assert detail["myChoice"] == ["p004o1", "p004o2"]

    # 他人身份互不影响
    other = await repo.call("vote", "detail", {"pollId": "p004"}, OTHER)
    assert other["hasVoted"] is False


async def test_vote_change_only_once(repo):
    payload = {"pollId": "p004", "optionIds": ["p004o1", "p004o2"]}
    await repo.call("vote", "cast", payload, IDENTITY)
    changed = await repo.call(
        "vote", "cast", {"pollId": "p004", "optionIds": ["p004o3", "p004o4"]}, IDENTITY
    )
    assert changed["changed"] is True
    with pytest.raises(BalaError):
        await repo.call("vote", "cast", payload, IDENTITY)


async def test_vote_rejects_bad_option_count(repo):
    with pytest.raises(BalaError):
        await repo.call("vote", "cast", {"pollId": "p004", "optionIds": ["p004o1"]}, IDENTITY)
    with pytest.raises(BalaError):
        await repo.call("vote", "cast", {"pollId": "p004", "optionIds": ["nope"]}, IDENTITY)


async def test_groupbuy_join_and_leave(repo):
    joined = await repo.call(
        "vote", "joinChain", {"pollId": "p005", "optionId": "p005o1"}, IDENTITY
    )
    assert joined["voted"] is True
    detail = await repo.call("vote", "detail", {"pollId": "p005"}, IDENTITY)
    assert detail["joined"] is True and detail["joinedOptionId"] == "p005o1"

    left = await repo.call("vote", "leaveChain", {"pollId": "p005"}, IDENTITY)
    assert left["left"] is True
    detail = await repo.call("vote", "detail", {"pollId": "p005"}, IDENTITY)
    assert detail["joined"] is False


async def test_club_join_leave_and_search(repo):
    clubs = await repo.call("club", "list", {"category": "all", "page": 0}, IDENTITY)
    assert len(clubs["list"]) == 6
    searched = await repo.call("club", "list", {"keyword": "辩论", "page": 0}, IDENTITY)
    assert len(searched["list"]) == 1

    await repo.call("club", "join", {"clubId": "c001"}, IDENTITY)
    detail = await repo.call("club", "detail", {"clubId": "c001"}, IDENTITY)
    assert detail["joined"] is True
    again = await repo.call("club", "join", {"clubId": "c001"}, IDENTITY)
    assert again["already"] is True

    await repo.call("club", "leave", {"clubId": "c001"}, IDENTITY)
    detail = await repo.call("club", "detail", {"clubId": "c001"}, IDENTITY)
    assert detail["joined"] is False

    posts = await repo.call("club", "posts", {"clubId": "c001"}, IDENTITY)
    assert posts["list"][0]["isPinned"] is True


async def test_event_calendar_and_join(repo):
    listed = await repo.call("event", "list", {"page": 0}, IDENTITY)
    assert listed["list"], "平移后应有进行中的活动"
    first_start = parse_dt(listed["list"][0]["startAt"])
    calendar = await repo.call(
        "event", "calendar", {"year": first_start.year, "month": first_start.month}, IDENTITY
    )
    assert calendar["events"], "活动所在月份必须能在日历里查到"
    assert calendar["days"]
    joined = await repo.call("event", "join", {"eventId": "e001"}, IDENTITY)
    assert joined["joined"] is True
    detail = await repo.call("event", "detail", {"eventId": "e001"}, IDENTITY)
    assert detail["registered"] is True


async def test_living_panels(repo):
    channels = await repo.call("living", "channels", {}, IDENTITY)
    assert len(channels["list"]) == 5
    posts = await repo.call("living", "channelPosts", {"channelId": "dc1"}, IDENTITY)
    assert len(posts["list"]) == 1
    lost = await repo.call("living", "lostFound", {"kind": "lost"}, IDENTITY)
    assert all(i["kind"] == "lost" for i in lost["list"])
    goods = await repo.call("living", "secondHand", {}, IDENTITY)
    assert len(goods["list"]) == 2


async def test_scan_checkin_badges_and_overview(repo):
    card = await repo.call("scan", "cardByCode", {"key": "QD-CT-01-A01"}, IDENTITY)
    assert card["checked"] is False and card["uniqueCards"] == 0
    assert card["targetType"] == "vote" and card["targetId"] == "p001"

    result = await repo.call("scan", "checkin", {"key": "QD-CT-01-A01"}, IDENTITY)
    assert result["firstTime"] is True and result["uniqueCards"] == 1

    again = await repo.call("scan", "checkin", {"key": "QD-CT-01-A01"}, IDENTITY)
    assert again["firstTime"] is False and again["uniqueCards"] == 1

    for key in ("QD-LB-01-A01", "QD-CL-01-A01"):
        await repo.call("scan", "checkin", {"key": key}, IDENTITY)
    overview = await repo.call("me", "overview", {}, IDENTITY)
    assert overview["stats"]["checkinCount"] == 3
    unlocked = {b["code"] for b in overview["badges"] if b["unlocked"]}
    assert "scan_explorer" in unlocked  # 累计 3 个点位解锁

    with pytest.raises(BalaError):
        await repo.call("scan", "cardByCode", {"key": "NOPE"}, IDENTITY)


async def test_vote_results_restricted_and_extended(repo):
    poll = await repo.store.get("polls", "p001")

    # resultScope=draft → 只回选项骨架
    await repo.store.put("polls", {**poll, "resultScope": "draft", "resultStatus": "published"})
    restricted = await repo.call("vote", "results", {"pollId": "p001"}, IDENTITY)
    assert restricted["restricted"] is True
    assert restricted["total"] == 0
    assert all(set(o.keys()) == {"optionId", "label"} for o in restricted["options"])

    # status=draft 同样受限
    await repo.store.put("polls", {**poll, "status": "draft"})
    draft = await repo.call("vote", "results", {"pollId": "p001"}, IDENTITY)
    assert draft["restricted"] is True

    # 正常返回：扩展字段齐备
    published = {
        **poll,
        "resultScope": "campus",
        "resultStatus": "published",
        "sampleNote": "样本 32 人",
        "ownerType": "school",
        "ownerName": "学生会",
        "ownerResponse": "已关注食堂改进建议",
        "ownerRespondedAt": iso(utcnow()),
    }
    await repo.store.put("polls", published)
    result = await repo.call("vote", "results", {"pollId": "p001"}, IDENTITY)
    assert result["restricted"] is False
    assert result["sampleSize"] == result["total"]
    assert result["percentBasis"] == "votes"  # p001 为单选
    assert result["resultScope"] == "campus"
    assert result["sampleNote"] == "样本 32 人"
    assert result["status"] == "active"
    assert all("count" in o and "percent" in o for o in result["options"])
    assert result["owner"]["ownerName"] == "学生会"
    assert result["owner"]["response"] == "已关注食堂改进建议"
    assert result["owner"]["respondedAt"]

    # 无负责人时 owner 为 None
    await repo.store.put("polls", {**published, "ownerType": None, "ownerName": None})
    plain = await repo.call("vote", "results", {"pollId": "p001"}, IDENTITY)
    assert plain["owner"] is None

    # 多选按人次计百分比
    await repo.store.put("polls", {**published, "pollType": "multi"})
    multi = await repo.call("vote", "results", {"pollId": "p001"}, IDENTITY)
    assert multi["percentBasis"] == "selections"
    assert multi["selectionTotal"] == sum(o["count"] for o in multi["options"])


async def test_event_calendar_excludes_cancelled(repo):
    listed = await repo.call("event", "list", {"page": 0}, IDENTITY)
    assert listed["list"], "平移后应有进行中的活动"
    first = listed["list"][0]
    start = parse_dt(first["startAt"])
    before = await repo.call("event", "calendar", {"year": start.year, "month": start.month}, IDENTITY)
    assert any(e["_id"] == first["_id"] for e in before["events"])

    raw = await repo.store.get("events", first["_id"])
    await repo.store.put("events", {**raw, "status": "cancelled"})
    after = await repo.call("event", "calendar", {"year": start.year, "month": start.month}, IDENTITY)
    assert all(e["_id"] != first["_id"] for e in after["events"])


async def test_home_feed_excludes_ended(repo):
    feed = await repo.call("home", "feed", {}, IDENTITY)
    now = utcnow()
    assert feed["hotPolls"], "平移后应有未结束的热门投票"
    for poll in feed["hotPolls"]:
        assert not poll.get("endAt") or parse_dt(poll["endAt"]) > now
    for event in feed["events"]:
        assert not event.get("endAt") or parse_dt(event["endAt"]) > now

    # 把一条投票的结束时间改到过去，热门列表不再出现
    poll = await repo.store.get("polls", feed["hotPolls"][0]["_id"])
    ended = {**poll, "endAt": iso(now - timedelta(days=1)), "totalVotes": 99999}
    await repo.store.put("polls", ended)
    after = await repo.call("home", "feed", {}, IDENTITY)
    assert all(p["_id"] != poll["_id"] for p in after["hotPolls"])


async def test_unknown_action_rejected(repo):
    with pytest.raises(BalaError):
        await repo.call("vote", "dropTables", {}, IDENTITY)


def _message(identity, index, total):
    return {
        "_openid": identity,
        "type": "poll_result" if index % 2 else "event_change",
        "title": f"消息 {index}",
        "content": "正文",
        "refType": "poll",
        "refId": "p001",
        "readAt": None,
        "createdAt": iso(utcnow() - timedelta(minutes=total - index)),
    }


async def test_me_messages_pagination_and_unread(repo):
    total = 25
    for i in range(total):
        await repo.store.insert("messages", _message(IDENTITY, i, total))

    page1 = await repo.call("me", "messages", {}, IDENTITY)
    assert len(page1["list"]) == 20
    assert page1["hasMore"] is True
    assert page1["unread"] == 25
    assert page1["list"][0]["title"] == "消息 24"  # createdAt 倒序
    assert page1["list"][0]["readAt"] is None

    page2 = await repo.call(
        "me", "messages", {"cursor": page1["list"][-1]["createdAt"]}, IDENTITY
    )
    assert len(page2["list"]) == 5
    assert page2["hasMore"] is False
    assert page2["unread"] == 25
    assert [m["title"] for m in page2["list"]] == ["消息 4", "消息 3", "消息 2", "消息 1", "消息 0"]

    typed = await repo.call("me", "messages", {"type": "poll_result"}, IDENTITY)
    assert all(m["type"] == "poll_result" for m in typed["list"])
    assert typed["unread"] == 25  # 未读数不受 type 过滤影响

    await repo.call("me", "markRead", {"id": page1["list"][0]["_id"]}, IDENTITY)
    unread_only = await repo.call("me", "messages", {"unreadOnly": True}, IDENTITY)
    assert len(unread_only["list"]) == 20
    assert all(m["readAt"] is None for m in unread_only["list"])
    assert unread_only["unread"] == 24


async def test_me_mark_read_only_own(repo):
    mine = await repo.store.insert("messages", _message(IDENTITY, 1, 2))
    theirs = await repo.store.insert("messages", _message(OTHER, 2, 2))

    # 用户 A 标记用户 B 的消息：不得越权
    denied = await repo.call("me", "markRead", {"id": theirs["_id"]}, IDENTITY)
    assert denied["updated"] == 0
    assert (await repo.store.get("messages", theirs["_id"]))["readAt"] is None
    assert (await repo.call("me", "messages", {}, OTHER))["unread"] == 1

    # 标记自己的消息
    own = await repo.call("me", "markRead", {"id": mine["_id"]}, IDENTITY)
    assert own["updated"] == 1
    stored = await repo.store.get("messages", mine["_id"])
    assert stored["readAt"]
    assert (await repo.call("me", "messages", {}, IDENTITY))["unread"] == 0

    # 重复标记已读消息不重复计数
    again = await repo.call("me", "markRead", {"ids": [mine["_id"]]}, IDENTITY)
    assert again["updated"] == 0

    # ids 批量 + all 两种路径
    second = await repo.store.insert("messages", _message(IDENTITY, 3, 4))
    third = await repo.store.insert("messages", _message(IDENTITY, 4, 4))
    batch = await repo.call(
        "me", "markRead", {"ids": [second["_id"], third["_id"]]}, IDENTITY
    )
    assert batch["updated"] == 2
    assert (await repo.call("me", "messages", {}, IDENTITY))["unread"] == 0

    fourth = await repo.store.insert("messages", _message(OTHER, 5, 6))
    fifth = await repo.store.insert("messages", _message(OTHER, 6, 6))
    everything = await repo.call("me", "markRead", {"all": True}, OTHER)
    assert everything["updated"] == 3  # B 的三条未读（最初那条 + 后加两条）
    assert (await repo.call("me", "messages", {}, OTHER))["unread"] == 0


async def test_me_message_prefs_upsert(repo):
    defaults = {
        "eventChange": True,
        "eventCancel": True,
        "pollResult": True,
        "ownerResponse": True,
        "deadline": True,
    }
    first = await repo.call("me", "messagePrefs", {}, IDENTITY)
    assert first["prefs"] == defaults

    saved = await repo.call(
        "me",
        "messagePrefs",
        {
            "prefs": {
                "eventChange": False,
                "eventCancel": True,
                "pollResult": False,
                "ownerResponse": False,
                "deadline": False,
            }
        },
        IDENTITY,
    )
    assert saved["prefs"] == {
        "eventChange": False,
        "eventCancel": True,
        "pollResult": False,
        "ownerResponse": False,
        "deadline": False,
    }

    reread = await repo.call("me", "messagePrefs", {}, IDENTITY)
    assert reread["prefs"]["eventCancel"] is True
    assert reread["prefs"]["eventChange"] is False

    # 第二个用户互不影响
    other = await repo.call("me", "messagePrefs", {}, OTHER)
    assert other["prefs"] == defaults


async def test_analytics_track_writes_without_echo(repo):
    tracked = await repo.call(
        "analytics",
        "track",
        {"event": "today_action_done", "props": {"pollId": "p001"}, "sessionId": "s-1"},
        IDENTITY,
    )
    assert tracked == {"ok": True}

    rows = [r for r in await repo.store.docs("analytics_events") if r["_openid"] == IDENTITY]
    assert len(rows) == 1
    assert rows[0]["event"] == "today_action_done"
    assert rows[0]["props"] == {"pollId": "p001"}
    assert rows[0]["sessionId"] == "s-1"
    assert rows[0]["createdAt"]

    with pytest.raises(BalaError):
        await repo.call("analytics", "track", {"event": ""}, IDENTITY)
