from __future__ import annotations
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Записаться",     callback_data="cl_menu:book"),
            InlineKeyboardButton(text="📅 Мои записи",    callback_data="cl_menu:my"),
        ],
        [
            InlineKeyboardButton(text="❌ Отменить запись", callback_data="cl_menu:cancel"),
            InlineKeyboardButton(text="ℹ️ Контакты",       callback_data="cl_menu:contacts"),
        ],
    ])


def services_kb(services: list[dict]) -> InlineKeyboardMarkup:
    rows = []
    for s in services:
        rows.append([InlineKeyboardButton(
            text=f"💅 {s['title']} — {s['default_price_text']} ({s['default_duration_min']} мин)",
            callback_data=f"cl_svc:{s['id']}",
        )])
    rows.append([InlineKeyboardButton(text="🔙 Назад", callback_data="cl_back_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def masters_kb(masters: list[dict]) -> InlineKeyboardMarkup:
    rows = []
    for m in masters:
        price = m.get("eff_price") or ""
        dur = m.get("eff_duration") or ""
        label = m["display_name"]
        if price or dur:
            label += f" — {price}"
            if dur:
                label += f" ({dur} мин)"
        rows.append([InlineKeyboardButton(text=f"👤 {label}", callback_data=f"cl_mst:{m['id']}")])
    rows.append([InlineKeyboardButton(text="🔙 Назад", callback_data="cl_back_svc")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def slots_kb(date_str: str, slots: list[str]) -> InlineKeyboardMarkup:
    rows = []
    row = []
    for i, slot in enumerate(slots):
        compact = date_str.replace("-", "") + ":" + slot.replace(":", "")
        row.append(InlineKeyboardButton(text=slot, callback_data=f"cl_slot:{compact}"))
        if len(row) == 4:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton(text="🔙 Назад", callback_data="cl_back_date")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def confirm_booking_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Подтвердить", callback_data="cl_book_ok"),
        InlineKeyboardButton(text="❌ Отмена",      callback_data="cl_book_cancel"),
    ]])


def my_appointments_kb(appointments: list[dict]) -> InlineKeyboardMarkup:
    from utils.formatting import fmt_date, STATUS_LABELS
    rows = []
    for apt in appointments:
        label = (
            f"{fmt_date(apt['date'])} {apt['start_time']} "
            f"— {apt.get('service_title','?')} "
            f"[{STATUS_LABELS.get(apt['status'], apt['status'])}]"
        )
        rows.append([InlineKeyboardButton(text=label, callback_data=f"cl_apt:{apt['id']}")])
    if not rows:
        rows.append([InlineKeyboardButton(text="Нет записей", callback_data="cl_ignore")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def appointment_detail_kb(apt: dict) -> InlineKeyboardMarkup:
    rows = []
    if apt["status"] in ("pending", "confirmed"):
        rows.append([InlineKeyboardButton(
            text="🚫 Отменить запись", callback_data=f"cl_acancel:{apt['id']}"
        )])
    if apt["status"] == "reschedule_offered":
        rows.append([
            InlineKeyboardButton(text="✅ Принять перенос",   callback_data=f"cl_rsr_ok:{apt['id']}"),
            InlineKeyboardButton(text="❌ Отказаться от переноса", callback_data=f"cl_rsr_no:{apt['id']}"),
        ])
    rows.append([InlineKeyboardButton(text="🔙 Назад", callback_data="cl_my_apts")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def cancel_confirm_kb(apt_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Да, отменить",  callback_data=f"cl_acancok:{apt_id}"),
        InlineKeyboardButton(text="❌ Нет, назад",    callback_data=f"cl_apt:{apt_id}"),
    ]])
