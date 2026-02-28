"""
Admin panel handlers.
All actions protected by is_admin flag from middleware.
"""
from __future__ import annotations
import csv
import io
from datetime import date as date_type

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message, CallbackQuery, BufferedInputFile, InlineKeyboardMarkup, InlineKeyboardButton
)

from db.database import get_db
from db import repositories as repo
from services.validation import validate_time, validate_date
from keyboards.admin_kb import (
    admin_menu_kb,
    masters_list_kb, master_detail_kb,
    services_list_kb, service_detail_kb,
    ms_masters_kb, ms_services_kb,
    schedule_kb, breaks_list_kb,
    blocks_menu_kb, global_blocks_kb, master_blocks_select_kb, master_blocks_kb,
    appointments_filter_kb, appointments_list_kb, apts_master_select_kb,
)
from utils.formatting import fmt_date, fmt_appointment, WEEKDAY_SHORT

router = Router()


class AdminStates(StatesGroup):
    # Master management
    add_master_tg_id       = State()
    add_master_display     = State()
    # Service management
    add_svc_title          = State()
    add_svc_duration       = State()
    add_svc_price          = State()
    edit_svc_value         = State()   # data: {svc_id, field}
    # Master–service override
    ms_set_duration        = State()   # data: {ms_master_id, ms_service_id}
    ms_set_price           = State()
    # Work schedule
    sched_wd               = State()
    sched_start            = State()
    sched_end              = State()
    sched_step             = State()
    # Break
    break_wd               = State()
    break_start            = State()
    break_end              = State()
    # Block
    blk_date               = State()   # data: {blk_master_id or None}
    blk_start              = State()
    blk_end                = State()
    blk_reason             = State()
    # Appointments by date
    apts_date              = State()
    # Appointments by master – just select from kb, no free text
    apts_master_id         = State()


def _guard(is_admin: bool):
    return is_admin


#ADMIN MENU

@router.callback_query(F.data == "ad_menu:back")
async def admin_back(callback: CallbackQuery, is_admin: bool):
    if not _guard(is_admin):
        await callback.answer("⛔ Нет доступа.", show_alert=True)
        return
    await callback.message.edit_text(
        "🛠 <b>Панель администратора</b>", reply_markup=admin_menu_kb(), parse_mode="HTML"
    )
    await callback.answer()


#ENTRY

@router.callback_query(F.data == "ad_menu:masters")
async def masters_section(callback: CallbackQuery, is_admin: bool):
    if not _guard(is_admin):
        await callback.answer("⛔ Нет доступа.", show_alert=True)
        return
    db = await get_db()
    masters = await repo.get_all_masters(db, active_only=False)
    await callback.message.edit_text(
        "👩‍🎨 <b>Мастера:</b>", reply_markup=masters_list_kb(masters), parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "ad_menu:services")
async def services_section(callback: CallbackQuery, is_admin: bool):
    if not _guard(is_admin):
        await callback.answer("⛔ Нет доступа.", show_alert=True)
        return
    db = await get_db()
    services = await repo.get_all_services(db, active_only=False)
    await callback.message.edit_text(
        "💅 <b>Услуги:</b>", reply_markup=services_list_kb(services), parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "ad_menu:ms")
async def ms_section(callback: CallbackQuery, is_admin: bool):
    if not _guard(is_admin):
        await callback.answer("⛔ Нет доступа.", show_alert=True)
        return
    db = await get_db()
    masters = await repo.get_all_masters(db, active_only=True)
    await callback.message.edit_text(
        "🎚️ Выберите мастера:", reply_markup=ms_masters_kb(masters)
    )
    await callback.answer()


@router.callback_query(F.data == "ad_menu:schedule")
async def schedule_section(callback: CallbackQuery, is_admin: bool):
    if not _guard(is_admin):
        await callback.answer("⛔ Нет доступа.", show_alert=True)
        return
    db = await get_db()
    rules = await repo.get_all_work_rules(db)
    await callback.message.edit_text(
        "🗓️ <b>Расписание салона:</b>", reply_markup=schedule_kb(rules), parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "ad_menu:blocks")
async def blocks_section(callback: CallbackQuery, is_admin: bool):
    if not _guard(is_admin):
        await callback.answer("⛔ Нет доступа.", show_alert=True)
        return
    await callback.message.edit_text(
        "🧱 <b>Блокировки:</b>", reply_markup=blocks_menu_kb(), parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "ad_menu:apts")
async def appointments_section(callback: CallbackQuery, is_admin: bool):
    if not _guard(is_admin):
        await callback.answer("⛔ Нет доступа.", show_alert=True)
        return
    await callback.message.edit_text(
        "📋 <b>Записи:</b>", reply_markup=appointments_filter_kb(), parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "ad_menu:csv")
async def export_csv_cb(callback: CallbackQuery, is_admin: bool):
    if not _guard(is_admin):
        await callback.answer("⛔ Нет доступа.", show_alert=True)
        return
    db = await get_db()
    apts = await repo.get_all_appointments(db)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Дата", "Начало", "Конец", "Клиент", "Телефон", "Мастер", "Услуга", "Статус", "Создано"])
    for apt in apts:
        writer.writerow([
            apt["id"], apt["date"], apt["start_time"], apt["end_time"],
            apt.get("client_name") or apt.get("client_full_name", ""),
            apt.get("client_phone") or apt.get("client_phone_u", ""),
            apt.get("master_display_name", ""),
            apt.get("service_title", ""),
            apt["status"],
            apt.get("created_at", ""),
        ])
    output.seek(0)
    file = BufferedInputFile(output.getvalue().encode("utf-8-sig"), filename="appointments.csv")
    await callback.message.answer_document(file, caption=f"📊 Экспорт: {len(apts)} записей")
    await callback.answer()


#MASTERS

@router.callback_query(F.data == "ad_mst_list")
async def masters_list(callback: CallbackQuery, is_admin: bool):
    if not _guard(is_admin):
        return
    db = await get_db()
    masters = await repo.get_all_masters(db, active_only=False)
    await callback.message.edit_text("👩‍🎨 <b>Мастера:</b>", reply_markup=masters_list_kb(masters), parse_mode="HTML")


@router.callback_query(F.data.startswith("ad_mst:"))
async def master_detail(callback: CallbackQuery, is_admin: bool):
    if not _guard(is_admin):
        return
    master_id = int(callback.data.split(":")[1])
    db = await get_db()
    master = await repo.get_master_by_id(db, master_id)
    if not master:
        await callback.answer("Мастер не найден.", show_alert=True)
        return
    sched = "✅ разрешено" if master["allow_personal_schedule"] else "❌ запрещено"
    status = "активен" if master["is_active"] else "неактивен"
    text = (
        f"👩‍🎨 <b>{master['display_name']}</b>\n"
        f"TG ID: <code>{master['tg_id']}</code>\n"
        f"Username: @{master.get('username') or '—'}\n"
        f"Статус: {status}\n"
        f"Личное расписание: {sched}"
    )
    await callback.message.edit_text(text, reply_markup=master_detail_kb(master), parse_mode="HTML")


@router.callback_query(F.data == "ad_mst_add")
async def add_master_start(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    if not _guard(is_admin):
        return
    await state.set_state(AdminStates.add_master_tg_id)
    await callback.message.edit_text(
        "➕ <b>Добавить мастера</b>\n\nВведите Telegram ID или @username:",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(AdminStates.add_master_tg_id)
async def add_master_tg_id(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    db = await get_db()
    user = None
    if text.startswith("@"):
        user = await repo.get_user_by_username(db, text)
    else:
        try:
            tg_id = int(text)
            user = await repo.get_user_by_tg_id(db, tg_id)
            if not user:
                # Create a placeholder user
                user = await repo.get_or_create_user(db, tg_id, None, f"tg:{tg_id}")
        except ValueError:
            await message.answer("❗ Введите числовой Telegram ID или @username.")
            return
    if not user:
        await message.answer("❗ Пользователь не найден. Он должен сначала написать боту /start.")
        return
    # Check if already a master
    existing = await repo.get_master_by_user_id(db, user["id"])
    if existing:
        await message.answer(
            f"⚠️ Этот пользователь уже является мастером: {existing['display_name']}",
            reply_markup=admin_menu_kb(),
        )
        await state.clear()
        return
    await state.update_data(new_master_user_id=user["id"], new_master_tg_id=user["tg_id"])
    await state.set_state(AdminStates.add_master_display)
    await message.answer(
        f"✅ Пользователь найден: {user.get('full_name') or user['tg_id']}\n\n"
        "Введите отображаемое имя мастера:"
    )


@router.message(AdminStates.add_master_display)
async def add_master_display(message: Message, state: FSMContext, is_admin: bool):
    display_name = (message.text or "").strip()
    if not display_name:
        await message.answer("❗ Имя не может быть пустым.")
        return
    data = await state.get_data()
    db = await get_db()
    try:
        new_master = await repo.create_master(db, data["new_master_user_id"], display_name)
    except Exception as e:
        await state.clear()
        await message.answer(
            f"❗ Не удалось добавить мастера: {e}\n\nВозможно, этот пользователь уже является мастером.",
            reply_markup=admin_menu_kb(),
        )
        return
    await state.clear()
    sched = "✅ разрешено" if new_master["allow_personal_schedule"] else "❌ запрещено"
    status = "активен" if new_master["is_active"] else "неактивен"
    text = (
        f"✅ Мастер добавлен!\n\n"
        f"👩‍🎨 <b>{new_master['display_name']}</b>\n"
        f"TG ID: <code>{new_master['tg_id']}</code>\n"
        f"Username: @{new_master.get('username') or '—'}\n"
        f"Статус: {status}\n"
        f"Личное расписание: {sched}"
    )
    await message.answer(text, reply_markup=master_detail_kb(new_master), parse_mode="HTML")


@router.callback_query(F.data.startswith("ad_mst_tog:"))
async def toggle_master(callback: CallbackQuery, is_admin: bool):
    if not _guard(is_admin):
        return
    master_id = int(callback.data.split(":")[1])
    db = await get_db()
    master = await repo.get_master_by_id(db, master_id)
    if not master:
        await callback.answer("Мастер не найден.", show_alert=True)
        return
    new_val = 0 if master["is_active"] else 1
    await repo.update_master(db, master_id, is_active=new_val)
    master_upd = await repo.get_master_by_id(db, master_id)
    sched = "✅ разрешено" if master_upd["allow_personal_schedule"] else "❌ запрещено"
    status = "активен" if master_upd["is_active"] else "неактивен"
    text = (
        f"👩‍🎨 <b>{master_upd['display_name']}</b>\n"
        f"TG ID: <code>{master_upd['tg_id']}</code>\n"
        f"Статус: {status}\n"
        f"Личное расписание: {sched}"
    )
    await callback.message.edit_text(text, reply_markup=master_detail_kb(master_upd), parse_mode="HTML")
    await callback.answer("Статус изменён.")


@router.callback_query(F.data.startswith("ad_mst_sched:"))
async def toggle_personal_schedule(callback: CallbackQuery, is_admin: bool):
    if not _guard(is_admin):
        return
    master_id = int(callback.data.split(":")[1])
    db = await get_db()
    master = await repo.get_master_by_id(db, master_id)
    if not master:
        await callback.answer("Мастер не найден.", show_alert=True)
        return
    new_val = 0 if master["allow_personal_schedule"] else 1
    await repo.update_master(db, master_id, allow_personal_schedule=new_val)
    master_upd = await repo.get_master_by_id(db, master_id)
    sched = "✅ разрешено" if master_upd["allow_personal_schedule"] else "❌ запрещено"
    status = "активен" if master_upd["is_active"] else "неактивен"
    text = (
        f"👩‍🎨 <b>{master_upd['display_name']}</b>\n"
        f"TG ID: <code>{master_upd['tg_id']}</code>\n"
        f"Статус: {status}\n"
        f"Личное расписание: {sched}"
    )
    await callback.message.edit_text(text, reply_markup=master_detail_kb(master_upd), parse_mode="HTML")
    await callback.answer("Настройка изменена.")


#SERVICES

@router.callback_query(F.data == "ad_svc_list")
async def services_list_cb(callback: CallbackQuery, is_admin: bool):
    if not _guard(is_admin):
        return
    db = await get_db()
    services = await repo.get_all_services(db, active_only=False)
    await callback.message.edit_text(
        "💅 <b>Услуги:</b>", reply_markup=services_list_kb(services), parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("ad_svc:"))
async def service_detail(callback: CallbackQuery, is_admin: bool):
    if not _guard(is_admin):
        return
    svc_id = int(callback.data.split(":")[1])
    db = await get_db()
    svc = await repo.get_service_by_id(db, svc_id)
    if not svc:
        await callback.answer("Услуга не найдена.", show_alert=True)
        return
    status = "✅ активна" if svc["is_active"] else "⛔ неактивна"
    text = (
        f"💅 <b>{svc['title']}</b>\n"
        f"Длительность: {svc['default_duration_min']} мин\n"
        f"Цена: {svc['default_price_text']}\n"
        f"Статус: {status}"
    )
    await callback.message.edit_text(text, reply_markup=service_detail_kb(svc), parse_mode="HTML")


@router.callback_query(F.data == "ad_svc_add")
async def add_svc_start(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    if not _guard(is_admin):
        return
    await state.set_state(AdminStates.add_svc_title)
    await callback.message.edit_text("➕ <b>Новая услуга</b>\n\nВведите название:", parse_mode="HTML")


@router.message(AdminStates.add_svc_title)
async def add_svc_title(message: Message, state: FSMContext):
    title = (message.text or "").strip()
    if not title:
        await message.answer("❗ Название не может быть пустым.")
        return
    await state.update_data(svc_title=title)
    await state.set_state(AdminStates.add_svc_duration)
    await message.answer("⏱️ Введите длительность в минутах:")


@router.message(AdminStates.add_svc_duration)
async def add_svc_duration(message: Message, state: FSMContext):
    try:
        dur = int(message.text.strip())
        assert dur > 0
    except (ValueError, AssertionError):
        await message.answer("❗ Введите положительное число.")
        return
    await state.update_data(svc_duration=dur)
    await state.set_state(AdminStates.add_svc_price)
    await message.answer("💰 Введите цену (например, «1 500 ₽»):")


@router.message(AdminStates.add_svc_price)
async def add_svc_price(message: Message, state: FSMContext, is_admin: bool):
    price = (message.text or "").strip()
    data = await state.get_data()
    db = await get_db()
    svc = await repo.create_service(db, data["svc_title"], data["svc_duration"], price)
    await state.clear()
    await message.answer(
        f"✅ Услуга <b>{svc['title']}</b> добавлена.",
        reply_markup=admin_menu_kb(),
        parse_mode="HTML",
    )


#Edit service fields

@router.callback_query(F.data.startswith("ad_svc_ed_title:"))
@router.callback_query(F.data.startswith("ad_svc_ed_dur:"))
@router.callback_query(F.data.startswith("ad_svc_ed_price:"))
async def edit_svc_start(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    if not _guard(is_admin):
        return
    parts = callback.data.split(":")
    action = parts[0]
    svc_id = int(parts[1])
    field_map = {
        "ad_svc_ed_title": ("title", "название"),
        "ad_svc_ed_dur":   ("default_duration_min", "длительность в минутах"),
        "ad_svc_ed_price": ("default_price_text", "цену"),
    }
    field, label = field_map[action]
    await state.update_data(edit_svc_id=svc_id, edit_svc_field=field)
    await state.set_state(AdminStates.edit_svc_value)
    await callback.message.edit_text(f"✏️ Введите новое {label}:")


@router.message(AdminStates.edit_svc_value)
async def edit_svc_value(message: Message, state: FSMContext, is_admin: bool):
    data = await state.get_data()
    field = data["edit_svc_field"]
    value: str | int = (message.text or "").strip()
    if field == "default_duration_min":
        try:
            value = int(value)
            assert value > 0
        except (ValueError, AssertionError):
            await message.answer("❗ Введите положительное число.")
            return
    db = await get_db()
    await repo.update_service(db, data["edit_svc_id"], **{field: value})
    await state.clear()
    await message.answer("✅ Услуга обновлена.", reply_markup=admin_menu_kb())


@router.callback_query(F.data.startswith("ad_svc_tog:"))
async def toggle_service(callback: CallbackQuery, is_admin: bool):
    if not _guard(is_admin):
        return
    svc_id = int(callback.data.split(":")[1])
    db = await get_db()
    svc = await repo.get_service_by_id(db, svc_id)
    if not svc:
        await callback.answer("Услуга не найдена.", show_alert=True)
        return
    await repo.update_service(db, svc_id, is_active=0 if svc["is_active"] else 1)
    svc_upd = await repo.get_service_by_id(db, svc_id)
    status = "✅ активна" if svc_upd["is_active"] else "⛔ неактивна"
    await callback.message.edit_text(
        f"💅 <b>{svc_upd['title']}</b>\nСтатус: {status}",
        reply_markup=service_detail_kb(svc_upd),
        parse_mode="HTML",
    )
    await callback.answer("Статус изменён.")


#MASTER–SERVICE

@router.callback_query(F.data.startswith("ad_ms_m:"))
async def ms_choose_service(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    if not _guard(is_admin):
        return
    master_id = int(callback.data.split(":")[1])
    db = await get_db()
    services = await repo.get_all_services(db, active_only=False)
    await callback.message.edit_text(
        "🎚️ Выберите услугу для настройки:",
        reply_markup=ms_services_kb(services, master_id),
    )


@router.callback_query(F.data.startswith("ad_ms_s:"))
async def ms_set_start(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    if not _guard(is_admin):
        return
    parts = callback.data.split(":")
    master_id, svc_id = int(parts[1]), int(parts[2])
    db = await get_db()
    master = await repo.get_master_by_id(db, master_id)
    svc = await repo.get_service_by_id(db, svc_id)
    existing = await repo.get_master_service(db, master_id, svc_id)
    cur_dur = existing["duration_min"] if existing and existing["duration_min"] else svc["default_duration_min"]
    cur_price = existing["price_text"] if existing and existing["price_text"] else svc["default_price_text"]
    await state.update_data(ms_master_id=master_id, ms_service_id=svc_id)
    await state.set_state(AdminStates.ms_set_duration)
    await callback.message.edit_text(
        f"🎚️ <b>{master['display_name']}</b> — <b>{svc['title']}</b>\n\n"
        f"Текущая длительность: {cur_dur} мин\n"
        f"Текущая цена: {cur_price}\n\n"
        "Введите длительность в минутах (или /default для сброса):",
        parse_mode="HTML",
    )


@router.message(AdminStates.ms_set_duration)
async def ms_set_duration(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    if text == "/default":
        await state.update_data(ms_duration=None)
    else:
        try:
            dur = int(text)
            assert dur > 0
            await state.update_data(ms_duration=dur)
        except (ValueError, AssertionError):
            await message.answer("❗ Введите число или /default.")
            return
    await state.set_state(AdminStates.ms_set_price)
    await message.answer("💰 Введите цену (или /default для сброса):")


@router.message(AdminStates.ms_set_price)
async def ms_set_price(message: Message, state: FSMContext, is_admin: bool):
    text = (message.text or "").strip()
    price = None if text == "/default" else text
    data = await state.get_data()
    db = await get_db()
    await repo.upsert_master_service(
        db, data["ms_master_id"], data["ms_service_id"],
        data.get("ms_duration"), price, 1,
    )
    await state.clear()
    await message.answer("✅ Настройка мастер–услуга сохранена.", reply_markup=admin_menu_kb())


#WORK SCHEDULE

@router.callback_query(F.data.startswith("ad_sched_wd:"))
async def edit_sched_wd(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    if not _guard(is_admin):
        return
    wd = int(callback.data.split(":")[1])
    await state.update_data(sched_wd=wd)
    await state.set_state(AdminStates.sched_start)
    await callback.message.edit_text(
        f"🗓️ <b>{WEEKDAY_SHORT[wd]}</b>\n\n"
        "Введите время начала (ЧЧ:ММ) или /dayoff для выходного:",
        parse_mode="HTML",
    )


@router.message(AdminStates.sched_start)
async def admin_sched_start(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    if text == "/dayoff":
        data = await state.get_data()
        db = await get_db()
        await repo.delete_work_rule(db, data["sched_wd"])
        await state.clear()
        await message.answer("✅ День помечен как выходной.", reply_markup=admin_menu_kb())
        return
    if not validate_time(text):
        await message.answer("❗ Введите ЧЧ:ММ или /dayoff.")
        return
    await state.update_data(sched_start=text)
    await state.set_state(AdminStates.sched_end)
    await message.answer("🕐 Введите время окончания (ЧЧ:ММ):")


@router.message(AdminStates.sched_end)
async def admin_sched_end(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    if not validate_time(text):
        await message.answer("❗ Введите ЧЧ:ММ.")
        return
    await state.update_data(sched_end=text)
    await state.set_state(AdminStates.sched_step)
    await message.answer("⏱️ Введите шаг слотов в минутах (например, 30):")


@router.message(AdminStates.sched_step)
async def admin_sched_step(message: Message, state: FSMContext, is_admin: bool):
    try:
        step = int((message.text or "").strip())
        assert 5 <= step <= 120
    except (ValueError, AssertionError):
        await message.answer("❗ Введите число от 5 до 120.")
        return
    data = await state.get_data()
    db = await get_db()
    await repo.upsert_work_rule(db, data["sched_wd"], data["sched_start"], data["sched_end"], step)
    await state.clear()
    await message.answer("✅ Расписание обновлено.", reply_markup=admin_menu_kb())


#Breaks

@router.callback_query(F.data == "ad_breaks_list")
async def breaks_list(callback: CallbackQuery, is_admin: bool):
    if not _guard(is_admin):
        return
    db = await get_db()
    breaks = await repo.get_all_breaks(db)
    await callback.message.edit_text(
        "🍽️ <b>Перерывы:</b>", reply_markup=breaks_list_kb(breaks), parse_mode="HTML"
    )


@router.callback_query(F.data == "ad_sched_back")
async def sched_back(callback: CallbackQuery, is_admin: bool):
    if not _guard(is_admin):
        return
    db = await get_db()
    rules = await repo.get_all_work_rules(db)
    await callback.message.edit_text(
        "🗓️ <b>Расписание салона:</b>", reply_markup=schedule_kb(rules), parse_mode="HTML"
    )


@router.callback_query(F.data == "ad_break_add")
async def add_break_start(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    if not _guard(is_admin):
        return
    await state.set_state(AdminStates.break_wd)
    weekdays_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=WEEKDAY_SHORT[i], callback_data=f"ad_brk_wd:{i}")]
        for i in range(7)
    ])
    await callback.message.edit_text("🍽️ Выберите день недели:", reply_markup=weekdays_kb)


@router.callback_query(AdminStates.break_wd, F.data.startswith("ad_brk_wd:"))
async def break_wd_chosen(callback: CallbackQuery, state: FSMContext):
    wd = int(callback.data.split(":")[1])
    await state.update_data(break_wd=wd)
    await state.set_state(AdminStates.break_start)
    await callback.message.edit_text(f"🍽️ {WEEKDAY_SHORT[wd]}\n🕐 Введите время начала перерыва (ЧЧ:ММ):")


@router.message(AdminStates.break_start)
async def break_start_entered(message: Message, state: FSMContext):
    if not validate_time(message.text or ""):
        await message.answer("❗ Введите ЧЧ:ММ.")
        return
    await state.update_data(break_start=message.text.strip())
    await state.set_state(AdminStates.break_end)
    await message.answer("🕐 Введите время окончания (ЧЧ:ММ):")


@router.message(AdminStates.break_end)
async def break_end_entered(message: Message, state: FSMContext, is_admin: bool):
    if not validate_time(message.text or ""):
        await message.answer("❗ Введите ЧЧ:ММ.")
        return
    data = await state.get_data()
    db = await get_db()
    await repo.add_break(db, data["break_wd"], data["break_start"], message.text.strip())
    await state.clear()
    await message.answer(
        f"✅ Перерыв добавлен: {WEEKDAY_SHORT[data['break_wd']]} {data['break_start']}–{message.text.strip()}",
        reply_markup=admin_menu_kb(),
    )


@router.callback_query(F.data.startswith("ad_break_del:"))
async def delete_break_cb(callback: CallbackQuery, is_admin: bool):
    if not _guard(is_admin):
        return
    break_id = int(callback.data.split(":")[1])
    db = await get_db()
    await repo.delete_break(db, break_id)
    breaks = await repo.get_all_breaks(db)
    await callback.message.edit_reply_markup(reply_markup=breaks_list_kb(breaks))
    await callback.answer("Перерыв удалён.")


#BLOCKS

@router.callback_query(F.data == "ad_blk_menu")
async def blk_menu(callback: CallbackQuery, is_admin: bool):
    if not _guard(is_admin):
        return
    await callback.message.edit_text("🧱 <b>Блокировки:</b>", reply_markup=blocks_menu_kb(), parse_mode="HTML")


@router.callback_query(F.data == "ad_blk_global")
async def blk_global(callback: CallbackQuery, is_admin: bool):
    if not _guard(is_admin):
        return
    db = await get_db()
    blocks = await repo.get_all_blocks(db, master_id=None)
    await callback.message.edit_text(
        "🌐 <b>Общие блокировки:</b>",
        reply_markup=global_blocks_kb(blocks),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "ad_blk_master")
async def blk_master_select(callback: CallbackQuery, is_admin: bool):
    if not _guard(is_admin):
        return
    db = await get_db()
    masters = await repo.get_all_masters(db, active_only=True)
    await callback.message.edit_text(
        "👤 Выберите мастера:", reply_markup=master_blocks_select_kb(masters)
    )


@router.callback_query(F.data.startswith("ad_blk_msel:"))
async def blk_master_blocks(callback: CallbackQuery, is_admin: bool):
    if not _guard(is_admin):
        return
    master_id = int(callback.data.split(":")[1])
    db = await get_db()
    blocks = await repo.get_all_blocks(db, master_id=master_id)
    master = await repo.get_master_by_id(db, master_id)
    await callback.message.edit_text(
        f"🧱 Блокировки мастера {master['display_name']}:",
        reply_markup=master_blocks_kb(blocks, master_id),
    )


@router.callback_query(F.data.startswith("ad_blk_add:"))
async def blk_add_start(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    if not _guard(is_admin):
        return
    target = callback.data.split(":")[1]
    master_id = None if target == "global" else int(target)
    await state.update_data(blk_master_id=master_id)
    await state.set_state(AdminStates.blk_date)
    await callback.message.edit_text("🗓️ Введите дату блокировки (ГГГГ-ММ-ДД):")


@router.message(AdminStates.blk_date)
async def blk_date_entered(message: Message, state: FSMContext):
    if not validate_date(message.text or ""):
        await message.answer("❗ Введите дату ГГГГ-ММ-ДД.")
        return
    await state.update_data(blk_date=message.text.strip())
    await state.set_state(AdminStates.blk_start)
    await message.answer("🕐 Введите время начала (ЧЧ:ММ):")


@router.message(AdminStates.blk_start)
async def blk_start_entered(message: Message, state: FSMContext):
    if not validate_time(message.text or ""):
        await message.answer("❗ Введите ЧЧ:ММ.")
        return
    await state.update_data(blk_start=message.text.strip())
    await state.set_state(AdminStates.blk_end)
    await message.answer("🕐 Введите время окончания (ЧЧ:ММ):")


@router.message(AdminStates.blk_end)
async def blk_end_entered(message: Message, state: FSMContext):
    if not validate_time(message.text or ""):
        await message.answer("❗ Введите ЧЧ:ММ.")
        return
    await state.update_data(blk_end=message.text.strip())
    await state.set_state(AdminStates.blk_reason)
    await message.answer("📝 Введите причину (или /skip):")


@router.message(AdminStates.blk_reason)
async def blk_reason_entered(message: Message, state: FSMContext, is_admin: bool):
    reason = "" if (message.text or "").strip() in ("/skip", "-") else (message.text or "")
    data = await state.get_data()
    db = await get_db()
    await repo.add_block(
        db,
        date_str=data["blk_date"],
        start=data["blk_start"],
        end=data["blk_end"],
        reason=reason,
        master_id=data.get("blk_master_id"),
    )
    await state.clear()
    target = "общая" if data.get("blk_master_id") is None else f"для мастера #{data['blk_master_id']}"
    await message.answer(
        f"✅ Блокировка ({target}) добавлена: {data['blk_date']} {data['blk_start']}–{data['blk_end']}",
        reply_markup=admin_menu_kb(),
    )


@router.callback_query(F.data.startswith("ad_blk_del:"))
async def blk_delete(callback: CallbackQuery, is_admin: bool):
    if not _guard(is_admin):
        return
    block_id = int(callback.data.split(":")[1])
    db = await get_db()
    await repo.delete_block(db, block_id)
    await callback.answer("✅ Блокировка удалена.")
    blocks = await repo.get_all_blocks(db, master_id=None)
    try:
        await callback.message.edit_reply_markup(reply_markup=global_blocks_kb(blocks))
    except Exception:
        pass


#APPOINTMENTS

@router.callback_query(F.data == "ad_apts_date")
async def apts_by_date_start(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    if not _guard(is_admin):
        return
    await state.set_state(AdminStates.apts_date)
    await callback.message.edit_text("📆 Введите дату (ГГГГ-ММ-ДД):")


@router.message(AdminStates.apts_date)
async def apts_by_date(message: Message, state: FSMContext, is_admin: bool):
    if not validate_date(message.text or ""):
        await message.answer("❗ Введите дату ГГГГ-ММ-ДД.")
        return
    date_str = message.text.strip()
    db = await get_db()
    apts = await repo.get_appointments_by_date(db, date_str)
    await state.clear()
    await message.answer(
        f"📋 Записи на {fmt_date(date_str)}:",
        reply_markup=appointments_list_kb(apts),
    )


@router.callback_query(F.data == "ad_apts_master")
async def apts_by_master_select(callback: CallbackQuery, is_admin: bool):
    if not _guard(is_admin):
        return
    db = await get_db()
    masters = await repo.get_all_masters(db, active_only=False)
    await callback.message.edit_text(
        "👤 Выберите мастера:", reply_markup=apts_master_select_kb(masters)
    )


@router.callback_query(F.data.startswith("ad_apts_m:"))
async def apts_by_master(callback: CallbackQuery, is_admin: bool):
    if not _guard(is_admin):
        return
    master_id = int(callback.data.split(":")[1])
    db = await get_db()
    apts = await repo.get_appointments_for_master(db, master_id)
    master = await repo.get_master_by_id(db, master_id)
    await callback.message.edit_text(
        f"📋 Записи мастера {master['display_name']}:",
        reply_markup=appointments_list_kb(apts),
    )


@router.callback_query(F.data == "ad_apts_pending")
async def apts_pending(callback: CallbackQuery, is_admin: bool):
    if not _guard(is_admin):
        return
    db = await get_db()
    apts = await repo.get_pending_appointments(db)
    await callback.message.edit_text(
        "⏳ Все pending записи:", reply_markup=appointments_list_kb(apts)
    )


@router.callback_query(F.data.startswith("ad_apt:"))
async def apt_detail_admin(callback: CallbackQuery, is_admin: bool):
    if not _guard(is_admin):
        return
    apt_id = int(callback.data.split(":")[1])
    db = await get_db()
    apt = await repo.get_appointment_by_id(db, apt_id)
    if not apt:
        await callback.answer("Запись не найдена.", show_alert=True)
        return
    text = f"📋 <b>Запись #{apt['id']}</b>\n\n{fmt_appointment(apt, show_client=True, show_master=True)}"
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="ad_apts_pending")]
    ]))


#IGNORE

@router.callback_query(F.data == "ad_ignore")
async def ignore(callback: CallbackQuery):
    await callback.answer()
