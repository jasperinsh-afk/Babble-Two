"""通用响应模型。

技术架构文档 §2.3 统一响应格式：
    {"code": 0, "message": "success", "data": {...}, "timestamp": 1696000000}
"""
from __future__ import annotations

import time
from typing import Any, Generic, List, Optional, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    code: int = 0
    message: str = "success"
    data: Optional[T] = None
    timestamp: int = 0

    @classmethod
    def ok(cls, data: Any = None, message: str = "success") -> "ApiResponse":
        return cls(code=0, message=message, data=data, timestamp=int(time.time()))


class Page(BaseModel, Generic[T]):
    items: List[T] = []
    total: int = 0
    offset: int = 0
    limit: int = 20
    has_more: bool = False

    @classmethod
    def build(cls, items: List[T], total: int, offset: int, limit: int) -> "Page[T]":
        return cls(
            items=items,
            total=total,
            offset=offset,
            limit=limit,
            has_more=offset + len(items) < total,
        )


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)
