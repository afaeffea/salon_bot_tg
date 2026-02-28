"""
Inline calendar keyboard builder.
"""
from __future__ import annotations
import calendar
from datetime import date, timedelta

import pytz
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import settings

WEEKDAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
MONTHS_RU = {
    1: "Январь", 2: "Февраль", 3: "Март", 4: "Апрель",
    5: "Май", 6: "Июнь", 7: "Июль", 8: "Август",
    9: "Сентябрь", 10: "Октябрь", 11: "Ноябрь", 12: "Декабрь",
}


def build_calendar(
    year: int,
    month: int,
    prefix: str = "cal",
    extra: str = "",
) -> InlineKeyboardMarkup:
    """
    prefix  – callback prefix, e.g. 'cal' or 'mres'
    extra   – appended as last part of callback (e.g. appointment id)
    Callback format:  {prefix}:{action}:{year}:{month}:{day}[:{extra}]
    """
    tz = pytz.timezone(settings.TIMEZONE)
    today = date.today()
    max_date = today + timedelta(days=30)

    def cb(action: str, y: int = 0, m: int = 0, d: int = 0) -> str:
        base = f"{prefix}:{action}:{y}:{m}:{d}"
        return f"{base}:{extra}" if extra else base

    # Navigation
    py, pm = (year, month - 1) if month > 1 else (year - 1, 12)
    ny, nm = (year, month + 1) if month < 12 else (year + 1, 1)

    rows = [
        [
            InlineKeyboardButton(text="◀", callback_data=cb("prev", py, pm)),
            InlineKeyboardButton(
                text=f"{MONTHS_RU[month]} {year}",
                callback_data=cb("ignore"),
            ),
            InlineKeyboardButton(text="▶", callback_data=cb("next", ny, nm)),
        ],
        [InlineKeyboardButton(text=d, callback_data=cb("ignore")) for d in WEEKDAYS],
    ]

    for week in calendar.monthcalendar(year, month):
        row = []
        for day in week:
            if day == 0:
                row.append(InlineKeyboardButton(text=" ", callback_data=cb("ignore")))
            else:
                d = date(year, month, day)
                if d < today or d > max_date:
                    row.append(InlineKeyboardButton(text="·", callback_data=cb("ignore")))
                else:
                    row.append(
                        InlineKeyboardButton(
                            text=str(day),
                            callback_data=cb("day", year, month, day),
                        )
                    )
        rows.append(row)

    return InlineKeyboardMarkup(inline_keyboard=rows)


def current_ym() -> tuple[int, int]:
    """Return (year, month) in the configured timezone."""
    tz = pytz.timezone(settings.TIMEZONE)
    from datetime import datetime
    now = datetime.now(tz)
    return now.year, now.month
