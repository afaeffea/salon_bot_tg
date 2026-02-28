from __future__ import annotations
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def master_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📅 Сегодня",       callback_data="ma_menu:today"),
            InlineKeyboardButton(text="📅 Завтра",        callback_data="ma_menu:tomorrow"),
        ],
        [
            InlineKeyboardButton(text="📅 Неделя",        callback_data="ma_menu:week"),
            InlineKeyboardButton(text="✅ Ожидают",       callback_data="ma_menu:pending"),
        ],
        [
            InlineKeyboardButton(text="🧱 Не получать запросы", callback_data="ma_menu:blocks"),
            InlineKeyboardButton(text="🕒 Моё расписание", callback_data="ma_menu:schedule"),
        ],
    ])


def appointments_list_kb(appointments: list[dict]) -> InlineKeyboardMarkup:
    from utils.formatting import fmt_date, STATUS_LABELS
    rows = []
    for apt in appointments:
        label = (
            f"{fmt_date(apt['date'])} {apt['start_time']} "
            f"— {apt.get('service_title','?')} "
            f"[{STATUS_LABELS.get(apt['status'], apt['status'])}]"
        )
        rows.append([InlineKeyboardButton(text=label, callback_data=f"ma_apt:{apt['id']}")])
    if not rows:
        rows.append([InlineKeyboardButton(text="Записей нет", callback_data="ma_ignore")])
    rows.append([InlineKeyboardButton(text="🔙 В меню", callback_data="ma_menu:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def appointment_actions_kb(apt: dict) -> InlineKeyboardMarkup:
    rows = []
    if apt["status"] == "pending":
        rows.append([
            InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"ma_conf:{apt['id']}"),
            InlineKeyboardButton(text="❌ Отклонить",   callback_data=f"ma_decl:{apt['id']}"),
        ])
    if apt["status"] in ("pending", "confirmed"):
        rows.append([InlineKeyboardButton(
            text="🔁 Предложить перенос", callback_data=f"ma_res:{apt['id']}"
        )])
    rows.append([InlineKeyboardButton(text="🔙 Назад", callback_data="ma_back_list")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def blocks_list_kb(blocks: list[dict]) -> InlineKeyboardMarkup:
    rows = []
    for b in blocks:
        label = f"🗓 {b['date']} {b['start_time']}–{b['end_time']}"
        if b.get("reason"):
            label += f" ({b['reason']})"
        rows.append([InlineKeyboardButton(text=label, callback_data=f"ma_blkdel:{b['id']}")])
    rows.append([InlineKeyboardButton(text="➕ Добавить блокировку", callback_data="ma_blkadd")])
    rows.append([InlineKeyboardButton(text="🔙 В меню", callback_data="ma_menu:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def master_schedule_kb(rules: list[dict], allow_personal: bool) -> InlineKeyboardMarkup:
    from utils.formatting import WEEKDAY_SHORT
    rows = []
    if not allow_personal:
        rows.append([InlineKeyboardButton(
            text="⛔ Личное расписание не разрешено администратором",
            callback_data="ma_ignore",
        )])
        rows.append([InlineKeyboardButton(text="🔙 В меню", callback_data="ma_menu:back")])
        return InlineKeyboardMarkup(inline_keyboard=rows)
    existing = {r["weekday"]: r for r in rules}
    for wd in range(7):
        rule = existing.get(wd)
        if rule:
            label = f"{WEEKDAY_SHORT[wd]}: {rule['start_time']}–{rule['end_time']} (шаг {rule['slot_step_min']} мин)"
        else:
            label = f"{WEEKDAY_SHORT[wd]}: выходной"
        rows.append([InlineKeyboardButton(text=label, callback_data=f"ma_sched:{wd}")])
    rows.append([InlineKeyboardButton(text="🔙 В меню", callback_data="ma_menu:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def reschedule_slot_confirm_kb(apt_id: int, date_str: str, time_str: str) -> InlineKeyboardMarkup:
    compact = date_str.replace("-", "") + ":" + time_str.replace(":", "")
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text=f"✅ Предложить {date_str} {time_str}",
            callback_data=f"ma_rsconf:{apt_id}:{compact}",
        ),
        InlineKeyboardButton(text="❌ Отмена", callback_data=f"ma_apt:{apt_id}"),
    ]])
