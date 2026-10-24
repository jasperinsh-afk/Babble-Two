"""本地 SQLite 文档存储：用 (collection, _id, json) 模拟云数据库集合。"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiosqlite

from app.repository.seed import load_seed_documents

logger = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    collection TEXT NOT NULL,
    id         TEXT NOT NULL,
    data       TEXT NOT NULL,
    PRIMARY KEY (collection, id)
);
CREATE INDEX IF NOT EXISTS idx_documents_collection ON documents(collection);
"""


class DocumentStore:
    def __init__(self, db_path: str, seed_file: str = "", shift_dates: bool = True):
        self.db_path = db_path
        self.seed_file = seed_file
        self.shift_dates = shift_dates
        self._conn: Optional[aiosqlite.Connection] = None
        self._init_lock = asyncio.Lock()
        self._write_lock = asyncio.Lock()

    async def ensure_ready(self) -> None:
        if self._conn is not None:
            return
        async with self._init_lock:
            if self._conn is not None:
                return
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            conn = await aiosqlite.connect(self.db_path)
            await conn.executescript(_SCHEMA)
            await conn.commit()
            self._conn = conn
            await self._seed_if_empty()

    async def _seed_if_empty(self) -> None:
        assert self._conn is not None
        async with self._conn.execute("SELECT COUNT(*) FROM documents") as cur:
            (count,) = await cur.fetchone()
        if count:
            return
        if not self.seed_file or not Path(self.seed_file).exists():
            logger.warning("[bala-web] 种子文件不存在：%s", self.seed_file)
            return
        seed = load_seed_documents(self.seed_file, shift_dates=self.shift_dates)
        rows = [
            (name, str(doc.get("_id") or uuid.uuid4().hex), json.dumps(doc, ensure_ascii=False))
            for name, docs in seed.items()
            for doc in docs
        ]
        await self._conn.executemany(
            "INSERT OR REPLACE INTO documents(collection, id, data) VALUES (?, ?, ?)", rows
        )
        await self._conn.commit()
        logger.info("[bala-web] 已导入本地种子数据 %d 条", len(rows))

    @property
    def conn(self) -> aiosqlite.Connection:
        if self._conn is None:
            raise RuntimeError("DocumentStore 尚未初始化，请先 await ensure_ready()")
        return self._conn

    async def docs(self, collection: str) -> List[Dict[str, Any]]:
        await self.ensure_ready()
        async with self.conn.execute(
            "SELECT data FROM documents WHERE collection = ?", (collection,)
        ) as cur:
            rows = await cur.fetchall()
        return [json.loads(row[0]) for row in rows]

    async def get(self, collection: str, doc_id: str) -> Optional[Dict[str, Any]]:
        await self.ensure_ready()
        async with self.conn.execute(
            "SELECT data FROM documents WHERE collection = ? AND id = ?",
            (collection, str(doc_id)),
        ) as cur:
            row = await cur.fetchone()
        return json.loads(row[0]) if row else None

    async def put(self, collection: str, doc: Dict[str, Any]) -> Dict[str, Any]:
        await self.ensure_ready()
        doc_id = str(doc.get("_id") or uuid.uuid4().hex)
        doc = {**doc, "_id": doc_id}
        async with self._write_lock:
            await self.conn.execute(
                "INSERT OR REPLACE INTO documents(collection, id, data) VALUES (?, ?, ?)",
                (collection, doc_id, json.dumps(doc, ensure_ascii=False)),
            )
            await self.conn.commit()
        return doc

    async def insert(self, collection: str, doc: Dict[str, Any]) -> Dict[str, Any]:
        return await self.put(collection, doc)

    async def delete(self, collection: str, doc_id: str) -> None:
        await self.ensure_ready()
        async with self._write_lock:
            await self.conn.execute(
                "DELETE FROM documents WHERE collection = ? AND id = ?",
                (collection, str(doc_id)),
            )
            await self.conn.commit()

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None


__all__ = ["DocumentStore"]
