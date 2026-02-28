from __future__ import annotations
import aiosqlite
import asyncio
from pathlib import Path
from config import settings

_db: aiosqlite.Connection | None = None
_lock = asyncio.Lock()


async def get_db() -> aiosqlite.Connection:
    global _db
    if _db is None:
        async with _lock:
            if _db is None:
                _db = await aiosqlite.connect(settings.DB_PATH)
                _db.row_factory = aiosqlite.Row
                await _db.execute("PRAGMA foreign_keys = ON")
                await _db.execute("PRAGMA journal_mode = WAL")
    return _db


async def init_db():
    db = await get_db()
    sql_path = Path(__file__).parent.parent / "init.sql"
    sql = sql_path.read_text(encoding="utf-8")
    await db.executescript(sql)
    await db.commit()


async def close_db():
    global _db
    if _db is not None:
        await _db.close()
        _db = None
