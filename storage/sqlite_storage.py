from __future__ import annotations
"""
Persistent FSM storage backed by SQLite.
Survives bot restarts.
"""
import json
from typing import Any, Dict, Optional

from aiogram.fsm.storage.base import BaseStorage, StorageKey

from db.database import get_db


def _key(k: StorageKey) -> str:
    return f"{k.bot_id}:{k.chat_id}:{k.user_id}:{k.destiny}"


class SqliteStorage(BaseStorage):
    async def set_state(
        self, key: StorageKey, state=None
    ) -> None:
        db = await get_db()
        k = _key(key)
        # aiogram may pass a State object — convert it to its string form
        if state is not None and not isinstance(state, str):
            state = state.state
        await db.execute(
            """INSERT INTO fsm_data (storage_key, state)
               VALUES (?, ?)
               ON CONFLICT(storage_key)
               DO UPDATE SET state=excluded.state""",
            (k, state),
        )
        await db.commit()

    async def get_state(self, key: StorageKey) -> Optional[str]:
        db = await get_db()
        cur = await db.execute(
            "SELECT state FROM fsm_data WHERE storage_key=?", (_key(key),)
        )
        row = await cur.fetchone()
        return row["state"] if row else None

    async def set_data(
        self, key: StorageKey, data: Dict[str, Any]
    ) -> None:
        db = await get_db()
        k = _key(key)
        await db.execute(
            """INSERT INTO fsm_data (storage_key, data)
               VALUES (?, ?)
               ON CONFLICT(storage_key)
               DO UPDATE SET data=excluded.data""",
            (k, json.dumps(data, ensure_ascii=False)),
        )
        await db.commit()

    async def get_data(self, key: StorageKey) -> Dict[str, Any]:
        db = await get_db()
        cur = await db.execute(
            "SELECT data FROM fsm_data WHERE storage_key=?", (_key(key),)
        )
        row = await cur.fetchone()
        if row and row["data"]:
            try:
                return json.loads(row["data"])
            except Exception:
                return {}
        return {}

    async def close(self) -> None:
        from db.database import close_db
        await close_db()
