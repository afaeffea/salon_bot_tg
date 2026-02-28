"""
Free-slot calculation.
"""
from __future__ import annotations
from datetime import datetime, date as date_type

import pytz

from config import settings


def t2m(t: str) -> int:
    """HH:MM → minutes from midnight."""
    h, m = map(int, t.split(":"))
    return h * 60 + m


def m2t(m: int) -> str:
    """Minutes from midnight → HH:MM."""
    return f"{m // 60:02d}:{m % 60:02d}"


def overlaps(s1: str, e1: str, s2: str, e2: str) -> bool:
    """True if [s1,e1) and [s2,e2) overlap."""
    return t2m(s1) < t2m(e2) and t2m(s2) < t2m(e1)


async def compute_free_slots(
    master_id: int,
    service_duration: int,
    date_str: str,
    exclude_apt_id: int | None = None,
) -> list[str]:
    """
    Returns list of HH:MM start times that are free for the given master
    to perform a service of `service_duration` minutes on `date_str`.
    """
    from db import repositories as repo
    from db.database import get_db

    db = await get_db()
    date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
    weekday = date_obj.weekday()  # 0=Mon … 6=Sun

    master = await repo.get_master_by_id(db, master_id)
    if not master:
        return []

    # ── Work rule ────────────────────────────────────────────
    work_rule = None
    if master["allow_personal_schedule"]:
        work_rule = await repo.get_master_work_rule(db, master_id, weekday)
    if not work_rule:
        work_rule = await repo.get_work_rule(db, weekday)
    if not work_rule:
        return []  # day off

    # ── Breaks ───────────────────────────────────────────────
    breaks = []
    if master["allow_personal_schedule"]:
        breaks = await repo.get_master_breaks(db, master_id, weekday)
    if not breaks:
        breaks = await repo.get_breaks(db, weekday)

    # ── Blocks (global + master-specific) ────────────────────
    blocks = await repo.get_blocks_for_date(db, date_str, master_id)

    # ── Existing active appointments ──────────────────────────
    appointments = await repo.get_active_appointments_for_master_on_date(db, master_id, date_str)
    if exclude_apt_id:
        appointments = [a for a in appointments if a["id"] != exclude_apt_id]

    start_m = t2m(work_rule["start_time"])
    end_m = t2m(work_rule["end_time"])
    step = work_rule["slot_step_min"]

    slots: list[str] = []
    t = start_m
    while t + service_duration <= end_m:
        slot_s = m2t(t)
        slot_e = m2t(t + service_duration)

        if not any(overlaps(slot_s, slot_e, b["start_time"], b["end_time"]) for b in breaks):
            if not any(overlaps(slot_s, slot_e, b["start_time"], b["end_time"]) for b in blocks):
                if not any(overlaps(slot_s, slot_e, a["start_time"], a["end_time"]) for a in appointments):
                    slots.append(slot_s)
        t += step

    # Filter past slots when date is today
    tz = pytz.timezone(settings.TIMEZONE)
    now = datetime.now(tz)
    if date_obj == now.date():
        cutoff = now.hour * 60 + now.minute + 30  # 30-min buffer
        slots = [s for s in slots if t2m(s) >= cutoff]

    return slots
