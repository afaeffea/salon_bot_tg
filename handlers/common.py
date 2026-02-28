from __future__ import annotations
"""
/start, /admin, /master commands + global "back to main menu" callback.
"""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from keyboards.client_kb import main_menu_kb

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message, user: dict, is_admin: bool, master: dict | None):
    name = message.from_user.first_name or "!"
    text = f"👋 Привет, {name}!\n\nДобро пожаловать в салон красоты.\nВыберите действие:"
    await message.answer(text, reply_markup=main_menu_kb())


@router.message(Command("admin"))
async def cmd_admin(message: Message, is_admin: bool):
    if not is_admin:
        await message.answer("⛔ У вас нет доступа к панели администратора.")
        return
    from keyboards.admin_kb import admin_menu_kb
    await message.answer("🛠 <b>Панель администратора</b>", reply_markup=admin_menu_kb(), parse_mode="HTML")


@router.message(Command("master"))
async def cmd_master(message: Message, master: dict | None):
    if not master or not master["is_active"]:
        await message.answer("⛔ У вас нет доступа к панели мастера.")
        return
    from keyboards.master_kb import master_menu_kb
    await message.answer("🎨 <b>Панель мастера</b>", reply_markup=master_menu_kb(), parse_mode="HTML")


@router.callback_query(F.data == "cl_menu:main")
async def back_to_main(callback: CallbackQuery):
    await callback.message.edit_text("Главное меню:", reply_markup=main_menu_kb())
    await callback.answer()
