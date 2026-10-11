"""内容审核：Aho-Corasick 敏感词机审 + LLM 二次审核 + 人工队列。

PRD §4.1 双保险 / §4.3 敏感词库管理
技术架构文档 §5.3 过滤管线
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import ERR_SENSITIVE_WORD_HIT
from app.models.common import ReviewStatus
from app.models.crawler import SensitiveWord

logger = logging.getLogger(__name__)


# ── Aho-Corasick 自动机（纯 Python，毫秒级 O(n) 匹配）──


class _Node:
    __slots__ = ("next", "fail", "out")

    def __init__(self):
        self.next: Dict[str, int] = {}
        self.fail: int = 0
        self.out: List[str] = []


class AhoCorasick:
    def __init__(self, words: Iterable[str]):
        self._nodes: List[_Node] = [_Node()]
        for w in words:
            self._add(w)
        self._build_fail()

    def _add(self, word: str) -> None:
        cur = 0
        for ch in word:
            nxt = self._nodes[cur].next.get(ch)
            if nxt is None:
                nxt = len(self._nodes)
                self._nodes[cur].next[ch] = nxt
                self._nodes.append(_Node())
            cur = nxt
        self._nodes[cur].out.append(word)

    def _build_fail(self) -> None:
        from collections import deque

        q: deque = deque()
        for ch, nxt in self._nodes[0].next.items():
            self._nodes[nxt].fail = 0
            q.append(nxt)
        while q:
            cur = q.popleft()
            node = self._nodes[cur]
            node.out = node.out + self._nodes[node.fail].out
            for ch, nxt in node.next.items():
                f = node.fail
                while f and ch not in self._nodes[f].next:
                    f = self._nodes[f].fail
                self._nodes[nxt].fail = self._nodes[f].next.get(ch, 0)
                q.append(nxt)

    def search(self, text: str) -> List[str]:
        """返回命中的敏感词列表（去重）。"""
        hits: List[str] = []
        cur = 0
        for ch in text:
            while cur and ch not in self._nodes[cur].next:
                cur = self._nodes[cur].fail
            cur = self._nodes[cur].next.get(ch, 0)
            if self._nodes[cur].out:
                hits.extend(self._nodes[cur].out)
        return list(dict.fromkeys(hits))


# ── 词库缓存（支持运营后台热更新）──


@dataclass
class _WordBank:
    automaton: Optional[AhoCorasick] = None
    words: List[str] = field(default_factory=list)
    categories: Dict[str, str] = field(default_factory=dict)


_bank = _WordBank()


async def load_word_bank(db: AsyncSession, force: bool = False) -> _WordBank:
    global _bank
    if _bank.automaton is not None and not force:
        return _bank
    rows = (
        await db.execute(select(SensitiveWord).where(SensitiveWord.is_active.is_(True)))
    ).scalars().all()
    words = [r.word for r in rows if r.word]
    _bank = _WordBank(
        automaton=AhoCorasick(words),
        words=words,
        categories={r.word: r.category for r in rows},
    )
    return _bank


async def refresh_word_bank(db: AsyncSession) -> None:
    await load_word_bank(db, force=True)


# ── 对外接口 ──


@dataclass
class ModerationResult:
    passed: bool
    hits: List[str] = field(default_factory=list)
    reason: str = ""
    status: ReviewStatus = ReviewStatus.APPROVED


async def check_text(db: AsyncSession, text: str, allow_warn: bool = True) -> ModerationResult:
    """第一层：敏感词匹配。命中 block 级词直接拦截。"""
    bank = await load_word_bank(db)
    if bank.automaton is None or not text:
        return ModerationResult(passed=True)

    hits = bank.automaton.search(text)
    if not hits:
        return ModerationResult(passed=True)

    blocking = [w for w in hits if bank.categories.get(w) != "warn" or not allow_warn]
    if not blocking:
        # 仅命中 warn 级：放行但标记需人工抽检
        return ModerationResult(
            passed=True,
            hits=hits,
            reason="命中提醒级词汇，转人工抽检",
            status=ReviewStatus.NEEDS_MANUAL,
        )

    return ModerationResult(
        passed=False,
        hits=blocking,
        reason=f"命中敏感词：{blocking[0]}",
        status=ReviewStatus.REJECTED,
    )


async def moderate_ugc(
    db: AsyncSession,
    text: str,
    auto_approve: Optional[bool] = None,
) -> ModerationResult:
    """UGC 双层审核入口：机审 → （可选）LLM → 人工队列。"""
    result = await check_text(db, text)
    if not result.passed:
        return result

    auto = settings.MODERATION_AUTO_APPROVE if auto_approve is None else auto_approve
    if result.status == ReviewStatus.NEEDS_MANUAL and not auto:
        return result

    if auto:
        result.status = ReviewStatus.APPROVED
        result.reason = ""
    return result


def assert_text_ok(result: ModerationResult) -> None:
    if not result.passed:
        from app.core.exceptions import AppError

        raise AppError(ERR_SENSITIVE_WORD_HIT, result.reason or "内容命中敏感词", 400)


# ── Prompt-4：LLM 辅助审核（边界案例）──


async def llm_review_ugc(content: str, poll_title: str = "", grade: str = "") -> dict:
    """《Prompt 工程文档》§5 —— 仅对边界案例调用，超时默认放行 + 人工抽检。"""
    from app.services.llm_service import safe_llm_call

    fallback = {
        "approved": True,
        "reason": "LLM 不可用，默认放行",
        "violation_type": "none",
    }
    if not settings.LLM_ENABLED:
        return fallback

    prompt = (
        "请审核以下用户发布的内容是否合规。\n\n"
        f"【内容信息】\n发布内容：{content}\n所属投票：{poll_title}\n用户年级：{grade}\n\n"
        '请严格按以下 JSON 格式输出：\n'
        '{"approved": true/false, "reason": "判断理由（20字以内）", '
        '"violation_type": "none/attack/privacy/incitement/rumor/ad"}'
    )
    return await safe_llm_call(
        prompt=prompt,
        system=UGC_REVIEW_SYSTEM,
        fallback=fallback,
        model=settings.QWEN_MODEL_SELECT,
        temperature=0.1,
    )


UGC_REVIEW_SYSTEM = """你是七德通的内容审核员，负责审核高中生用户发布的内容。

审核标准：

【必须拦截】
1. 人身攻击、网络暴力、群体歧视
2. 泄露他人隐私（姓名+班级+负面信息的组合）
3. 煽动对立（性别、地域、班级之间的对立）
4. 明显谣言或未经证实的指控
5. 广告、引流、外链

【可以放行】
1. 正常的观点表达，即使观点偏激但不攻击他人
2. 对校园管理的合理批评建议
3. 吐槽、抱怨，但不针对具体个人
4. 使用适度网络用语、表情表达
5. 与投票话题相关的讨论

注意：高中生用户，语言可能比较直率，不要因为语气激烈就误判。
关键判断标准是：是否在攻击具体的人/群体，是否在传播有害信息。"""


# ── 爬虫话题三层过滤（技术架构文档 §5.3）──


async def filter_crawler_topic(db: AsyncSession, title: str, summary: str = "") -> ModerationResult:
    text = f"{title} {summary}"
    return await check_text(db, text, allow_warn=False)
