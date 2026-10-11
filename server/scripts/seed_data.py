"""演示数据种子脚本（技术架构文档 §3.1 scripts/seed_data.py）。

用法：
    python scripts/seed_data.py            # 灌入演示数据
    python scripts/seed_data.py --reset    # 先清空再灌入
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import delete, select  # noqa: E402

from app.core.database import SessionLocal, engine, init_db  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.models.badge import Badge  # noqa: E402
from app.models.club import Club, ClubMember, Post  # noqa: E402
from app.models.common import (  # noqa: E402
    ClubCategory,
    CrawlerItemStatus,
    CrawlerSource,
    DormChannelScope,
    EventStatus,
    NfcLocationType,
    NfcTargetType,
    OrganizerType,
    PollCategory,
    PollSource,
    PollStatus,
    PollTag,
    PollType,
    ReviewStatus,
    UserRole,
)
from app.models.crawler import DEFAULT_SENSITIVE_WORDS, CrawlerItem, SensitiveWord  # noqa: E402
from app.models.event import Event  # noqa: E402
from app.models.living import DormChannel, DormPost, LostFound  # noqa: E402
from app.models.nfc import NfcCard  # noqa: E402
from app.models.user import User  # noqa: E402
from app.models.vote import Ballot, Poll, PollOption  # noqa: E402
from app.services import badge_service  # noqa: E402

NOW = datetime.now(timezone.utc)


def h(hours: int = 0) -> datetime:
    return NOW + timedelta(hours=hours)


async def reset(db) -> None:
    from app.models.common import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await init_db()
    print("✓ 已重建数据表")


async def seed_users(db) -> dict:
    users = {}
    specs = [
        ("20240001", "alice@qd.baoan.edu.cn", "林小满", "11", "A305", UserRole.ADMIN),
        ("20240002", "bob@qd.baoan.edu.cn", "陈嘉树", "11", "A305", UserRole.OPERATOR),
        ("20240003", "carol@qd.baoan.edu.cn", "周予安", "10", "B212", UserRole.STUDENT),
        ("20240004", "dave@qd.baoan.edu.cn", "吴知遥", "12", "C108", UserRole.CLUB_ADMIN),
        ("20240005", "erin@qd.baoan.edu.cn", "苏晓棠", "10", "B212", UserRole.STUDENT),
    ]
    for sid, email, nick, grade, dorm, role in specs:
        u = (
            await db.execute(select(User).where(User.student_id == sid))
        ).scalars().first()
        if u is None:
            u = User(
                student_id=sid,
                email=email,
                password_hash=hash_password("goqd1234"),
                nickname=nick,
                grade=grade,
                dormitory=dorm,
                dorm_floor=dorm[1] if len(dorm) > 1 else None,
                role=role,
                is_verified=True,
                is_active=True,
                created_at=NOW,
                updated_at=NOW,
            )
            db.add(u)
            await db.flush()
        users[nick] = u

    # 补充一批学生账号，用于模拟真实投票分布
    for i in range(6, 61):
        sid = f"2024{i:04d}"
        u = (await db.execute(select(User).where(User.student_id == sid))).scalars().first()
        if u is None:
            u = User(
                student_id=sid,
                email=f"stu{i}@qd.baoan.edu.cn",
                password_hash=hash_password("goqd1234"),
                nickname=f"同学{i}",
                grade=str(10 + (i % 3)),
                dormitory=f"{'ABC'[i % 3]}{100 + i}",
                dorm_floor=str(1 + (i % 3)),
                role=UserRole.STUDENT,
                is_verified=True,
                is_active=True,
                created_at=NOW,
                updated_at=NOW,
            )
            db.add(u)
            await db.flush()
        users[f"同学{i}"] = u

    print(f"✓ 用户 {len(users)} 个（统一密码 goqd1234）")
    return users


async def seed_polls(db, users) -> None:
    specs = [
        {
            "title": "学校该不该禁止手机进教室？",
            "desc": "多地中学推行「手机不入教室」，支持者认为能提升专注度，反对者担心影响紧急联络。",
            "type": PollType.PK,
            "category": PollCategory.CAMPUS,
            "tag": PollTag.CAMPUS,
            "options": ["支持，专注度更重要", "反对，联络自由不该被剥夺"],
            "votes": [42, 35],
        },
        {
            "title": "如果你们学校放春秋假，你支持吗？",
            "desc": "教育部鼓励各地探索春秋假制度，已有城市试点。假如你的学校也在考虑，你怎么选？",
            "type": PollType.PK,
            "category": PollCategory.CAMPUS,
            "tag": PollTag.NEWS,
            "options": ["支持，早该放了", "反对，打乱节奏"],
            "votes": [88, 21],
        },
        {
            "title": "周末你最想参加的校园活动是？",
            "desc": "社团联合提案，用于安排本学期的周末场地与预算。",
            "type": PollType.SINGLE,
            "category": PollCategory.LIFESTYLE,
            "tag": PollTag.CAMPUS,
            "options": ["羽毛球局", "电影放映", "辩论公开赛", "手作市集"],
            "votes": [31, 27, 18, 24],
        },
        {
            "title": "食堂你最希望新增哪种窗口？（可多选）",
            "desc": "后勤处征集意见，最多选 2 项。",
            "type": PollType.MULTI,
            "category": PollCategory.CAMPUS,
            "tag": PollTag.CAMPUS,
            "options": ["轻食沙拉", "川湘小炒", "日式咖喱", "广式糖水"],
            "votes": [40, 52, 33, 29],
            "max_choices": 2,
        },
        {
            "title": "给下面这些社团活动按期待值排序",
            "desc": "排序题演示：拖动选项排出你的优先级。",
            "type": PollType.RANKING,
            "category": PollCategory.CULTURE,
            "tag": PollTag.MEME,
            "options": ["校园歌手大赛", "机器人公开日", "慈善义卖", "摄影展"],
            "votes": [30, 25, 20, 15],
        },
        {
            "title": "周六下午三点，羽毛球场，缺 2 人",
            "desc": "活动接龙：满 4 人自动关闭，人齐了就去。",
            "type": PollType.GROUP_BUY,
            "category": PollCategory.LIFESTYLE,
            "tag": PollTag.GROUP,
            "options": ["我要参加"],
            "votes": [2],
            "max_participants": 4,
        },
    ]

    students = sorted(
        [u for u in users.values() if u.role == UserRole.STUDENT], key=lambda x: x.id
    )
    for i, s in enumerate(specs):
        poll = Poll(
            title=s["title"],
            description=s["desc"],
            poll_type=s["type"],
            source_type=PollSource.MANUAL if i % 2 else PollSource.CRAWLER,
            status=PollStatus.ACTIVE if i < 5 else PollStatus.ACTIVE,
            category=s["category"],
            tag=s["tag"],
            topic_tags="#校园生活",
            start_at=h(-20 + i),
            end_at=h(24 - i * 2),
            allow_change=True,
            max_choices=s.get("max_choices"),
            max_participants=s.get("max_participants"),
            created_by=users["陈嘉树"].id,
            review_status=ReviewStatus.APPROVED,
            created_at=h(-20 + i),
            updated_at=h(-20 + i),
        )
        db.add(poll)
        await db.flush()

        opts = []
        for idx, label in enumerate(s["options"]):
            o = PollOption(poll_id=poll.id, label=label, sort_order=idx)
            db.add(o)
            opts.append(o)
        await db.flush()

        # 模拟投票记录：同一用户同一投票只投一次（ballots 唯一约束）
        used: set = set()
        for oi, o in enumerate(opts):
            need = s["votes"][oi]
            placed = 0
            for u in students:
                if placed >= need:
                    break
                if u.id in used:
                    continue
                db.add(
                    Ballot(
                        poll_id=poll.id,
                        user_id=u.id,
                        option_id=o.id,
                        created_at=h(-19 + i),
                        updated_at=h(-19 + i),
                    )
                )
                used.add(u.id)
                placed += 1
        await db.flush()
    print(f"✓ 投票 {len(specs)} 道（含单选/PK/多选/排序/接龙）")


async def seed_clubs(db, users) -> None:
    specs = [
        ("七德辩论社", "每周三下午，用逻辑和表达拆解世界。", ClubCategory.ACADEMIC, 68),
        ("星野摄影社", "记录校园光影，每学期一本影集。", ClubCategory.ART, 55),
        ("晨曦公益社", "社区服务、义卖、支教，做点实在的事。", ClubCategory.CHARITY, 47),
        ("破晓机器人社", "从机械臂到自动驾驶小车，动手造。", ClubCategory.ACADEMIC, 39),
        ("羽毛球爱好者联盟", "每周六固定场地，欢迎各水平。", ClubCategory.SPORTS, 31),
    ]
    clubs = []
    for name, desc, cat, heat in specs:
        c = (
            await db.execute(select(Club).where(Club.name == name))
        ).scalars().first()
        if c is None:
            c = Club(
                name=name,
                description=desc,
                category=cat,
                is_verified=True,
                review_status=ReviewStatus.APPROVED,
                owner_id=users["吴知遥"].id,
                member_count=heat // 5,
                heat_score=heat,
                created_at=NOW,
                updated_at=NOW,
            )
            db.add(c)
            await db.flush()
            db.add(
                ClubMember(
                    club_id=c.id, user_id=users["吴知遥"].id, role="admin", joined_at=NOW
                )
            )
        clubs.append(c)
    await db.flush()

    posts = [
        (clubs[0].id, "春季招新启动", "本周五中午在食堂门口设摊，带一个问题来，我们现场辩一场。"),
        (clubs[1].id, "校园光影征集", "本月主题「窗」，投稿截止 30 号，优秀作品进期末影集。"),
        (clubs[2].id, "周末社区义卖", "所得全部捐给对口小学，欢迎捐出闲置物品。"),
        (clubs[3].id, "机器人公开日", "周六下午实验室开放，来试试操作机械臂。"),
    ]
    for cid, title, content in posts:
        p = (
            await db.execute(select(Post).where(Post.club_id == cid, Post.title == title))
        ).scalars().first()
        if p is None:
            db.add(
                Post(
                    club_id=cid,
                    author_id=users["吴知遥"].id,
                    title=title,
                    content=content,
                    status=ReviewStatus.APPROVED,
                    like_count=12,
                    created_at=NOW,
                )
            )
    await db.flush()
    print(f"✓ 社团 {len(clubs)} 个 + 内容 {len(posts)} 条")


async def seed_events(db, users) -> None:
    specs = [
        ("春季校园歌手大赛", "大礼堂", OrganizerType.CLUB, 1, 3, 200),
        ("机器人公开日", "实验楼 301", OrganizerType.CLUB, 4, 2, 40),
        ("社区义卖", "校门口广场", OrganizerType.CLUB, 3, 5, 60),
        ("期中诚信考试动员", "各班教室", OrganizerType.SCHOOL, 0, 6, 0),
    ]
    for title, loc, otype, oid, offset, cap in specs:
        e = (
            await db.execute(select(Event).where(Event.title == title))
        ).scalars().first()
        if e is None:
            db.add(
                Event(
                    title=title,
                    description=f"{title} · 演示数据",
                    location=loc,
                    organizer_type=otype,
                    organizer_id=oid or None,
                    start_at=h(offset * 24),
                    end_at=h(offset * 24 + 2),
                    max_participants=cap or None,
                    status=EventStatus.ACTIVE,
                    review_status=ReviewStatus.APPROVED,
                    participant_count=0,
                    created_by=users["陈嘉树"].id,
                    created_at=NOW,
                    updated_at=NOW,
                )
            )
    await db.flush()
    print(f"✓ 活动 {len(specs)} 场")


async def seed_living(db, users) -> None:
    for name, scope, building, floor, room in [
        ("全校住宿生广场", DormChannelScope.ALL, None, None, None),
        ("B 座 2 层", DormChannelScope.FLOOR, "B", "2", None),
        ("A305 宿舍", DormChannelScope.ROOM, "A", "3", "A305"),
    ]:
        c = (
            await db.execute(select(DormChannel).where(DormChannel.name == name))
        ).scalars().first()
        if c is None:
            db.add(
                DormChannel(
                    name=name, scope=scope, building=building, floor=floor, room=room, is_active=True,
                    created_at=NOW, updated_at=NOW,
                )
            )
    await db.flush()

    ch = (await db.execute(select(DormChannel).where(DormChannel.name == "全校住宿生广场"))).scalars().first()
    if ch:
        db.add(
            DormPost(
                channel_id=ch.id,
                author_id=users["苏晓棠"].id,
                content="今晚热水供应到几点？有人知道吗",
                review_status=ReviewStatus.APPROVED,
                created_at=NOW,
            )
        )
        db.add(
            LostFound(
                kind="lost",
                title="丢失一副黑色无线耳机",
                description="可能落在图书馆二楼靠窗位置，有捡到的请联系。",
                location="图书馆二楼",
                contact="微信同号",
                user_id=users["周予安"].id,
                created_at=NOW,
                updated_at=NOW,
            )
        )
    await db.flush()
    print("✓ 住宿频道 3 个 + 帖子/失物各 1 条")


async def seed_nfc(db) -> None:
    """OMEGA §4.2 编码规则：{学校}-{区域}-{位置}-{序号}"""
    specs = [
        ("QD-CT-01-A01", "食堂一楼A区入口柱面", NfcLocationType.CT, NfcTargetType.VOTE, 1, "S1"),
        ("QD-LB-02-B03", "图书馆二楼借阅台前", NfcLocationType.LB, NfcTargetType.CLUB, 2, "S1"),
        ("QD-DM-01-C02", "宿舍楼一楼大厅公告栏", NfcLocationType.DM, NfcTargetType.EVENT, 1, "S1"),
        ("QD-BB-00-001", "中心公告栏", NfcLocationType.BB, NfcTargetType.DOWNLOAD, None, "S1"),
        ("QD-CL-03-A07", "社团活动室 303 门口", NfcLocationType.CL, NfcTargetType.CLUB, 1, "S1"),
    ]
    for cid, loc, ltype, ttype, tid, batch in specs:
        c = (
            await db.execute(select(NfcCard).where(NfcCard.card_id == cid))
        ).scalars().first()
        if c is None:
            db.add(
                NfcCard(
                    card_id=cid,
                    location_desc=loc,
                    location_type=ltype,
                    target_type=ttype,
                    target_id=tid,
                    is_active=True,
                    poster_batch=batch,
                    deployed_at=NOW,
                    created_at=NOW,
                    updated_at=NOW,
                )
            )
    await db.flush()
    print(f"✓ NFC 卡片 {len(specs)} 张")


async def seed_crawler(db) -> None:
    topics = [
        (CrawlerSource.WEIBO, "多地推行中小学春秋假", 9800000),
        (CrawlerSource.ZHIHU, "AI 写作业被多所学校禁止", 7600000),
        (CrawlerSource.BILIBILI, "高中生自制简易卫星地面站", 5400000),
        (CrawlerSource.BAIDU, "青少年日均屏幕时长调查报告", 4300000),
        (CrawlerSource.CCTV, "教育部鼓励学生参与社会实践", 3200000),
        (CrawlerSource.WEIBO, "校园食堂菜品评分系统上线", 2100000),
    ]
    for src, title, heat in topics:
        exists = (
            await db.execute(select(CrawlerItem).where(CrawlerItem.title == title))
        ).scalars().first()
        if exists:
            continue
        db.add(
            CrawlerItem(
                source=src,
                title=title,
                url="",
                summary=f"{title} —— 演示候选话题",
                heat_score=heat,
                status=CrawlerItemStatus.PENDING,
                risk_level="none",
                llm_suggestion="偏校园生活角度",
                crawled_at=NOW,
            )
        )
    await db.flush()

    for word, cat, sev in DEFAULT_SENSITIVE_WORDS:
        exists = (
            await db.execute(select(SensitiveWord).where(SensitiveWord.word == word))
        ).scalars().first()
        if exists:
            continue
        db.add(
            SensitiveWord(
                word=word, category=cat, severity=sev, is_active=True, created_at=NOW
            )
        )
    await db.flush()
    print(f"✓ 候选话题 {len(topics)} 条 + 敏感词 {len(DEFAULT_SENSITIVE_WORDS)} 个")


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reset", action="store_true", help="先清空数据库再灌入")
    args = ap.parse_args()

    await init_db()
    async with SessionLocal() as db:
        if args.reset:
            await reset(db)
            await init_db()

        await badge_service.seed_badges(db)
        await db.flush()
        print("✓ 勋章定义已写入")

        users = await seed_users(db)
        await seed_polls(db, users)
        await seed_clubs(db, users)
        await seed_events(db, users)
        await seed_living(db, users)
        await seed_nfc(db)
        await seed_crawler(db)
        await db.commit()

    print("\n全部完成。启动服务：uvicorn app.main:app --reload --port 8000")
    print("运营后台：http://localhost:8000/admin/web")
    print("测试账号：20240001 / goqd1234（管理员）")


if __name__ == "__main__":
    asyncio.run(main())
