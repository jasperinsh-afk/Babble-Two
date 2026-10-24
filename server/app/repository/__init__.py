"""网页版数据源装配：按配置在云数据库与本地 SQLite 之间选择。"""
from __future__ import annotations

from typing import Optional

from app.config import settings
from app.repository.base import BalaError, BalaRepository
from app.repository.cloud_repo import CloudRepository
from app.repository.local_repo import LocalRepository
from app.repository.local_store import DocumentStore

_repository: Optional[BalaRepository] = None


def get_repository() -> BalaRepository:
    global _repository
    if _repository is None:
        if settings.web_data_mode == "cloud":
            _repository = CloudRepository()
        else:
            _repository = LocalRepository(
                DocumentStore(
                    settings.web_local_db_path,
                    seed_file=settings.web_seed_file_path,
                    shift_dates=settings.WEB_SEED_SHIFT_DATES,
                )
            )
    return _repository


def reset_repository() -> None:
    """测试用：丢弃已装配的数据源。"""
    global _repository
    _repository = None


__all__ = [
    "BalaError",
    "BalaRepository",
    "CloudRepository",
    "LocalRepository",
    "DocumentStore",
    "get_repository",
    "reset_repository",
]
