"""本地仓储：无微信凭据时的开发数据源。

业务规则逐条对齐 cloudfunctions/{home,vote,club,event,living,scan,me}/index.js，
使本地模式与云端模式对前端表现一致。云端模式的规则以云函数为准，此处不重写云端。
"""
from __future__ import annotations

import asyncio
import calendar as _calendar
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional

from app.repository.base import BalaError
from app.repository.dates import iso, parse_dt, utcnow
from app.repository.local_store import DocumentStore

PAGE_SIZE = 20

OPTION_RANGE = {
    "single": (1, 1),
    "multi": (1, 8),
    "pk": (1, 1),
    "ranking": (2, 6),
    "groupbuy": (1, 1),
}

LOCATION_RULES = [
    {"type": "canteen", "name": "食堂", "desc": "食堂入口海报，扫码参与今日午餐投票"},
    {"type": "library", "name": "图书馆", "desc": "图书馆一楼公告位，扫码查看读书社团"},
    {"type": "dormitory", "name": "宿舍楼", "desc": "各楼层电梯口，扫码进入住宿圈"},
    {"type": "bulletin", "name": "公告栏", "desc": "中央公告栏，扫码查看全校活动"},
    {"type": "classroom", "name": "教室区", "desc": "教学楼走廊，扫码参与课程相关投票"},
    {"type": "clubroom", "name": "社团活动室", "desc": "社团活动室门口，扫码直达社团主页"},
    {"type": "sports", "name": "体育场馆", "desc": "体育馆入口，扫码报名体育赛事"},
    {"type": "gateway", "name": "校门", "desc": "校门口迎新海报，扫码领取新手勋章"},
]


def _fail(message: str, code: str = ""):
    raise BalaError(message, code)


def _visible(doc: Dict[str, Any]) -> bool:
    return not doc.get("isDeleted", False)


def _dt_key(value: Any) -> float:
    parsed = parse_dt(value)
    return parsed.timestamp() if parsed else 0.0


def _paginate(items: List[Any], page: int, size: int = PAGE_SIZE) -> Dict[str, Any]:
    page = max(int(page or 0), 0)
    chunk = items[page * size : (page + 1) * size]
    return {"list": chunk, "hasMore": len(chunk) == size}


class LocalRepository:
    mode = "local"

    def __init__(self, store: DocumentStore):
        self.store = store
        self._write_lock = asyncio.Lock()

    async def call(
        self, fn: str, action: str, payload: Dict[str, Any], identity: str
    ) -> Optional[Any]:
        await self.store.ensure_ready()
        handler: Optional[Callable] = _ACTIONS.get((fn, action))
        if handler is None:
            raise BalaError(f"未知操作：{fn}.{action}", "UNKNOWN_ACTION", 404)
        return await handler(self, payload or {}, identity)

    # ── 通用读取 ──

    async def _poll(self, poll_id: str) -> Dict[str, Any]:
        poll = await self.store.get("polls", poll_id)
        if not poll:
            _fail("投票不存在", "NOT_FOUND")
        return poll

    async def _my_ballot(self, identity: str, poll_id: str) -> Optional[Dict[str, Any]]:
        ballots = await self.store.docs("ballots")
        for ballot in ballots:
            if ballot.get("_openid") == identity and ballot.get("pollId") == poll_id:
                return ballot
        return None

    # ── identity / home ──

    async def identity_get(self, payload, identity):
        return {"openid": identity}

    async def home_feed(self, payload, identity):
        banners = [b for b in await self.store.docs("banners") if b.get("isActive")]
        banners.sort(key=lambda b: b.get("sort") or 0)

        polls = [
            p for p in await self.store.docs("polls") if p.get("status") == "active" and _visible(p)
        ]
        now = utcnow()
        ongoing = [p for p in polls if (parse_dt(p.get("endAt")) or now) > now]
        ongoing.sort(key=lambda p: _dt_key(p.get("endAt")))
        hot = sorted(polls, key=lambda p: p.get("totalVotes") or 0, reverse=True)

        events = [
            e
            for e in await self.store.docs("events")
            if e.get("status") in ("active", "full") and _visible(e)
        ]
        events.sort(key=lambda e: _dt_key(e.get("startAt")))

        clubs = [c for c in await self.store.docs("clubs") if _visible(c)]
        clubs.sort(key=lambda c: c.get("heatScore") or 0, reverse=True)

        return {
            "banners": [
                {
                    "_id": b.get("_id"),
                    "title": b.get("title"),
                    "imageUrl": b.get("imageUrl"),
                    "targetRoute": b.get("targetRoute") or "",
                }
                for b in banners[:5]
            ],
            "todayPoll": _slim_poll_home(ongoing[0]) if ongoing else None,
            "hotPolls": [_slim_poll_home(p) for p in hot[:5]],
            "events": [_slim_event_home(e) for e in events[:3]],
            "clubs": [_slim_club_home(c) for c in clubs[:6]],
        }

    # ── vote ──

    async def vote_list(self, payload, identity):
        tag = payload.get("tag") or ""
        polls = [
            p for p in await self.store.docs("polls") if p.get("status") == "active" and _visible(p)
        ]
        if tag and tag != "all":
            polls = [p for p in polls if p.get("tag") == tag]
        polls.sort(key=lambda p: _dt_key(p.get("createdAt") or p.get("startAt")), reverse=True)
        page = _paginate([_slim_poll(p) for p in polls], payload.get("page", 0))
        return page

    async def vote_detail(self, payload, identity):
        poll_id = payload.get("pollId")
        if not poll_id:
            _fail("缺少 pollId", "PARAM_MISSING")
        poll = _slim_poll(await self._poll(poll_id))
        mine = await self._my_ballot(identity, poll_id)
        poll["myChoice"] = _ballot_option_ids(mine) if mine else []
        poll["hasVoted"] = bool(mine)
        poll["isChanged"] = bool(mine and mine.get("isChanged"))
        poll["canChange"] = bool(poll.get("allowChange")) and not bool(
            mine and mine.get("isChanged")
        )
        if poll.get("pollType") == "groupbuy":
            poll["joined"] = bool(mine)
            poll["joinedOptionId"] = mine.get("optionId") if mine else None
            max_participants = poll.get("maxParticipants")
            poll["isFull"] = bool(
                max_participants and (poll.get("participantCount") or 0) >= max_participants
            )
        return poll

    async def vote_results(self, payload, identity):
        poll_id = payload.get("pollId")
        if not poll_id:
            _fail("缺少 pollId", "PARAM_MISSING")
        raw = await self._poll(poll_id)
        total = raw.get("totalVotes") or 0
        options = [
            {
                "optionId": o.get("optionId"),
                "label": o.get("label"),
                "count": o.get("count") or 0,
                "percent": round((o.get("count") or 0) / total * 1000) / 10 if total else 0,
            }
            for o in raw.get("options") or []
        ]
        return {"pollId": poll_id, "total": total, "options": options, "groups": []}

    async def vote_cast(self, payload, identity):
        async with self._write_lock:
            return await self._cast(payload, identity)

    async def _cast(self, payload, identity):
        poll_id = payload.get("pollId")
        option_ids: List[str] = list(payload.get("optionIds") or [])
        if not poll_id:
            _fail("缺少 pollId", "PARAM_MISSING")

        raw = await self._poll(poll_id)
        if raw.get("isDeleted"):
            _fail("投票不存在", "NOT_FOUND")
        if raw.get("status") in ("draft", "archived", "withdrawn"):
            _fail("投票未开放", "POLL_CLOSED")
        now = utcnow()
        start_at = parse_dt(raw.get("startAt"))
        end_at = parse_dt(raw.get("endAt"))
        if start_at and start_at > now:
            _fail("投票尚未开始", "POLL_NOT_STARTED")
        if raw.get("status") == "closed" or (end_at and end_at < now):
            _fail("投票已结束", "POLL_CLOSED")

        low, high = OPTION_RANGE.get(raw.get("pollType"), (1, 1))
        if not (low <= len(option_ids) <= high):
            _fail(f"该题需选择 {low}~{high} 个选项", "PARAM_INVALID")
        max_choices = raw.get("maxChoices")
        if raw.get("pollType") == "multi" and max_choices and len(option_ids) > max_choices:
            _fail(f"最多可选 {max_choices} 项", "PARAM_INVALID")

        options = raw.get("options") or []
        valid_ids = {o.get("optionId") for o in options}
        if any(oid not in valid_ids for oid in option_ids):
            _fail("选项不合法", "PARAM_INVALID")

        mine = await self._my_ballot(identity, poll_id)
        if raw.get("pollType") == "groupbuy" and raw.get("maxParticipants"):
            if not mine and (raw.get("participantCount") or 0) >= raw["maxParticipants"]:
                _fail("接龙人数已满", "FULL")

        def adjust(delta: int, ids: List[str]):
            raw["totalVotes"] = (raw.get("totalVotes") or 0) + delta
            for oid in ids:
                for option in options:
                    if option.get("optionId") == oid:
                        option["count"] = (option.get("count") or 0) + delta
            if raw.get("pollType") == "groupbuy":
                raw["participantCount"] = (raw.get("participantCount") or 0) + delta

        if mine:
            if not raw.get("allowChange"):
                _fail("该投票不支持改票", "ALREADY_VOTED")
            if mine.get("isChanged"):
                _fail("你已修改过一次", "ALREADY_VOTED")
            adjust(-1, _ballot_option_ids(mine))

        adjust(1, option_ids)
        raw["options"] = options
        raw["updatedAt"] = iso(now)
        await self.store.put("polls", raw)

        record = {
            "_openid": identity,
            "pollId": poll_id,
            "optionId": option_ids[0] if len(option_ids) == 1 else None,
            "optionIds": option_ids,
            "isChanged": bool(mine),
            "updatedAt": iso(now),
        }
        if mine:
            record["_id"] = mine["_id"]
            record["createdAt"] = mine.get("createdAt") or iso(now)
        else:
            record["createdAt"] = iso(now)
        await self.store.put("ballots", record)

        new_badges = await self._evaluate_badges(identity, with_streak=True)
        return {"voted": True, "changed": bool(mine), "optionIds": option_ids, "newBadges": new_badges}

    async def vote_join_chain(self, payload, identity):
        poll_id, option_id = payload.get("pollId"), payload.get("optionId")
        if not poll_id or not option_id:
            _fail("缺少 pollId 或 optionId", "PARAM_MISSING")
        raw = await self._poll(poll_id)
        if raw.get("pollType") != "groupbuy":
            _fail("接龙不存在", "NOT_FOUND")
        async with self._write_lock:
            return await self._cast({"pollId": poll_id, "optionIds": [option_id]}, identity)

    async def vote_leave_chain(self, payload, identity):
        poll_id = payload.get("pollId")
        if not poll_id:
            _fail("缺少 pollId", "PARAM_MISSING")
        async with self._write_lock:
            mine = await self._my_ballot(identity, poll_id)
            if not mine:
                _fail("你还没有接龙", "NOT_FOUND")
            raw = await self._poll(poll_id)
            end_at = parse_dt(raw.get("endAt"))
            if end_at and end_at < utcnow():
                _fail("接龙已结束", "POLL_CLOSED")
            raw["totalVotes"] = (raw.get("totalVotes") or 0) - 1
            raw["participantCount"] = (raw.get("participantCount") or 0) - 1
            for oid in _ballot_option_ids(mine):
                for option in raw.get("options") or []:
                    if option.get("optionId") == oid:
                        option["count"] = (option.get("count") or 0) - 1
            await self.store.put("polls", raw)
            await self.store.delete("ballots", mine["_id"])
            return {"left": True}

    # ── club ──

    async def club_list(self, payload, identity):
        category = payload.get("category") or ""
        keyword = (payload.get("keyword") or "").strip().lower()
        clubs = [c for c in await self.store.docs("clubs") if _visible(c)]
        if category and category != "all":
            clubs = [c for c in clubs if c.get("category") == category]
        if keyword:
            clubs = [c for c in clubs if keyword in (c.get("name") or "").lower()]
        clubs.sort(key=lambda c: c.get("heatScore") or 0, reverse=True)
        return _paginate([_slim_club(c) for c in clubs], payload.get("page", 0))

    async def club_rank(self, payload, identity):
        clubs = [c for c in await self.store.docs("clubs") if _visible(c)]
        clubs.sort(key=lambda c: c.get("heatScore") or 0, reverse=True)
        return {"list": [_slim_club(c) for c in clubs[:10]]}

    async def club_detail(self, payload, identity):
        club_id = payload.get("clubId")
        if not club_id:
            _fail("缺少 clubId", "PARAM_MISSING")
        raw = await self.store.get("clubs", club_id)
        if not raw:
            _fail("社团不存在", "NOT_FOUND")
        club = _slim_club(raw)
        club["joined"] = identity in (raw.get("memberOpenids") or [])
        return club

    async def club_posts(self, payload, identity):
        club_id = payload.get("clubId")
        if not club_id:
            _fail("缺少 clubId", "PARAM_MISSING")
        posts = [p for p in await self.store.docs("club_posts") if p.get("clubId") == club_id]
        posts.sort(key=lambda p: _dt_key(p.get("publishedAt")), reverse=True)
        posts.sort(key=lambda p: bool(p.get("isPinned")), reverse=True)
        shaped = [
            {
                "_id": p.get("_id"),
                "clubId": p.get("clubId"),
                "title": p.get("title") or "",
                "content": p.get("content") or "",
                "images": p.get("images") or [],
                "isPinned": bool(p.get("isPinned")),
                "likeCount": p.get("likeCount") or 0,
                "publishedAt": p.get("publishedAt"),
            }
            for p in posts
        ]
        return _paginate(shaped, payload.get("page", 0))

    async def club_join(self, payload, identity):
        async with self._write_lock:
            raw = await self._club(payload)
            members = raw.get("memberOpenids") or []
            if identity in members:
                return {"joined": True, "already": True}
            raw["memberOpenids"] = members + [identity]
            raw["memberCount"] = (raw.get("memberCount") or 0) + 1
            raw["updatedAt"] = iso(utcnow())
            await self.store.put("clubs", raw)
            return {"joined": True, "already": False}

    async def club_leave(self, payload, identity):
        async with self._write_lock:
            raw = await self._club(payload)
            members = raw.get("memberOpenids") or []
            if identity not in members:
                return {"left": True, "already": True}
            raw["memberOpenids"] = [m for m in members if m != identity]
            raw["memberCount"] = (raw.get("memberCount") or 0) - 1
            raw["updatedAt"] = iso(utcnow())
            await self.store.put("clubs", raw)
            return {"left": True, "already": False}

    async def _club(self, payload) -> Dict[str, Any]:
        club_id = payload.get("clubId")
        if not club_id:
            _fail("缺少 clubId", "PARAM_MISSING")
        raw = await self.store.get("clubs", club_id)
        if not raw:
            _fail("社团不存在", "NOT_FOUND")
        return raw

    # ── event ──

    async def event_list(self, payload, identity):
        events = [
            e
            for e in await self.store.docs("events")
            if _visible(e) and e.get("status") in ("active", "full")
        ]
        events.sort(key=lambda e: _dt_key(e.get("startAt")))
        return _paginate([_slim_event(e) for e in events], payload.get("page", 0))

    async def event_calendar(self, payload, identity):
        try:
            year, month = int(payload.get("year")), int(payload.get("month"))
        except (TypeError, ValueError):
            _fail("缺少 year 或 month", "PARAM_MISSING")
        start = datetime(year, month, 1, tzinfo=timezone.utc).timestamp()
        end = datetime(
            year, month, _calendar.monthrange(year, month)[1], 23, 59, 59, tzinfo=timezone.utc
        ).timestamp()
        events = [
            e
            for e in await self.store.docs("events")
            if _visible(e) and start <= _dt_key(e.get("startAt")) <= end
        ]
        events.sort(key=lambda e: _dt_key(e.get("startAt")))
        day_map: Dict[str, int] = {}
        for event in events:
            parsed = parse_dt(event.get("startAt"))
            if not parsed:
                continue
            local = parsed.astimezone()
            key = local.strftime("%Y-%m-%d")
            day_map[key] = day_map.get(key, 0) + 1
        return {
            "days": [{"date": date, "count": count} for date, count in day_map.items()],
            "events": [_slim_event(e) for e in events],
        }

    async def event_detail(self, payload, identity):
        raw = await self._event(payload)
        event = _slim_event(raw)
        event["registered"] = identity in (raw.get("registeredOpenids") or [])
        event["waitlisted"] = identity in (raw.get("waitlistOpenids") or [])
        return event

    async def event_join(self, payload, identity):
        async with self._write_lock:
            raw = await self._event(payload)
            if raw.get("status") == "cancelled":
                _fail("活动已取消", "EVENT_CANCELLED")
            if raw.get("status") == "closed":
                _fail("报名已结束", "POLL_CLOSED")
            now = utcnow()
            deadline = parse_dt(raw.get("signupDeadline"))
            if deadline and deadline < now:
                _fail("报名已截止", "POLL_CLOSED")
            end_at = parse_dt(raw.get("endAt"))
            if end_at and end_at < now:
                _fail("活动已结束", "POLL_CLOSED")

            registered = raw.get("registeredOpenids") or []
            waitlist = raw.get("waitlistOpenids") or []
            if identity in registered:
                return {"joined": True, "waitlisted": False, "already": True}
            if identity in waitlist:
                return {"joined": False, "waitlisted": True, "already": True}

            max_participants = raw.get("maxParticipants")
            is_full = bool(
                max_participants and (raw.get("participantCount") or 0) >= max_participants
            )
            raw["updatedAt"] = iso(now)
            if is_full:
                raw["waitlistOpenids"] = waitlist + [identity]
                await self.store.put("events", raw)
                return {"joined": False, "waitlisted": True, "already": False}

            raw["registeredOpenids"] = registered + [identity]
            raw["participantCount"] = (raw.get("participantCount") or 0) + 1
            if max_participants and raw["participantCount"] >= max_participants:
                raw["status"] = "full"
            await self.store.put("events", raw)
            return {"joined": True, "waitlisted": False, "already": False}

    async def event_my_cas(self, payload, identity):
        records = [r for r in await self.store.docs("cas_records") if r.get("_openid") == identity]
        records.sort(key=lambda r: _dt_key(r.get("happenedAt")), reverse=True)
        events = [
            e
            for e in await self.store.docs("events")
            if _visible(e) and identity in (e.get("registeredOpenids") or [])
        ]
        events.sort(key=lambda e: _dt_key(e.get("startAt")), reverse=True)
        stats = {"C": 0, "A": 0, "S": 0}
        for record in records:
            if record.get("casType") in stats:
                stats[record["casType"]] += 1
        return {
            "records": records[:50],
            "stats": stats,
            "myEvents": [_slim_event(e) for e in events[:50]],
        }

    async def _event(self, payload) -> Dict[str, Any]:
        event_id = payload.get("eventId")
        if not event_id:
            _fail("缺少 eventId", "PARAM_MISSING")
        raw = await self.store.get("events", event_id)
        if not raw:
            _fail("活动不存在", "NOT_FOUND")
        return raw

    # ── living ──

    async def living_channels(self, payload, identity):
        channels = [c for c in await self.store.docs("dorm_channels") if c.get("isActive")]
        channels.sort(key=lambda c: c.get("sort") or 0)
        channels.sort(key=lambda c: c.get("scope") or "")
        return {
            "list": [
                {
                    "_id": c.get("_id"),
                    "name": c.get("name"),
                    "scope": c.get("scope"),
                    "building": c.get("building") or "",
                    "floor": c.get("floor") or "",
                    "room": c.get("room") or "",
                }
                for c in channels[:50]
            ]
        }

    async def living_channel_posts(self, payload, identity):
        channel_id = payload.get("channelId")
        if not channel_id:
            _fail("缺少 channelId", "PARAM_MISSING")
        posts = [
            p
            for p in await self.store.docs("dorm_posts")
            if p.get("channelId") == channel_id
            and _visible(p)
            and p.get("reviewStatus") == "approved"
        ]
        posts.sort(key=lambda p: _dt_key(p.get("createdAt")), reverse=True)
        shaped = [
            {
                "_id": p.get("_id"),
                "channelId": p.get("channelId"),
                "content": p.get("content") or "",
                "images": p.get("images") or [],
                "likeCount": p.get("likeCount") or 0,
                "createdAt": p.get("createdAt"),
            }
            for p in posts
        ]
        return _paginate(shaped, payload.get("page", 0))

    async def living_lost_found(self, payload, identity):
        kind = payload.get("kind") or ""
        items = [i for i in await self.store.docs("lost_found") if _visible(i)]
        if kind and kind != "all":
            items = [i for i in items if i.get("kind") == kind]
        items.sort(key=lambda i: _dt_key(i.get("createdAt")), reverse=True)
        shaped = [
            {
                "_id": i.get("_id"),
                "kind": i.get("kind"),
                "title": i.get("title"),
                "description": i.get("description") or "",
                "location": i.get("location") or "",
                "contact": i.get("contact") or "",
                "images": i.get("images") or [],
                "isResolved": bool(i.get("isResolved")),
                "createdAt": i.get("createdAt"),
            }
            for i in items
        ]
        return _paginate(shaped, payload.get("page", 0))

    async def living_second_hand(self, payload, identity):
        items = [i for i in await self.store.docs("second_hand") if _visible(i)]
        items.sort(key=lambda i: _dt_key(i.get("createdAt")), reverse=True)
        shaped = [
            {
                "_id": i.get("_id"),
                "title": i.get("title"),
                "description": i.get("description") or "",
                "price": i.get("price"),
                "images": i.get("images") or [],
                "contact": i.get("contact") or "",
                "isSold": bool(i.get("isSold")),
                "createdAt": i.get("createdAt"),
            }
            for i in items
        ]
        return _paginate(shaped, payload.get("page", 0))

    # ── scan ──

    async def _load_card(self, key: str) -> Dict[str, Any]:
        if not key:
            _fail("缺少卡片标识", "PARAM_MISSING")
        cards = await self.store.docs("nfc_cards")
        for card in cards:
            if card.get("_id") == key:
                return card
        for card in cards:
            if key in (card.get("code"), card.get("cardId"), card.get("cardUid")):
                return card
        _fail("点位不存在", "CARD_NOT_FOUND")

    async def scan_card_by_code(self, payload, identity):
        card = await self._load_card(payload.get("key"))
        if not card.get("isActive", True):
            _fail("该点位已停用", "CARD_INACTIVE")
        checkins = [
            c for c in await self.store.docs("nfc_checkins") if c.get("_openid") == identity
        ]
        mine = next((c for c in checkins if c.get("cardId") == card.get("cardId")), None)
        return {
            "cardId": card.get("cardId"),
            "locationDesc": card.get("locationDesc") or "",
            "locationType": card.get("locationType") or "",
            "targetType": card.get("targetType"),
            "targetId": card.get("targetId"),
            "checked": bool(mine),
            "tapCount": (mine or {}).get("tapCount") or 0,
            "uniqueCards": len(checkins),
            "rules": LOCATION_RULES,
        }

    async def scan_checkin(self, payload, identity):
        async with self._write_lock:
            card = await self._load_card(payload.get("key"))
            if not card.get("isActive", True):
                _fail("该点位已停用", "CARD_INACTIVE")
            now = iso(utcnow())
            checkins = [
                c for c in await self.store.docs("nfc_checkins") if c.get("_openid") == identity
            ]
            mine = next((c for c in checkins if c.get("cardId") == card.get("cardId")), None)
            if mine:
                mine["tapCount"] = (mine.get("tapCount") or 0) + 1
                mine["lastTapAt"] = now
                await self.store.put("nfc_checkins", mine)
            else:
                await self.store.insert(
                    "nfc_checkins",
                    {
                        "_openid": identity,
                        "cardId": card.get("cardId"),
                        "firstTapAt": now,
                        "lastTapAt": now,
                        "tapCount": 1,
                    },
                )
            newly, unique_cards = await self._evaluate_badges(identity, with_streak=False)
            return {
                "checked": True,
                "firstTime": not mine,
                "cardId": card.get("cardId"),
                "uniqueCards": unique_cards,
                "newBadges": newly,
                "target": {"type": card.get("targetType"), "id": card.get("targetId")},
            }

    # ── me / 勋章 ──

    async def _evaluate_badges(self, identity: str, with_streak: bool):
        ballots = [b for b in await self.store.docs("ballots") if b.get("_openid") == identity]
        checkins = [
            c for c in await self.store.docs("nfc_checkins") if c.get("_openid") == identity
        ]
        clubs = [
            c
            for c in await self.store.docs("clubs")
            if _visible(c) and identity in (c.get("memberOpenids") or [])
        ]
        events = [
            e
            for e in await self.store.docs("events")
            if _visible(e) and identity in (e.get("registeredOpenids") or [])
        ]
        counters = {
            "vote_count": len(ballots),
            "nfc_unique": len(checkins),
            "club_count": len(clubs),
            "event_count": len(events),
            "vote_streak": _vote_streak(ballots) if with_streak else 0,
        }

        owned = {
            b.get("badgeCode")
            for b in await self.store.docs("user_badges")
            if b.get("_openid") == identity
        }
        newly = []
        for badge in await self.store.docs("badges"):
            rule = badge.get("rule") or {}
            code = badge.get("code")
            if code in owned:
                continue
            if counters.get(rule.get("type"), 0) < (rule.get("count") or 0):
                continue
            await self.store.insert(
                "user_badges",
                {"_openid": identity, "badgeCode": code, "earnedAt": iso(utcnow())},
            )
            owned.add(code)
            newly.append(
                {
                    "code": code,
                    "name": badge.get("name"),
                    "rarity": badge.get("rarity"),
                    "iconUrl": badge.get("iconUrl") or "",
                }
            )
        return (newly, counters["nfc_unique"]) if not with_streak else newly

    async def me_overview(self, payload, identity):
        ballots = [b for b in await self.store.docs("ballots") if b.get("_openid") == identity]
        ballots.sort(key=lambda b: _dt_key(b.get("createdAt")), reverse=True)
        checkins = [
            c for c in await self.store.docs("nfc_checkins") if c.get("_openid") == identity
        ]
        checkins.sort(key=lambda c: _dt_key(c.get("lastTapAt") or c.get("firstTapAt")), reverse=True)
        owned_badges = [
            b for b in await self.store.docs("user_badges") if b.get("_openid") == identity
        ]
        owned_badges.sort(key=lambda b: _dt_key(b.get("earnedAt")), reverse=True)
        owned_map = {b.get("badgeCode"): b.get("earnedAt") for b in owned_badges}

        polls = {p.get("_id"): p for p in await self.store.docs("polls")}
        badges = [
            {
                "code": b.get("code"),
                "name": b.get("name"),
                "description": b.get("description") or "",
                "iconUrl": b.get("iconUrl") or "",
                "icon": b.get("icon") or "",
                "rarity": b.get("rarity"),
                "rule": b.get("rule") or {},
                "earnedAt": owned_map.get(b.get("code")),
                "unlocked": b.get("code") in owned_map,
            }
            for b in await self.store.docs("badges")
        ]
        recent_votes = [
            {
                "pollId": b.get("pollId"),
                "title": (polls.get(b.get("pollId")) or {}).get("title") or "（已下架投票）",
                "optionIds": _ballot_option_ids(b),
                "createdAt": b.get("createdAt"),
            }
            for b in ballots[:20]
        ]
        recent_checkins = [
            {
                "cardId": c.get("cardId"),
                "tapCount": c.get("tapCount") or 1,
                "firstTapAt": c.get("firstTapAt"),
                "lastTapAt": c.get("lastTapAt") or c.get("firstTapAt"),
            }
            for c in checkins[:10]
        ]
        return {
            "stats": {
                "voteCount": len(ballots),
                "checkinCount": len(checkins),
                "badgeCount": len(owned_badges),
                "badgeTotal": len(badges),
            },
            "badges": badges,
            "recentVotes": recent_votes,
            "recentCheckins": recent_checkins,
        }


# ── 视图裁剪（对齐云函数 slim*）──


def _slim_poll(poll: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "_id": poll.get("_id"),
        "title": poll.get("title"),
        "description": poll.get("description") or "",
        "pollType": poll.get("pollType"),
        "status": poll.get("status"),
        "tag": poll.get("tag"),
        "category": poll.get("category"),
        "topicTags": poll.get("topicTags") or [],
        "coverUrl": poll.get("coverUrl") or "",
        "startAt": poll.get("startAt"),
        "endAt": poll.get("endAt"),
        "allowChange": bool(poll.get("allowChange")),
        "maxChoices": poll.get("maxChoices"),
        "maxParticipants": poll.get("maxParticipants"),
        "totalVotes": poll.get("totalVotes") or 0,
        "participantCount": poll.get("participantCount") or 0,
        "options": [
            {
                "optionId": o.get("optionId"),
                "label": o.get("label"),
                "sortOrder": o.get("sortOrder") or 0,
                "count": o.get("count") or 0,
            }
            for o in poll.get("options") or []
        ],
    }


def _slim_poll_home(poll: Dict[str, Any]) -> Dict[str, Any]:
    slim = _slim_poll(poll)
    slim["options"] = [
        {"optionId": o["optionId"], "label": o["label"]} for o in slim["options"]
    ]
    return {
        key: slim[key]
        for key in (
            "_id",
            "title",
            "description",
            "pollType",
            "tag",
            "category",
            "coverUrl",
            "endAt",
            "totalVotes",
            "participantCount",
            "maxParticipants",
            "options",
        )
    }


def _slim_club(club: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "_id": club.get("_id"),
        "name": club.get("name"),
        "description": club.get("description") or "",
        "logoUrl": club.get("logoUrl") or "",
        "coverUrl": club.get("coverUrl") or "",
        "category": club.get("category"),
        "isVerified": bool(club.get("isVerified")),
        "memberCount": club.get("memberCount") or 0,
        "followerCount": club.get("followerCount") or 0,
        "heatScore": club.get("heatScore") or 0,
    }


def _slim_club_home(club: Dict[str, Any]) -> Dict[str, Any]:
    slim = _slim_club(club)
    return {key: value for key, value in slim.items() if key != "followerCount"}


def _slim_event(event: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "_id": event.get("_id"),
        "title": event.get("title"),
        "description": event.get("description") or "",
        "coverUrl": event.get("coverUrl") or "",
        "location": event.get("location") or "",
        "organizerType": event.get("organizerType"),
        "organizerId": event.get("organizerId"),
        "startAt": event.get("startAt"),
        "endAt": event.get("endAt"),
        "signupDeadline": event.get("signupDeadline"),
        "maxParticipants": event.get("maxParticipants"),
        "status": event.get("status"),
        "casType": event.get("casType"),
        "participantCount": event.get("participantCount") or 0,
    }


def _slim_event_home(event: Dict[str, Any]) -> Dict[str, Any]:
    slim = _slim_event(event)
    return {
        key: slim[key]
        for key in (
            "_id",
            "title",
            "location",
            "coverUrl",
            "startAt",
            "endAt",
            "organizerType",
            "status",
            "participantCount",
            "maxParticipants",
        )
    }


def _ballot_option_ids(ballot: Optional[Dict[str, Any]]) -> List[str]:
    if not ballot:
        return []
    if ballot.get("optionIds"):
        return list(ballot["optionIds"])
    return [ballot["optionId"]] if ballot.get("optionId") else []


def _vote_streak(ballots: List[Dict[str, Any]]) -> int:
    days = set()
    for ballot in ballots:
        parsed = parse_dt(ballot.get("createdAt"))
        if parsed:
            local = parsed.astimezone()
            days.add((local.year, local.month, local.day))
    streak = 0
    cursor = utcnow().astimezone()
    for _ in range(400):
        if (cursor.year, cursor.month, cursor.day) not in days:
            break
        streak += 1
        cursor = cursor - timedelta(days=1)
    return streak


_ACTIONS = {
    ("identity", "get"): LocalRepository.identity_get,
    ("home", "feed"): LocalRepository.home_feed,
    ("vote", "list"): LocalRepository.vote_list,
    ("vote", "detail"): LocalRepository.vote_detail,
    ("vote", "results"): LocalRepository.vote_results,
    ("vote", "cast"): LocalRepository.vote_cast,
    ("vote", "joinChain"): LocalRepository.vote_join_chain,
    ("vote", "leaveChain"): LocalRepository.vote_leave_chain,
    ("club", "list"): LocalRepository.club_list,
    ("club", "rank"): LocalRepository.club_rank,
    ("club", "detail"): LocalRepository.club_detail,
    ("club", "posts"): LocalRepository.club_posts,
    ("club", "join"): LocalRepository.club_join,
    ("club", "leave"): LocalRepository.club_leave,
    ("event", "list"): LocalRepository.event_list,
    ("event", "calendar"): LocalRepository.event_calendar,
    ("event", "detail"): LocalRepository.event_detail,
    ("event", "join"): LocalRepository.event_join,
    ("event", "myCas"): LocalRepository.event_my_cas,
    ("living", "channels"): LocalRepository.living_channels,
    ("living", "channelPosts"): LocalRepository.living_channel_posts,
    ("living", "lostFound"): LocalRepository.living_lost_found,
    ("living", "secondHand"): LocalRepository.living_second_hand,
    ("scan", "cardByCode"): LocalRepository.scan_card_by_code,
    ("scan", "checkin"): LocalRepository.scan_checkin,
    ("me", "overview"): LocalRepository.me_overview,
}


__all__ = ["LocalRepository", "LOCATION_RULES"]
