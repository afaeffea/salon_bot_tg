"""
Client-facing handlers:
  • Booking flow (FSM)
  • My appointments
  • Cancel appointment
  • Reschedule accept / decline
"""
from __future__ import annotations
from datetime import date, datetime

import pytz
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
)

from config import settings
from db.database import get_db
from db import repositories as repo
from services.slots import compute_free_slots
from services.calendar_utils import build_calendar, current_ym
from services.notifications import (
    notify_new_booking, notify_confirmed,
    notify_cancelled, notify_reschedule_accepted, notify_reschedule_declined,
)
from services.validation import validate_name, validate_phone
from keyboards.client_kb import (
    main_menu_kb, services_kb, masters_kb, slots_kb,
    confirm_booking_kb, my_appointments_kb,
    appointment_detail_kb, cancel_confirm_kb,
)
from utils.formatting import fmt_date, fmt_appointment

router = Router()


class ClientBooking(StatesGroup):
    choosing_service = State()
    choosing_master  = State()
    choosing_date    = State()
    choosing_time    = State()
    entering_name    = State()
    entering_phone   = State()
    confirming       = State()


# ─────────────────── ENTRY: "Записаться" ──────────────────────

@router.callback_query(F.data == "cl_menu:book")
async def start_booking(callback: CallbackQuery, state: FSMContext):
    db = await get_db()
    services = await repo.get_all_services(db, active_only=True)
    if not services:
        await callback.answer("😔 К сожалению, услуги временно недоступны.", show_alert=True)
        return
    await state.set_state(ClientBooking.choosing_service)
    await callback.message.edit_text("💅 Выберите услугу:", reply_markup=services_kb(services))
    await callback.answer()


@router.callback_query(ClientBooking.choosing_service, F.data.startswith("cl_svc:"))
async def choose_service(callback: CallbackQuery, state: FSMContext):
    service_id = int(callback.data.split(":")[1])
    db = await get_db()
    service = await repo.get_service_by_id(db, service_id)
    if not service:
        await callback.answer("Услуга не найдена.", show_alert=True)
        return
    masters = await repo.get_masters_for_service(db, service_id)
    if not masters:
        await callback.answer("Нет доступных мастеров для этой услуги.", show_alert=True)
        return
    await state.update_data(
        service_id=service_id,
        service_title=service["title"],
        service_duration=service["default_duration_min"],
    )
    await state.set_state(ClientBooking.choosing_master)
    await callback.message.edit_text(
        f"💅 Услуга: <b>{service['title']}</b>\n\n👤 Выберите мастера:",
        reply_markup=masters_kb(masters),
        parse_mode="HTML",
    )


@router.callback_query(ClientBooking.choosing_service, F.data == "cl_back_main")
@router.callback_query(ClientBooking.choosing_master,  F.data == "cl_back_main")
async def booking_back_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Главное меню:", reply_markup=main_menu_kb())
    await callback.answer()


@router.callback_query(ClientBooking.choosing_master, F.data.startswith("cl_mst:"))
async def choose_master(callback: CallbackQuery, state: FSMContext):
    master_id = int(callback.data.split(":")[1])
    db = await get_db()
    master = await repo.get_master_by_id(db, master_id)
    if not master:
        await callback.answer("Мастер не найден.", show_alert=True)
        return
    data = await state.get_data()
    service_id = data["service_id"]
    duration = await repo.get_effective_duration(db, master_id, service_id)
    await state.update_data(
        master_id=master_id,
        master_name=master["display_name"],
        service_duration=duration,
    )
    await state.set_state(ClientBooking.choosing_date)
    y, m = current_ym()
    await callback.message.edit_text(
        f"💅 {data['service_title']}\n"
        f"👤 Мастер: <b>{master['display_name']}</b>\n\n"
        "📅 Выберите дату:",
        reply_markup=build_calendar(y, m, prefix="cl_cal"),
        parse_mode="HTML",
    )


@router.callback_query(ClientBooking.choosing_master, F.data == "cl_back_svc")
async def back_to_service(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ClientBooking.choosing_service)
    db = await get_db()
    services = await repo.get_all_services(db, active_only=True)
    await callback.message.edit_text("💅 Выберите услугу:", reply_markup=services_kb(services))


# ─────────────────── CALENDAR ─────────────────────────────────

@router.callback_query(ClientBooking.choosing_date, F.data.startswith("cl_cal:"))
async def calendar_action(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    # format: cl_cal:{action}:{year}:{month}[:{day}]
    action = parts[1]
    if action == "ignore":
        await callback.answer()
        return
    year, month = int(parts[2]), int(parts[3])
    if action in ("prev", "next"):
        await callback.message.edit_reply_markup(
            reply_markup=build_calendar(year, month, prefix="cl_cal")
        )
        await callback.answer()
        return
    # action == "day"
    day = int(parts[4])
    date_str = f"{year:04d}-{month:02d}-{day:02d}"
    data = await state.get_data()
    slots = await compute_free_slots(data["master_id"], data["service_duration"], date_str)
    if not slots:
        await callback.answer("На этот день нет свободных слотов.", show_alert=True)
        return
    await state.update_data(date_str=date_str)
    await state.set_state(ClientBooking.choosing_time)
    await callback.message.edit_text(
        f"💅 {data['service_title']}\n"
        f"👤 Мастер: {data['master_name']}\n"
        f"📅 Дата: <b>{fmt_date(date_str)}</b>\n\n"
        "🕐 Выберите время:",
        reply_markup=slots_kb(date_str, slots),
        parse_mode="HTML",
    )


# ─────────────────── TIME SLOT ────────────────────────────────

@router.callback_query(ClientBooking.choosing_time, F.data.startswith("cl_slot:"))
async def choose_slot(callback: CallbackQuery, state: FSMContext):
    # format: cl_slot:{YYYYMMDD}:{HHMM}
    parts = callback.data.split(":")
    raw_date = parts[1]   # YYYYMMDD
    raw_time = parts[2]   # HHMM
    date_str = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:]}"
    time_str = f"{raw_time[:2]}:{raw_time[2:]}"

    data = await state.get_data()
    from services.slots import m2t, t2m
    end_m = t2m(time_str) + data["service_duration"]
    end_time = m2t(end_m)

    await state.update_data(time_str=time_str, end_time=end_time)
    await state.set_state(ClientBooking.entering_name)
    await callback.message.edit_text(
        f"💅 {data['service_title']}\n"
        f"👤 Мастер: {data['master_name']}\n"
        f"📅 {fmt_date(date_str)}  🕐 {time_str}–{end_time}\n\n"
        "✍️ Введите ваше имя:",
        parse_mode="HTML",
    )


@router.callback_query(ClientBooking.choosing_time, F.data == "cl_back_date")
async def back_to_date(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ClientBooking.choosing_date)
    y, m = current_ym()
    await callback.message.edit_text(
        "📅 Выберите дату:",
        reply_markup=build_calendar(y, m, prefix="cl_cal"),
    )


# ─────────────────── NAME ─────────────────────────────────────

@router.message(ClientBooking.entering_name)
async def enter_name(message: Message, state: FSMContext):
    name = validate_name(message.text or "")
    if not name:
        await message.answer("❗ Введите корректное имя (2–64 символа).")
        return
    await state.update_data(client_name=name)
    await state.set_state(ClientBooking.entering_phone)
    await message.answer("📞 Введите ваш номер телефона (например, +7 999 123-45-67):")


# ─────────────────── PHONE ────────────────────────────────────

@router.message(ClientBooking.entering_phone)
async def enter_phone(message: Message, state: FSMContext, user: dict):
    phone = validate_phone(message.text or "")
    if not phone:
        await message.answer("❗ Введите корректный номер телефона.")
        return
    data = await state.get_data()
    db = await get_db()
    await repo.update_user_phone(db, user["id"], phone)
    await state.update_data(client_phone=phone)
    await state.set_state(ClientBooking.confirming)
    summary = (
        f"📋 <b>Подтвердите запись:</b>\n\n"
        f"💅 Услуга:  {data['service_title']}\n"
        f"👤 Мастер:  {data['master_name']}\n"
        f"📅 Дата:    {fmt_date(data['date_str'])}\n"
        f"🕐 Время:   {data['time_str']}–{data['end_time']}\n"
        f"👤 Имя:     {data['client_name']}\n"
        f"📞 Телефон: {phone}"
    )
    await message.answer(summary, reply_markup=confirm_booking_kb(), parse_mode="HTML")


# ─────────────────── CONFIRM ──────────────────────────────────

@router.callback_query(ClientBooking.confirming, F.data == "cl_book_ok")
async def confirm_booking(callback: CallbackQuery, state: FSMContext, user: dict):
    data = await state.get_data()
    db = await get_db()
    apt, result = await repo.create_appointment(
        db,
        client_id=user["id"],
        master_id=data["master_id"],
        service_id=data["service_id"],
        date_str=data["date_str"],
        start_time=data["time_str"],
        end_time=data["end_time"],
        client_name=data["client_name"],
        client_phone=data["client_phone"],
    )
    await state.clear()
    if result == "overlap":
        await callback.message.edit_text(
            "😔 К сожалению, это время уже занято. Пожалуйста, выберите другое.",
            reply_markup=None,
        )
        await callback.message.answer("Главное меню:", reply_markup=main_menu_kb())
        return
    if not apt:
        await callback.message.edit_text("⚠️ Ошибка при создании записи. Попробуйте позже.")
        await callback.message.answer("Главное меню:", reply_markup=main_menu_kb())
        return
    await callback.message.edit_text(
        f"✅ <b>Запись создана!</b>\n\n"
        f"{fmt_appointment(apt, show_master=True)}\n\n"
        "Ожидайте подтверждения мастера.",
        parse_mode="HTML",
    )
    await callback.message.answer("Главное меню:", reply_markup=main_menu_kb())
    await notify_new_booking(apt)


@router.callback_query(ClientBooking.confirming, F.data == "cl_book_cancel")
async def cancel_booking_flow(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Запись отменена.")
    await callback.message.answer("Главное меню:", reply_markup=main_menu_kb())


# ─────────────────── MY APPOINTMENTS ──────────────────────────

@router.callback_query(F.data.in_({"cl_menu:my", "cl_my_apts"}))
async def my_appointments(callback: CallbackQuery, user: dict):
    db = await get_db()
    apts = await repo.get_appointments_for_client(db, user["id"])
    kb = my_appointments_kb(apts)
    text = "📅 <b>Ваши записи:</b>" if apts else "📅 У вас нет активных записей."
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("cl_apt:"))
async def appointment_detail(callback: CallbackQuery, user: dict):
    apt_id = int(callback.data.split(":")[1])
    db = await get_db()
    apt = await repo.get_appointment_by_id(db, apt_id)
    if not apt or apt["client_id"] != user["id"]:
        await callback.answer("Запись не найдена.", show_alert=True)
        return
    text = f"📋 <b>Запись #{apt['id']}</b>\n\n{fmt_appointment(apt, show_master=True)}"
    if apt["status"] == "reschedule_offered" and apt.get("proposed_date"):
        text += (
            f"\n\n🔁 <b>Предложено новое время:</b>\n"
            f"📅 {fmt_date(apt['proposed_date'])}  "
            f"🕐 {apt['proposed_start_time']}–{apt['proposed_end_time']}"
        )
    await callback.message.edit_text(text, reply_markup=appointment_detail_kb(apt), parse_mode="HTML")


# ─────────────────── CANCEL APPOINTMENT ───────────────────────

@router.callback_query(F.data == "cl_menu:cancel")
async def cancel_menu(callback: CallbackQuery, user: dict):
    db = await get_db()
    apts = await repo.get_appointments_for_client(db, user["id"])
    cancellable = [a for a in apts if a["status"] in ("pending", "confirmed")]
    kb = my_appointments_kb(cancellable)
    text = "❌ Выберите запись для отмены:" if cancellable else "Нет записей для отмены."
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("cl_acancel:"))
async def initiate_cancel(callback: CallbackQuery, user: dict):
    apt_id = int(callback.data.split(":")[1])
    db = await get_db()
    apt = await repo.get_appointment_by_id(db, apt_id)
    if not apt or apt["client_id"] != user["id"]:
        await callback.answer("Запись не найдена.", show_alert=True)
        return
    await callback.message.edit_text(
        f"❓ Вы уверены, что хотите отменить запись?\n\n{fmt_appointment(apt, show_master=True)}",
        reply_markup=cancel_confirm_kb(apt_id),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("cl_acancok:"))
async def confirm_cancel(callback: CallbackQuery, user: dict):
    apt_id = int(callback.data.split(":")[1])
    db = await get_db()
    apt = await repo.get_appointment_by_id(db, apt_id)
    if not apt or apt["client_id"] != user["id"]:
        await callback.answer("Запись не найдена.", show_alert=True)
        return
    await repo.cancel_appointment(db, apt_id)
    apt_updated = await repo.get_appointment_by_id(db, apt_id)
    await callback.message.edit_text("🚫 Запись отменена.")
    if apt_updated:
        await notify_cancelled(apt_updated)


# ─────────────────── RESCHEDULE RESPONSE ──────────────────────

@router.callback_query(F.data.startswith("cl_rsr_ok:"))
async def reschedule_accept(callback: CallbackQuery, user: dict):
    apt_id = int(callback.data.split(":")[1])
    db = await get_db()
    apt = await repo.get_appointment_by_id(db, apt_id)
    if not apt or apt["client_id"] != user["id"]:
        await callback.answer("Запись не найдена.", show_alert=True)
        return
    new_apt = await repo.accept_reschedule(db, apt_id)
    if not new_apt:
        await callback.answer("Не удалось принять перенос — время уже занято.", show_alert=True)
        return
    apt_updated = await repo.get_appointment_by_id(db, apt_id)
    await callback.message.edit_text(
        f"✅ Перенос принят!\n\n"
        f"Новая запись #{new_apt['id']}:\n"
        f"{fmt_appointment(new_apt, show_master=True)}",
        parse_mode="HTML",
    )
    if apt_updated:
        await notify_reschedule_accepted(apt_updated, new_apt)


@router.callback_query(F.data.startswith("cl_rsr_no:"))
async def reschedule_decline(callback: CallbackQuery, user: dict):
    apt_id = int(callback.data.split(":")[1])
    db = await get_db()
    apt = await repo.get_appointment_by_id(db, apt_id)
    if not apt or apt["client_id"] != user["id"]:
        await callback.answer("Запись не найдена.", show_alert=True)
        return
    await repo.decline_reschedule(db, apt_id)
    apt_updated = await repo.get_appointment_by_id(db, apt_id)
    await callback.message.edit_text("❌ Вы отказались от переноса.")
    if apt_updated:
        await notify_reschedule_declined(apt_updated)


# ─────────────────── CONTACTS ─────────────────────────────────

@router.callback_query(F.data == "cl_menu:contacts")
async def contacts(callback: CallbackQuery):
    from config import settings as s
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🔙 Назад", callback_data="cl_menu:main")
    ]])
    await callback.message.edit_text(s.CONTACT_INFO, reply_markup=kb)
    await callback.answer()


# ─────────────────── IGNORE ───────────────────────────────────

@router.callback_query(F.data == "cl_ignore")
async def ignore(callback: CallbackQuery):
    await callback.answer()
