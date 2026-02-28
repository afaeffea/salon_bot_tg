from __future__ import annotations
"""
Entry point.  Run with:  python main.py
"""
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import settings
from db.database import init_db, close_db
from storage.sqlite_storage import SqliteStorage
from middlewares.auth import AuthMiddleware
from services import notifications
from handlers import common, client, master, admin


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    log = logging.getLogger("main")

    # ── Init DB ──────────────────────────────────────────────
    log.info("Initialising database …")
    await init_db()
    log.info("Database ready.")

    # ── Bot & Dispatcher ─────────────────────────────────────
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    storage = SqliteStorage()
    dp = Dispatcher(storage=storage)

    # ── Notifications ────────────────────────────────────────
    notifications.set_bot(bot)

    # ── Middlewares ──────────────────────────────────────────
    dp.message.outer_middleware(AuthMiddleware())
    dp.callback_query.outer_middleware(AuthMiddleware())

    # ── Routers ──────────────────────────────────────────────
    dp.include_router(common.router)
    dp.include_router(client.router)
    dp.include_router(master.router)
    dp.include_router(admin.router)

    # ── Start polling ────────────────────────────────────────
    log.info("Bot started. Press Ctrl+C to stop.")
    try:
        await dp.start_polling(bot, allowed_updates=["message", "callback_query"])
    finally:
        await close_db()
        await bot.session.close()
        log.info("Bot stopped.")


if __name__ == "__main__":
    asyncio.run(main())
