"""
All outgoing notifications to clients, masters, and admins.
"""
from __future__ import annotations

from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import settings
from utils.formatting import fmt_date, fmt_appointment

_bot: Bot | None = None


def set_bot(bot: Bot) -> None:
    global _bot
    _bot = bot


async def _send(chat_id: int, text: str, reply_markup=None) -> None:
    if _bot is None:
        return
    try:
        await _bot.send_message(chat_id, text, reply_markup=reply_markup, parse_mode="HTML")
    except Exception:
        pass  # user may have blocked the bot


# ─────────────────────── NEW BOOKING ──────────────────────────

async def notify_new_booking(apt: dict) -> None:
    """Notify master + all admins about a new booking."""
    text = (
        f"🔔 <b>Новая запись #{apt['id']}</b>\n\n"
        f"{fmt_appointment(apt, show_client=True)}"
    )
    master_kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"ma_conf:{apt['id']}"),
        InlineKeyboardButton(text="❌ Отклонить",   callback_data=f"ma_decl:{apt['id']}"),
    ], [
        InlineKeyboardButton(text="🔁 Предложить перенос", callback_data=f"ma_res:{apt['id']}"),
    ]])
    await _send(apt["master_tg_id"], text, master_kb)
    for admin_id in settings.admin_ids:
        await _send(admin_id, f"📋 {text}")


# ─────────────────────── APPOINTMENT CONFIRMED ────────────────

async def notify_confirmed(apt: dict) -> None:
    text = (
        f"✅ <b>Запись подтверждена!</b>\n\n"
        f"{fmt_appointment(apt, show_master=True)}"
    )
    await _send(apt["client_tg_id"], text)
    for admin_id in settings.admin_ids:
        await _send(admin_id, f"✅ Запись #{apt['id']} подтверждена мастером {apt['master_display_name']}.")


# ─────────────────────── APPOINTMENT DECLINED ─────────────────

async def notify_declined(apt: dict) -> None:
    text = (
        f"❌ <b>Запись отклонена.</b>\n\n"
        f"{fmt_appointment(apt, show_master=True)}\n\n"
        "Вы можете записаться на другое время."
    )
    await _send(apt["client_tg_id"], text)
    for admin_id in settings.admin_ids:
        await _send(admin_id, f"❌ Запись #{apt['id']} отклонена мастером {apt['master_display_name']}.")


# ─────────────────────── RESCHEDULE OFFER ─────────────────────

async def notify_reschedule_offer(apt: dict) -> None:
    """Send reschedule proposal to client."""
    proposed = (
        f"📅 {fmt_date(apt['proposed_date'])}  "
        f"🕐 {apt['proposed_start_time']}–{apt['proposed_end_time']}"
    )
    text = (
        f"🔁 <b>Мастер предлагает перенести вашу запись</b>\n\n"
        f"Услуга: {apt['service_title']}\n"
        f"Мастер: {apt['master_display_name']}\n\n"
        f"<b>Предложенное время:</b>\n{proposed}"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Принять",   callback_data=f"cl_rsr_ok:{apt['id']}"),
        InlineKeyboardButton(text="❌ Отказаться", callback_data=f"cl_rsr_no:{apt['id']}"),
    ]])
    await _send(apt["client_tg_id"], text, kb)


# ─────────────────────── RESCHEDULE ACCEPTED ──────────────────

async def notify_reschedule_accepted(old_apt: dict, new_apt: dict) -> None:
    await _send(
        old_apt["master_tg_id"],
        f"✅ Клиент принял перенос записи #{old_apt['id']}.\n"
        f"Новая запись #{new_apt['id']}: "
        f"{fmt_date(new_apt['date'])} {new_apt['start_time']}–{new_apt['end_time']}",
    )
    for admin_id in settings.admin_ids:
        await _send(
            admin_id,
            f"🔁 Перенос принят. Запись #{old_apt['id']} → #{new_apt['id']} "
            f"({fmt_date(new_apt['date'])} {new_apt['start_time']}).",
        )


# ─────────────────────── RESCHEDULE DECLINED ──────────────────

async def notify_reschedule_declined(apt: dict) -> None:
    await _send(
        apt["master_tg_id"],
        f"❌ Клиент отказался от переноса записи #{apt['id']}.",
    )


# ─────────────────────── APPOINTMENT CANCELLED ────────────────

async def notify_cancelled(apt: dict) -> None:
    text = (
        f"🚫 Запись #{apt['id']} отменена клиентом.\n"
        f"{fmt_appointment(apt, show_client=True)}"
    )
    await _send(apt["master_tg_id"], text)
    for admin_id in settings.admin_ids:
        await _send(admin_id, text)
