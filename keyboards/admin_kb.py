from __future__ import annotations
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils.formatting import WEEKDAY_SHORT


def admin_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👩‍🎨 Мастера",        callback_data="ad_menu:masters"),
            InlineKeyboardButton(text="💅 Услуги",          callback_data="ad_menu:services"),
        ],
        [
            InlineKeyboardButton(text="🎚️ Мастер–услуга",   callback_data="ad_menu:ms"),
            InlineKeyboardButton(text="🗓️ Расписание",      callback_data="ad_menu:schedule"),
        ],
        [
            InlineKeyboardButton(text="🧱 Неполучать новые записи",      callback_data="ad_menu:blocks"),
            InlineKeyboardButton(text="📋 Записи",          callback_data="ad_menu:apts"),
        ],
        [
            InlineKeyboardButton(text="🧾 Экспорт CSV",     callback_data="ad_menu:csv"),
        ],
    ])


# ─────────────────── MASTERS ──────────────────────────────────

def masters_list_kb(masters: list[dict]) -> InlineKeyboardMarkup:
    rows = []
    for m in masters:
        status = "✅" if m["is_active"] else "⛔"
        rows.append([InlineKeyboardButton(
            text=f"{status} {m['display_name']} (tg:{m['tg_id']})",
            callback_data=f"ad_mst:{m['id']}",
        )])
    rows.append([InlineKeyboardButton(text="➕ Добавить мастера", callback_data="ad_mst_add")])
    rows.append([InlineKeyboardButton(text="🔙 В меню", callback_data="ad_menu:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def master_detail_kb(master: dict) -> InlineKeyboardMarkup:
    toggle = "⛔ Деактивировать" if master["is_active"] else "✅ Активировать"
    sched = "🕒 Запретить личн. расписание" if master["allow_personal_schedule"] else "🕒 Разрешить личн. расписание"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=toggle, callback_data=f"ad_mst_tog:{master['id']}")],
        [InlineKeyboardButton(text=sched,  callback_data=f"ad_mst_sched:{master['id']}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="ad_mst_list")],
    ])


# ─────────────────── SERVICES ─────────────────────────────────

def services_list_kb(services: list[dict]) -> InlineKeyboardMarkup:
    rows = []
    for s in services:
        status = "✅" if s["is_active"] else "⛔"
        rows.append([InlineKeyboardButton(
            text=f"{status} {s['title']} ({s['default_duration_min']} мин, {s['default_price_text']})",
            callback_data=f"ad_svc:{s['id']}",
        )])
    rows.append([InlineKeyboardButton(text="➕ Добавить услугу", callback_data="ad_svc_add")])
    rows.append([InlineKeyboardButton(text="🔙 В меню", callback_data="ad_menu:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def service_detail_kb(service: dict) -> InlineKeyboardMarkup:
    toggle = "⛔ Деактивировать" if service["is_active"] else "✅ Активировать"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Изменить название",     callback_data=f"ad_svc_ed_title:{service['id']}")],
        [InlineKeyboardButton(text="⏱️ Изменить длительность",  callback_data=f"ad_svc_ed_dur:{service['id']}")],
        [InlineKeyboardButton(text="💰 Изменить цену",          callback_data=f"ad_svc_ed_price:{service['id']}")],
        [InlineKeyboardButton(text=toggle,                      callback_data=f"ad_svc_tog:{service['id']}")],
        [InlineKeyboardButton(text="🔙 Назад",                  callback_data="ad_svc_list")],
    ])


# ─────────────────── MASTER–SERVICE OVERRIDES ─────────────────

def ms_masters_kb(masters: list[dict]) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(
        text=m["display_name"], callback_data=f"ad_ms_m:{m['id']}"
    )] for m in masters]
    rows.append([InlineKeyboardButton(text="🔙 В меню", callback_data="ad_menu:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def ms_services_kb(services: list[dict], master_id: int) -> InlineKeyboardMarkup:
    rows = []
    for s in services:
        rows.append([InlineKeyboardButton(
            text=f"{s['title']} ({s['default_duration_min']} мин)",
            callback_data=f"ad_ms_s:{master_id}:{s['id']}",
        )])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ─────────────────── WORK SCHEDULE ────────────────────────────

def schedule_kb(rules: list[dict]) -> InlineKeyboardMarkup:
    existing = {r["weekday"]: r for r in rules}
    rows = []
    for wd in range(7):
        rule = existing.get(wd)
        if rule:
            label = f"{WEEKDAY_SHORT[wd]}: {rule['start_time']}–{rule['end_time']} (шаг {rule['slot_step_min']} мин)"
        else:
            label = f"{WEEKDAY_SHORT[wd]}: выходной"
        rows.append([InlineKeyboardButton(text=label, callback_data=f"ad_sched_wd:{wd}")])
    rows.append([InlineKeyboardButton(text="🍽️ Перерывы", callback_data="ad_breaks_list")])
    rows.append([InlineKeyboardButton(text="🔙 В меню", callback_data="ad_menu:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def breaks_list_kb(breaks: list[dict]) -> InlineKeyboardMarkup:
    rows = []
    for b in breaks:
        label = f"{WEEKDAY_SHORT[b['weekday']]}: {b['start_time']}–{b['end_time']} ❌"
        rows.append([InlineKeyboardButton(text=label, callback_data=f"ad_break_del:{b['id']}")])
    rows.append([InlineKeyboardButton(text="➕ Добавить перерыв", callback_data="ad_break_add")])
    rows.append([InlineKeyboardButton(text="🔙 Назад", callback_data="ad_sched_back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ─────────────────── BLOCKS ───────────────────────────────────

def blocks_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌐 Общие блокировки",      callback_data="ad_blk_global")],
        [InlineKeyboardButton(text="👤 Блокировка по мастеру", callback_data="ad_blk_master")],
        [InlineKeyboardButton(text="🔙 В меню",                callback_data="ad_menu:back")],
    ])


def global_blocks_kb(blocks: list[dict]) -> InlineKeyboardMarkup:
    rows = []
    for b in blocks:
        label = f"🗓 {b['date']} {b['start_time']}–{b['end_time']}"
        if b.get("reason"):
            label += f" ({b['reason']})"
        label += " ❌"
        rows.append([InlineKeyboardButton(text=label, callback_data=f"ad_blk_del:{b['id']}")])
    rows.append([InlineKeyboardButton(text="➕ Добавить блокировку", callback_data="ad_blk_add:global")])
    rows.append([InlineKeyboardButton(text="🔙 Назад", callback_data="ad_blk_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def master_blocks_select_kb(masters: list[dict]) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(
        text=m["display_name"], callback_data=f"ad_blk_msel:{m['id']}"
    )] for m in masters]
    rows.append([InlineKeyboardButton(text="🔙 Назад", callback_data="ad_blk_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def master_blocks_kb(blocks: list[dict], master_id: int) -> InlineKeyboardMarkup:
    rows = []
    for b in blocks:
        label = f"🗓 {b['date']} {b['start_time']}–{b['end_time']}"
        if b.get("reason"):
            label += f" ({b['reason']})"
        label += " ❌"
        rows.append([InlineKeyboardButton(text=label, callback_data=f"ad_blk_del:{b['id']}")])
    rows.append([InlineKeyboardButton(
        text="➕ Добавить блокировку",
        callback_data=f"ad_blk_add:{master_id}",
    )])
    rows.append([InlineKeyboardButton(text="🔙 Назад", callback_data="ad_blk_master")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ─────────────────── APPOINTMENTS ─────────────────────────────

def appointments_filter_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📆 По дате",    callback_data="ad_apts_date")],
        [InlineKeyboardButton(text="👤 По мастеру", callback_data="ad_apts_master")],
        [InlineKeyboardButton(text="⏳ Все ожидающие", callback_data="ad_apts_pending")],
        [InlineKeyboardButton(text="🔙 В меню",     callback_data="ad_menu:back")],
    ])


def appointments_list_kb(appointments: list[dict]) -> InlineKeyboardMarkup:
    from utils.formatting import fmt_date, STATUS_LABELS
    rows = []
    for apt in appointments:
        label = (
            f"{fmt_date(apt['date'])} {apt['start_time']} "
            f"— {apt.get('master_display_name','?')} "
            f"— {apt.get('service_title','?')} "
            f"[{STATUS_LABELS.get(apt['status'], apt['status'])}]"
        )
        rows.append([InlineKeyboardButton(text=label, callback_data=f"ad_apt:{apt['id']}")])
    if not rows:
        rows.append([InlineKeyboardButton(text="Записей нет", callback_data="ad_ignore")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def apts_master_select_kb(masters: list[dict]) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(
        text=m["display_name"], callback_data=f"ad_apts_m:{m['id']}"
    )] for m in masters]
    return InlineKeyboardMarkup(inline_keyboard=rows)
