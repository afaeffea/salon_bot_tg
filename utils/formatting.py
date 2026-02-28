from __future__ import annotations
"""
Helper functions for formatting messages.
"""
from datetime import date

WEEKDAY_RU = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
WEEKDAY_SHORT = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
MONTHS_GEN = {
    1: "января", 2: "февраля", 3: "марта", 4: "апреля",
    5: "мая", 6: "июня", 7: "июля", 8: "августа",
    9: "сентября", 10: "октября", 11: "ноября", 12: "декабря",
}

STATUS_LABELS = {
    "pending":            "⏳ Ожидает подтверждения",
    "confirmed":          "✅ Подтверждена",
    "declined":           "❌ Отклонена",
    "cancelled":          "🚫 Отменена",
    "reschedule_offered": "🔁 Предложен перенос",
    "rescheduled":        "📆 Перенесена",
}


def fmt_date(date_str: str) -> str:
    """'2024-03-15' → '15 марта (Пт)'"""
    d = date.fromisoformat(date_str)
    return f"{d.day} {MONTHS_GEN[d.month]} ({WEEKDAY_SHORT[d.weekday()]})"


def fmt_appointment(apt: dict, show_client: bool = False, show_master: bool = False) -> str:
    lines = [
        f"📅 {fmt_date(apt['date'])}  🕐 {apt['start_time']}–{apt['end_time']}",
        f"💅 {apt.get('service_title', '—')}",
    ]
    if show_master:
        lines.append(f"👤 Мастер: {apt.get('master_display_name', '—')}")
    if show_client:
        name = apt.get('client_name') or apt.get('client_full_name') or '—'
        phone = apt.get('client_phone') or '—'
        lines.append(f"👤 Клиент: {name}  📞 {phone}")
    lines.append(f"Статус: {STATUS_LABELS.get(apt['status'], apt['status'])}")
    return "\n".join(lines)


def fmt_time_range(start: str, end: str) -> str:
    return f"{start}–{end}"
