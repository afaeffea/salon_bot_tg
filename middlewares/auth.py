"""
Middleware that:
 1. Registers / refreshes the user in the DB on every update.
 2. Injects `user`, `is_admin`, `master` into handler data.
"""
from __future__ import annotations
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update

from config import settings
from db.database import get_db
from db import repositories as repo


class AuthMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        from_user = None
        if hasattr(event, "from_user"):
            from_user = event.from_user
        elif isinstance(event, Update):
            if event.message:
                from_user = event.message.from_user
            elif event.callback_query:
                from_user = event.callback_query.from_user

        if from_user:
            db = await get_db()
            user = await repo.get_or_create_user(
                db,
                from_user.id,
                from_user.username,
                from_user.full_name,
            )
            master = await repo.get_master_by_tg_id(db, from_user.id)
            data["user"] = user
            data["is_admin"] = from_user.id in settings.admin_ids
            data["master"] = master  # None if not a master

        return await handler(event, data)
