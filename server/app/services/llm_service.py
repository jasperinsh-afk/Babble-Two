"""通义千问 LLM 客户端封装。

《Prompt 工程文档》通用约定：
 - 模型 qwen-max（筛选/审核）/ qwen-plus（生成/分类）
 - 温度：筛选 0.1，生成 0.7
 - 输出统一 JSON
 - 超时 ≤10s
 - 降级：失败时转人工队列而非丢弃
 - 日志：prompt + response + 耗时 + token
 - 缓存：相同话题 24h 内不重复调用
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from typing import Any, Dict, Optional

from app.config import settings
from app.core.redis import cache, cache_get_json, cache_set_json

logger = logging.getLogger(__name__)

_JSON_BLOCK = re.compile(r"\{.*\}|\[.*\]", re.DOTALL)


def _cache_key(prompt: str, model: str) -> str:
    digest = hashlib.sha256(f"{model}:{prompt}".encode("utf-8")).hexdigest()
    return f"llm:{digest}"


async def call_llm(
    prompt: str,
    system: str = "",
    model: Optional[str] = None,
    temperature: float = 0.1,
    timeout: Optional[int] = None,
) -> str:
    """返回模型原始文本。未启用 LLM 时抛 RuntimeError 由调用方降级。"""
    if not settings.LLM_ENABLED or not settings.DASHSCOPE_API_KEY:
        raise RuntimeError("LLM 未启用")

    model = model or settings.QWEN_MODEL_SELECT
    timeout = timeout or settings.LLM_TIMEOUT

    try:
        import dashscope  # type: ignore
        from dashscope import Generation  # type: ignore

        dashscope.api_key = settings.DASHSCOPE_API_KEY
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        started = time.time()
        resp = Generation.call(
            model=model,
            messages=messages,
            temperature=temperature,
            timeout=timeout,
            result_format="message",
        )
        cost = time.time() - started

        text = ""
        if getattr(resp, "status_code", None) == 200:
            text = resp.output.choices[0].message.content  # type: ignore
        else:
            raise RuntimeError(f"LLM 调用失败: {getattr(resp, 'message', 'unknown')}")

        usage = getattr(resp, "usage", None)
        logger.info(
            "llm_call model=%s cost=%.2fs tokens=%s",
            model,
            cost,
            getattr(usage, "total_tokens", None) if usage else None,
        )
        return text
    except Exception as exc:  # noqa: BLE001
        logger.warning("LLM 调用异常，降级处理: %s", exc)
        raise


async def safe_llm_call(
    prompt: str,
    system: str = "",
    fallback: Optional[Dict[str, Any]] = None,
    model: Optional[str] = None,
    temperature: float = 0.1,
    use_cache: bool = True,
) -> Dict[str, Any]:
    """安全调用：解析失败/超时一律返回 fallback（Prompt 文档 §7.1）。"""
    fallback = fallback or {}
    model = model or settings.QWEN_MODEL_SELECT

    key = _cache_key(prompt + system, model)
    if use_cache:
        cached = await cache_get_json(key)
        if cached is not None:
            return cached

    try:
        raw = await call_llm(prompt, system=system, model=model, temperature=temperature)
    except Exception:  # noqa: BLE001
        return dict(fallback)

    parsed = _parse_json(raw)
    if parsed is None:
        logger.warning("LLM 输出解析失败: %s", raw[:200])
        return dict(fallback)

    if use_cache:
        await cache_set_json(key, parsed, ex=settings.LLM_CACHE_TTL)
    return parsed


def _parse_json(raw: str) -> Optional[Any]:
    """先整体解析，失败则正则提取 JSON 片段（Prompt 文档 §7.1）。"""
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.DOTALL).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    m = _JSON_BLOCK.search(raw)
    if m:
        try:
            return json.loads(m.group())
        except json.JSONDecodeError:
            return None
    return None
