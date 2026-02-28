"""
Master panel handlers.
"""
from __future__ import annotations
from datetime import date, timedelta

import pytz
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery

from config import settings
from db.database import get_db
from db import repositories as repo
from services.slots import compute_free_slots, m2t, t2m
from services.calendar_utils import build_calendar, current_ym
from services.notifications import (
    notify_confirmed, notify_declined,
    notify_reschedule_offer,
)
from services.validation import validate_time, validate_date
from keyboards.master_kb import (
    master_menu_kb,
    appointments_list_kb,
    appointment_actions_kb,
    blocks_list_kb,
    master_schedule_kb,
    reschedule_slot_confirm_kb,
)
from utils.formatting import fmt_date, fmt_appointment

router = Router()


class MasterStates(StatesGroup):
    # Reschedule offer
    reschedule_apt_id   = State()
    reschedule_date     = State()
    reschedule_time     = State()
    # My block
    block_date          = State()
    block_start         = State()
    block_end           = State()
    block_reason        = State()
    # Personal schedule
    sched_weekday       = State()
    sched_start         = State()
    sched_end           = State()
    sched_step          = State()


def _tz_today() -> date:
    tz = pytz.timezone(settings.TIMEZONE)
    from datetime import datetime
    return datetime.now(tz).date()


def _require_master(master):
    return master and master["is_active"]


# ─────────────────── MENU ENTRY POINTS ────────────────────────

@router.callback_query(F.data == "ma_menu:back")
async def master_back_menu(callback: CallbackQuery, master: dict | None):
    if not _require_master(master):
        await callback.answer("⛔ Нет доступа.", show_alert=True)
        return
    await callback.message.edit_text("🎨 <b>Панель мастера</b>", reply_markup=master_menu_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "ma_menu:today")
async def today_apts(callback: CallbackQuery, master: dict | None):
    if not _require_master(master):
        await callback.answer("⛔ Нет доступа.", show_alert=True)
        return
    db = await get_db()
    today = _tz_today().isoformat()
    apts = await repo.get_appointments_for_master(
        db, master["id"], date_str=today,
        status_filter=["pending", "confirmed", "reschedule_offered"],
    )
    await callback.message.edit_text(
        f"📅 Записи на сегодня ({fmt_date(today)}):",
        reply_markup=appointments_list_kb(apts),
    )
    await callback.answer()


@router.callback_query(F.data == "ma_menu:tomorrow")
async def tomorrow_apts(callback: CallbackQuery, master: dict | None):
    if not _require_master(master):
        await callback.answer("⛔ Нет доступа.", show_alert=True)
        return
    db = await get_db()
    tomorrow = (_tz_today() + timedelta(days=1)).isoformat()
    apts = await repo.get_appointments_for_master(
        db, master["id"], date_str=tomorrow,
        status_filter=["pending", "confirmed", "reschedule_offered"],
    )
    await callback.message.edit_text(
        f"📅 Записи на завтра ({fmt_date(tomorrow)}):",
        reply_markup=appointments_list_kb(apts),
    )
    await callback.answer()


@router.callback_query(F.data == "ma_menu:week")
async def week_apts(callback: CallbackQuery, master: dict | None):
    if not _require_master(master):
        await callback.answer("⛔ Нет доступа.", show_alert=True)
        return
    db = await get_db()
    apts_all = []
    today = _tz_today()
    for i in range(7):
        d = (today + timedelta(days=i)).isoformat()
        apts = await repo.get_appointments_for_master(
            db, master["id"], date_str=d,
            status_filter=["pending", "confirmed", "reschedule_offered"],
        )
        apts_all.extend(apts)
    await callback.message.edit_text(
        "📅 Записи на неделю:",
        reply_markup=appointments_list_kb(apts_all),
    )
    await callback.answer()


@router.callback_query(F.data == "ma_menu:pending")
async def pending_apts(callback: CallbackQuery, master: dict | None):
    if not _require_master(master):
        await callback.answer("⛔ Нет доступа.", show_alert=True)
        return
    db = await get_db()
    apts = await repo.get_appointments_for_master(
        db, master["id"], status_filter=["pending"]
    )
    await callback.message.edit_text(
        "✅ Записи, ожидающие подтверждения:",
        reply_markup=appointments_list_kb(apts),
    )
    await callback.answer()


# ─────────────────── APPOINTMENT DETAIL ──────────────────────

@router.callback_query(F.data.startswith("ma_apt:"))
async def apt_detail(callback: CallbackQuery, master: dict | None):
    if not _require_master(master):
        await callback.answer("⛔ Нет доступа.", show_alert=True)
        return
    apt_id = int(callback.data.split(":")[1])
    db = await get_db()
    apt = await repo.get_appointment_by_id(db, apt_id)
    if not apt or apt["master_id"] != master["id"]:
        await callback.answer("Запись не найдена.", show_alert=True)
        return
    text = f"📋 <b>Запись #{apt['id']}</b>\n\n{fmt_appointment(apt, show_client=True)}"
    if apt["status"] == "reschedule_offered" and apt.get("proposed_date"):
        text += (
            f"\n\n🔁 Предложено: {fmt_date(apt['proposed_date'])} "
            f"{apt['proposed_start_time']}–{apt['proposed_end_time']}"
        )
    await callback.message.edit_text(
        text, reply_markup=appointment_actions_kb(apt), parse_mode="HTML"
    )


@router.callback_query(F.data == "ma_back_list")
async def back_to_list(callback: CallbackQuery, master: dict | None):
    if not _require_master(master):
        await callback.answer()
        return
    db = await get_db()
    today = _tz_today().isoformat()
    apts = await repo.get_appointments_for_master(
        db, master["id"], date_str=today,
        status_filter=["pending", "confirmed", "reschedule_offered"],
    )
    await callback.message.edit_text(
        f"📅 Записи на сегодня ({fmt_date(today)}):",
        reply_markup=appointments_list_kb(apts),
    )


# ─────────────────── CONFIRM / DECLINE ────────────────────────

@router.callback_query(F.data.startswith("ma_conf:"))
async def confirm_apt(callback: CallbackQuery, master: dict | None):
    if not _require_master(master):
        await callback.answer("⛔ Нет доступа.", show_alert=True)
        return
    apt_id = int(callback.data.split(":")[1])
    db = await get_db()
    apt = await repo.get_appointment_by_id(db, apt_id)
    if not apt or apt["master_id"] != master["id"]:
        await callback.answer("Запись не найдена.", show_alert=True)
        return
    await repo.update_appointment_status(db, apt_id, "confirmed")
    apt_updated = await repo.get_appointment_by_id(db, apt_id)
    await callback.message.edit_text(
        f"✅ Запись #{apt_id} подтверждена.",
        reply_markup=None,
    )
    if apt_updated:
        await notify_confirmed(apt_updated)


@router.callback_query(F.data.startswith("ma_decl:"))
async def decline_apt(callback: CallbackQuery, master: dict | None):
    if not _require_master(master):
        await callback.answer("⛔ Нет доступа.", show_alert=True)
        return
    apt_id = int(callback.data.split(":")[1])
    db = await get_db()
    apt = await repo.get_appointment_by_id(db, apt_id)
    if not apt or apt["master_id"] != master["id"]:
        await callback.answer("Запись не найдена.", show_alert=True)
        return
    await repo.update_appointment_status(db, apt_id, "declined")
    apt_updated = await repo.get_appointment_by_id(db, apt_id)
    await callback.message.edit_text(f"❌ Запись #{apt_id} отклонена.", reply_markup=None)
    if apt_updated:
        await notify_declined(apt_updated)


# ─────────────────── RESCHEDULE OFFER ─────────────────────────

@router.callback_query(F.data.startswith("ma_res:"))
async def start_reschedule(callback: CallbackQuery, state: FSMContext, master: dict | None):
    if not _require_master(master):
        await callback.answer("⛔ Нет доступа.", show_alert=True)
        return
    apt_id = int(callback.data.split(":")[1])
    db = await get_db()
    apt = await repo.get_appointment_by_id(db, apt_id)
    if not apt or apt["master_id"] != master["id"]:
        await callback.answer("Запись не найдена.", show_alert=True)
        return
    await state.set_state(MasterStates.reschedule_date)
    await state.update_data(reschedule_apt_id=apt_id)
    y, m = current_ym()
    await callback.message.edit_text(
        f"🔁 Предложить перенос записи #{apt_id}\n\n📅 Выберите новую дату:",
        reply_markup=build_calendar(y, m, prefix="mres", extra=str(apt_id)),
    )


@router.callback_query(MasterStates.reschedule_date, F.data.startswith("mres:"))
async def reschedule_calendar(callback: CallbackQuery, state: FSMContext, master: dict | None):
    parts = callback.data.split(":")
    action = parts[1]
    year, month = int(parts[2]), int(parts[3])
    extra = parts[5] if len(parts) > 5 else (parts[4] if len(parts) > 4 else "")

    if action == "ignore":
        await callback.answer()
        return
    if action in ("prev", "next"):
        apt_id_str = extra
        await callback.message.edit_reply_markup(
            reply_markup=build_calendar(year, month, prefix="mres", extra=apt_id_str)
        )
        await callback.answer()
        return
    # action == "day"
    day = int(parts[4])
    apt_id_str = parts[5] if len(parts) > 5 else ""
    date_str = f"{year:04d}-{month:02d}-{day:02d}"

    data = await state.get_data()
    apt_id = data.get("reschedule_apt_id")
    db = await get_db()
    apt = await repo.get_appointment_by_id(db, apt_id)
    if not apt:
        await callback.answer("Запись не найдена.", show_alert=True)
        return
    duration = await repo.get_effective_duration(db, apt["master_id"], apt["service_id"])
    slots = await compute_free_slots(apt["master_id"], duration, date_str, exclude_apt_id=apt_id)
    if not slots:
        await callback.answer("На этот день нет свободных слотов.", show_alert=True)
        return
    await state.update_data(reschedule_date=date_str)
    await state.set_state(MasterStates.reschedule_time)
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    rows = []
    row = []
    for i, slot in enumerate(slots):
        compact = date_str.replace("-", "") + ":" + slot.replace(":", "")
        row.append(InlineKeyboardButton(
            text=slot, callback_data=f"ma_rslot:{apt_id}:{compact}"
        ))
        if len(row) == 4:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton(text="🔙 Отмена", callback_data=f"ma_apt:{apt_id}")])
    await callback.message.edit_text(
        f"🔁 Перенос записи #{apt_id}\n"
        f"📅 {fmt_date(date_str)}\n\n🕐 Выберите время:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
    )


@router.callback_query(MasterStates.reschedule_time, F.data.startswith("ma_rslot:"))
async def reschedule_slot_chosen(callback: CallbackQuery, state: FSMContext, master: dict | None):
    # ma_rslot:{apt_id}:{YYYYMMDD}:{HHMM}
    parts = callback.data.split(":")
    apt_id = int(parts[1])
    raw_date = parts[2]
    raw_time = parts[3]
    date_str = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:]}"
    time_str = f"{raw_time[:2]}:{raw_time[2:]}"

    db = await get_db()
    apt = await repo.get_appointment_by_id(db, apt_id)
    duration = await repo.get_effective_duration(db, apt["master_id"], apt["service_id"])
    end_time = m2t(t2m(time_str) + duration)

    await state.update_data(reschedule_time=time_str, reschedule_end=end_time)
    await callback.message.edit_text(
        f"🔁 Перенос записи #{apt_id}\n\n"
        f"📅 {fmt_date(date_str)}  🕐 {time_str}–{end_time}\n\n"
        "Подтвердить предложение?",
        reply_markup=reschedule_slot_confirm_kb(apt_id, date_str, time_str),
    )


@router.callback_query(F.data.startswith("ma_rsconf:"))
async def reschedule_confirm(callback: CallbackQuery, state: FSMContext, master: dict | None):
    # ma_rsconf:{apt_id}:{YYYYMMDD}:{HHMM}
    parts = callback.data.split(":")
    apt_id = int(parts[1])
    raw_date = parts[2]
    raw_time = parts[3]
    date_str = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:]}"
    time_str = f"{raw_time[:2]}:{raw_time[2:]}"

    db = await get_db()
    apt = await repo.get_appointment_by_id(db, apt_id)
    duration = await repo.get_effective_duration(db, apt["master_id"], apt["service_id"])
    end_time = m2t(t2m(time_str) + duration)

    await repo.offer_reschedule(db, apt_id, date_str, time_str, end_time)
    apt_updated = await repo.get_appointment_by_id(db, apt_id)
    await state.clear()
    await callback.message.edit_text(
        f"🔁 Перенос предложен клиенту.\n"
        f"📅 {fmt_date(date_str)}  🕐 {time_str}–{end_time}",
    )
    if apt_updated:
        await notify_reschedule_offer(apt_updated)


# ─────────────────── MY BLOCKS ────────────────────────────────

@router.callback_query(F.data == "ma_menu:blocks")
async def my_blocks(callback: CallbackQuery, master: dict | None):
    if not _require_master(master):
        await callback.answer("⛔ Нет доступа.", show_alert=True)
        return
    db = await get_db()
    blocks = await repo.get_all_blocks(db, master_id=master["id"])
    await callback.message.edit_text(
        "🧱 Ваши блокировки (нажмите для удаления):",
        reply_markup=blocks_list_kb(blocks),
    )
    await callback.answer()


@router.callback_query(F.data == "ma_blkadd")
async def add_block_start(callback: CallbackQuery, state: FSMContext, master: dict | None):
    if not _require_master(master):
        await callback.answer("⛔ Нет доступа.", show_alert=True)
        return
    await state.set_state(MasterStates.block_date)
    await callback.message.edit_text(
        "🗓 Введите дату блокировки (ГГГГ-ММ-ДД):"
    )


@router.message(MasterStates.block_date)
async def block_date_entered(message: Message, state: FSMContext):
    if not validate_date(message.text or ""):
        await message.answer("❗ Введите дату в формате ГГГГ-ММ-ДД.")
        return
    await state.update_data(block_date=message.text.strip())
    await state.set_state(MasterStates.block_start)
    await message.answer("🕐 Введите время начала (ЧЧ:ММ):")


@router.message(MasterStates.block_start)
async def block_start_entered(message: Message, state: FSMContext):
    if not validate_time(message.text or ""):
        await message.answer("❗ Введите время в формате ЧЧ:ММ.")
        return
    await state.update_data(block_start=message.text.strip())
    await state.set_state(MasterStates.block_end)
    await message.answer("🕐 Введите время окончания (ЧЧ:ММ):")


@router.message(MasterStates.block_end)
async def block_end_entered(message: Message, state: FSMContext):
    if not validate_time(message.text or ""):
        await message.answer("❗ Введите время в формате ЧЧ:ММ.")
        return
    await state.update_data(block_end=message.text.strip())
    await state.set_state(MasterStates.block_reason)
    await message.answer("📝 Укажите причину (или нажмите /skip):")


@router.message(MasterStates.block_reason)
async def block_reason_entered(message: Message, state: FSMContext, master: dict | None):
    reason = "" if message.text in ("/skip", "-") else (message.text or "")
    data = await state.get_data()
    db = await get_db()
    await repo.add_block(
        db,
        date_str=data["block_date"],
        start=data["block_start"],
        end=data["block_end"],
        reason=reason,
        master_id=master["id"] if master else None,
    )
    await state.clear()
    await message.answer(
        f"✅ Блокировка добавлена: {data['block_date']} {data['block_start']}–{data['block_end']}",
        reply_markup=master_menu_kb(),
    )


@router.callback_query(F.data.startswith("ma_blkdel:"))
async def delete_block(callback: CallbackQuery, master: dict | None):
    if not _require_master(master):
        await callback.answer("⛔ Нет доступа.", show_alert=True)
        return
    block_id = int(callback.data.split(":")[1])
    db = await get_db()
    await repo.delete_block(db, block_id)
    blocks = await repo.get_all_blocks(db, master_id=master["id"])
    await callback.message.edit_reply_markup(reply_markup=blocks_list_kb(blocks))
    await callback.answer("Блокировка удалена.")


# ─────────────────── PERSONAL SCHEDULE ───────────────────────

@router.callback_query(F.data == "ma_menu:schedule")
async def my_schedule(callback: CallbackQuery, master: dict | None):
    if not _require_master(master):
        await callback.answer("⛔ Нет доступа.", show_alert=True)
        return
    db = await get_db()
    allow = bool(master["allow_personal_schedule"])
    rules = await repo.get_all_master_work_rules(db, master["id"]) if allow else []
    await callback.message.edit_text(
        "🕒 Ваше личное расписание:" if allow else "🕒 Личное расписание:",
        reply_markup=master_schedule_kb(rules, allow),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("ma_sched:"))
async def edit_schedule_day(callback: CallbackQuery, state: FSMContext, master: dict | None):
    if not _require_master(master) or not master["allow_personal_schedule"]:
        await callback.answer("⛔ Нет доступа.", show_alert=True)
        return
    weekday = int(callback.data.split(":")[1])
    await state.update_data(sched_weekday=weekday)
    await state.set_state(MasterStates.sched_start)
    from utils.formatting import WEEKDAY_RU
    await callback.message.edit_text(
        f"📅 {WEEKDAY_RU[weekday]}\n\n🕐 Введите время начала (ЧЧ:ММ) или /dayoff для выходного:"
    )


@router.message(MasterStates.sched_start)
async def sched_start_entered(message: Message, state: FSMContext, master: dict | None):
    if message.text and message.text.strip() == "/dayoff":
        data = await state.get_data()
        db = await get_db()
        await repo.delete_master_work_rule(db, master["id"], data["sched_weekday"])
        await state.clear()
        await message.answer("✅ День помечен как выходной.", reply_markup=master_menu_kb())
        return
    if not validate_time(message.text or ""):
        await message.answer("❗ Введите время в формате ЧЧ:ММ или /dayoff.")
        return
    await state.update_data(sched_start=message.text.strip())
    await state.set_state(MasterStates.sched_end)
    await message.answer("🕐 Введите время окончания (ЧЧ:ММ):")


@router.message(MasterStates.sched_end)
async def sched_end_entered(message: Message, state: FSMContext):
    if not validate_time(message.text or ""):
        await message.answer("❗ Введите время в формате ЧЧ:ММ.")
        return
    await state.update_data(sched_end=message.text.strip())
    await state.set_state(MasterStates.sched_step)
    await message.answer("⏱️ Введите шаг слотов в минутах (например, 30):")


@router.message(MasterStates.sched_step)
async def sched_step_entered(message: Message, state: FSMContext, master: dict | None):
    try:
        step = int(message.text.strip())
        assert 5 <= step <= 120
    except (ValueError, AssertionError):
        await message.answer("❗ Введите число от 5 до 120.")
        return
    data = await state.get_data()
    db = await get_db()
    await repo.upsert_master_work_rule(
        db, master["id"], data["sched_weekday"],
        data["sched_start"], data["sched_end"], step,
    )
    await state.clear()
    await message.answer(
        f"✅ Расписание обновлено: {data['sched_start']}–{data['sched_end']}, шаг {step} мин.",
        reply_markup=master_menu_kb(),
    )


# ─────────────────── IGNORE ───────────────────────────────────

@router.callback_query(F.data == "ma_ignore")
async def ignore(callback: CallbackQuery):
    await callback.answer()
