"""
All database operations.
Every function receives `db: aiosqlite.Connection` as first argument.
Rows are returned as plain dicts.
"""
from __future__ import annotations
import aiosqlite
from typing import Any


def _row(row) -> dict | None:
    return dict(row) if row else None


def _rows(rows) -> list[dict]:
    return [dict(r) for r in rows]


# ─────────────────────────── USERS ───────────────────────────

async def get_user_by_tg_id(db: aiosqlite.Connection, tg_id: int) -> dict | None:
    cur = await db.execute("SELECT * FROM users WHERE tg_id = ?", (tg_id,))
    return _row(await cur.fetchone())


async def get_user_by_id(db: aiosqlite.Connection, user_id: int) -> dict | None:
    cur = await db.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return _row(await cur.fetchone())


async def get_user_by_username(db: aiosqlite.Connection, username: str) -> dict | None:
    cur = await db.execute(
        "SELECT * FROM users WHERE LOWER(username) = LOWER(?)", (username.lstrip("@"),)
    )
    return _row(await cur.fetchone())


async def get_or_create_user(
    db: aiosqlite.Connection, tg_id: int, username: str | None, full_name: str | None
) -> dict:
    # INSERT OR IGNORE avoids UNIQUE race; then always refresh profile fields
    await db.execute(
        "INSERT OR IGNORE INTO users (tg_id, username, full_name) VALUES (?, ?, ?)",
        (tg_id, username, full_name),
    )
    await db.execute(
        "UPDATE users SET username=?, full_name=? WHERE tg_id=?",
        (username, full_name, tg_id),
    )
    await db.commit()
    return await get_user_by_tg_id(db, tg_id)


async def update_user_phone(db: aiosqlite.Connection, user_id: int, phone: str):
    await db.execute("UPDATE users SET phone=? WHERE id=?", (phone, user_id))
    await db.commit()


async def update_user_name(db: aiosqlite.Connection, user_id: int, name: str):
    await db.execute("UPDATE users SET full_name=? WHERE id=?", (name, user_id))
    await db.commit()


# ─────────────────────────── MASTERS ──────────────────────────

async def get_master_by_id(db: aiosqlite.Connection, master_id: int) -> dict | None:
    cur = await db.execute(
        """SELECT m.*, u.tg_id, u.username, u.full_name, u.phone
           FROM masters m JOIN users u ON m.user_id = u.id
           WHERE m.id = ?""",
        (master_id,),
    )
    return _row(await cur.fetchone())


async def get_master_by_user_id(db: aiosqlite.Connection, user_id: int) -> dict | None:
    cur = await db.execute(
        """SELECT m.*, u.tg_id, u.username, u.full_name, u.phone
           FROM masters m JOIN users u ON m.user_id = u.id
           WHERE m.user_id = ?""",
        (user_id,),
    )
    return _row(await cur.fetchone())


async def get_master_by_tg_id(db: aiosqlite.Connection, tg_id: int) -> dict | None:
    cur = await db.execute(
        """SELECT m.*, u.tg_id, u.username, u.full_name, u.phone
           FROM masters m JOIN users u ON m.user_id = u.id
           WHERE u.tg_id = ?""",
        (tg_id,),
    )
    return _row(await cur.fetchone())


async def get_all_masters(db: aiosqlite.Connection, active_only: bool = False) -> list[dict]:
    q = """SELECT m.*, u.tg_id, u.username, u.full_name, u.phone
           FROM masters m JOIN users u ON m.user_id = u.id"""
    if active_only:
        q += " WHERE m.is_active = 1"
    q += " ORDER BY m.display_name"
    cur = await db.execute(q)
    return _rows(await cur.fetchall())


async def get_masters_for_service(
    db: aiosqlite.Connection, service_id: int, active_only: bool = True
) -> list[dict]:
    """Return masters that have this service active (or default active)."""
    cur = await db.execute(
        """SELECT m.*, u.tg_id, u.username, u.full_name, u.phone,
                  COALESCE(ms.duration_min, s.default_duration_min) AS eff_duration,
                  COALESCE(ms.price_text,  s.default_price_text)    AS eff_price,
                  COALESCE(ms.is_active, 1)                          AS ms_active
           FROM masters m
           JOIN users u ON m.user_id = u.id
           JOIN services s ON s.id = ?
           LEFT JOIN master_services ms ON ms.master_id = m.id AND ms.service_id = s.id
           WHERE m.is_active = 1 AND COALESCE(ms.is_active, 1) = 1
           ORDER BY m.display_name""",
        (service_id,),
    )
    return _rows(await cur.fetchall())


async def create_master(
    db: aiosqlite.Connection, user_id: int, display_name: str
) -> dict:
    cur = await db.execute(
        "INSERT INTO masters (user_id, display_name) VALUES (?, ?)",
        (user_id, display_name),
    )
    await db.commit()
    return await get_master_by_id(db, cur.lastrowid)


async def update_master(db: aiosqlite.Connection, master_id: int, **kwargs):
    sets = ", ".join(f"{k}=?" for k in kwargs)
    await db.execute(
        f"UPDATE masters SET {sets} WHERE id=?", (*kwargs.values(), master_id)
    )
    await db.commit()


# ─────────────────────────── SERVICES ─────────────────────────

async def get_service_by_id(db: aiosqlite.Connection, service_id: int) -> dict | None:
    cur = await db.execute("SELECT * FROM services WHERE id = ?", (service_id,))
    return _row(await cur.fetchone())


async def get_all_services(db: aiosqlite.Connection, active_only: bool = True) -> list[dict]:
    q = "SELECT * FROM services"
    if active_only:
        q += " WHERE is_active = 1"
    q += " ORDER BY title"
    cur = await db.execute(q)
    return _rows(await cur.fetchall())


async def create_service(
    db: aiosqlite.Connection, title: str, duration: int, price: str
) -> dict:
    cur = await db.execute(
        "INSERT INTO services (title, default_duration_min, default_price_text) VALUES (?, ?, ?)",
        (title, duration, price),
    )
    await db.commit()
    return await get_service_by_id(db, cur.lastrowid)


async def update_service(db: aiosqlite.Connection, service_id: int, **kwargs):
    sets = ", ".join(f"{k}=?" for k in kwargs)
    await db.execute(
        f"UPDATE services SET {sets} WHERE id=?", (*kwargs.values(), service_id)
    )
    await db.commit()


# ─────────────────────── MASTER SERVICES ──────────────────────

async def get_master_service(
    db: aiosqlite.Connection, master_id: int, service_id: int
) -> dict | None:
    cur = await db.execute(
        "SELECT * FROM master_services WHERE master_id=? AND service_id=?",
        (master_id, service_id),
    )
    return _row(await cur.fetchone())


async def upsert_master_service(
    db: aiosqlite.Connection,
    master_id: int,
    service_id: int,
    duration_min: int | None,
    price_text: str | None,
    is_active: int = 1,
):
    await db.execute(
        """INSERT INTO master_services (master_id, service_id, duration_min, price_text, is_active)
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT(master_id, service_id)
           DO UPDATE SET duration_min=excluded.duration_min,
                         price_text=excluded.price_text,
                         is_active=excluded.is_active""",
        (master_id, service_id, duration_min, price_text, is_active),
    )
    await db.commit()


async def get_services_for_master(
    db: aiosqlite.Connection, master_id: int, active_only: bool = True
) -> list[dict]:
    cur = await db.execute(
        """SELECT s.*,
                  COALESCE(ms.duration_min, s.default_duration_min) AS eff_duration,
                  COALESCE(ms.price_text,  s.default_price_text)    AS eff_price,
                  COALESCE(ms.is_active, 1)                          AS ms_active
           FROM services s
           LEFT JOIN master_services ms ON ms.master_id=? AND ms.service_id=s.id
           WHERE s.is_active=1 AND COALESCE(ms.is_active, 1)=1
           ORDER BY s.title""",
        (master_id,),
    )
    return _rows(await cur.fetchall())


async def get_effective_duration(
    db: aiosqlite.Connection, master_id: int, service_id: int
) -> int:
    cur = await db.execute(
        """SELECT COALESCE(ms.duration_min, s.default_duration_min) AS dur
           FROM services s
           LEFT JOIN master_services ms ON ms.master_id=? AND ms.service_id=s.id
           WHERE s.id=?""",
        (master_id, service_id),
    )
    row = await cur.fetchone()
    return row["dur"] if row else 60


async def get_effective_price(
    db: aiosqlite.Connection, master_id: int, service_id: int
) -> str:
    cur = await db.execute(
        """SELECT COALESCE(ms.price_text, s.default_price_text) AS pr
           FROM services s
           LEFT JOIN master_services ms ON ms.master_id=? AND ms.service_id=s.id
           WHERE s.id=?""",
        (master_id, service_id),
    )
    row = await cur.fetchone()
    return row["pr"] if row else ""


# ─────────────────────── WORK RULES ───────────────────────────

async def get_work_rule(db: aiosqlite.Connection, weekday: int) -> dict | None:
    cur = await db.execute("SELECT * FROM work_rules WHERE weekday=?", (weekday,))
    return _row(await cur.fetchone())


async def get_all_work_rules(db: aiosqlite.Connection) -> list[dict]:
    cur = await db.execute("SELECT * FROM work_rules ORDER BY weekday")
    return _rows(await cur.fetchall())


async def upsert_work_rule(
    db: aiosqlite.Connection,
    weekday: int,
    start: str,
    end: str,
    step: int,
):
    await db.execute(
        """INSERT INTO work_rules (weekday, start_time, end_time, slot_step_min) VALUES (?,?,?,?)
           ON CONFLICT(weekday) DO UPDATE SET start_time=excluded.start_time,
               end_time=excluded.end_time, slot_step_min=excluded.slot_step_min""",
        (weekday, start, end, step),
    )
    await db.commit()


async def delete_work_rule(db: aiosqlite.Connection, weekday: int):
    await db.execute("DELETE FROM work_rules WHERE weekday=?", (weekday,))
    await db.commit()


# ─────────────────────────── BREAKS ───────────────────────────

async def get_breaks(db: aiosqlite.Connection, weekday: int) -> list[dict]:
    cur = await db.execute("SELECT * FROM breaks WHERE weekday=? ORDER BY start_time", (weekday,))
    return _rows(await cur.fetchall())


async def get_all_breaks(db: aiosqlite.Connection) -> list[dict]:
    cur = await db.execute("SELECT * FROM breaks ORDER BY weekday, start_time")
    return _rows(await cur.fetchall())


async def add_break(db: aiosqlite.Connection, weekday: int, start: str, end: str):
    await db.execute(
        "INSERT INTO breaks (weekday, start_time, end_time) VALUES (?,?,?)",
        (weekday, start, end),
    )
    await db.commit()


async def delete_break(db: aiosqlite.Connection, break_id: int):
    await db.execute("DELETE FROM breaks WHERE id=?", (break_id,))
    await db.commit()


# ─────────────────── MASTER WORK RULES ────────────────────────

async def get_master_work_rule(
    db: aiosqlite.Connection, master_id: int, weekday: int
) -> dict | None:
    cur = await db.execute(
        "SELECT * FROM master_work_rules WHERE master_id=? AND weekday=?",
        (master_id, weekday),
    )
    return _row(await cur.fetchone())


async def get_all_master_work_rules(
    db: aiosqlite.Connection, master_id: int
) -> list[dict]:
    cur = await db.execute(
        "SELECT * FROM master_work_rules WHERE master_id=? ORDER BY weekday",
        (master_id,),
    )
    return _rows(await cur.fetchall())


async def upsert_master_work_rule(
    db: aiosqlite.Connection,
    master_id: int,
    weekday: int,
    start: str,
    end: str,
    step: int,
):
    await db.execute(
        """INSERT INTO master_work_rules (master_id, weekday, start_time, end_time, slot_step_min)
           VALUES (?,?,?,?,?)
           ON CONFLICT(master_id, weekday)
           DO UPDATE SET start_time=excluded.start_time,
                         end_time=excluded.end_time,
                         slot_step_min=excluded.slot_step_min""",
        (master_id, weekday, start, end, step),
    )
    await db.commit()


async def delete_master_work_rule(
    db: aiosqlite.Connection, master_id: int, weekday: int
):
    await db.execute(
        "DELETE FROM master_work_rules WHERE master_id=? AND weekday=?",
        (master_id, weekday),
    )
    await db.commit()


# ─────────────────── MASTER BREAKS ────────────────────────────

async def get_master_breaks(
    db: aiosqlite.Connection, master_id: int, weekday: int
) -> list[dict]:
    cur = await db.execute(
        "SELECT * FROM master_breaks WHERE master_id=? AND weekday=? ORDER BY start_time",
        (master_id, weekday),
    )
    return _rows(await cur.fetchall())


async def add_master_break(
    db: aiosqlite.Connection, master_id: int, weekday: int, start: str, end: str
):
    await db.execute(
        "INSERT INTO master_breaks (master_id, weekday, start_time, end_time) VALUES (?,?,?,?)",
        (master_id, weekday, start, end),
    )
    await db.commit()


async def delete_master_break(db: aiosqlite.Connection, break_id: int):
    await db.execute("DELETE FROM master_breaks WHERE id=?", (break_id,))
    await db.commit()


# ─────────────────────────── BLOCKS ───────────────────────────

async def get_blocks_for_date(
    db: aiosqlite.Connection, date_str: str, master_id: int | None = None
) -> list[dict]:
    """Return global blocks + master-specific blocks for the given date."""
    cur = await db.execute(
        "SELECT * FROM blocks WHERE date=? AND (master_id IS NULL OR master_id=?) ORDER BY start_time",
        (date_str, master_id),
    )
    return _rows(await cur.fetchall())


async def get_all_blocks(
    db: aiosqlite.Connection, master_id: int | None = None
) -> list[dict]:
    if master_id is None:
        cur = await db.execute(
            "SELECT * FROM blocks WHERE master_id IS NULL ORDER BY date, start_time"
        )
    else:
        cur = await db.execute(
            "SELECT * FROM blocks WHERE master_id=? ORDER BY date, start_time",
            (master_id,),
        )
    return _rows(await cur.fetchall())


async def add_block(
    db: aiosqlite.Connection,
    date_str: str,
    start: str,
    end: str,
    reason: str = "",
    master_id: int | None = None,
) -> dict:
    cur = await db.execute(
        "INSERT INTO blocks (master_id, date, start_time, end_time, reason) VALUES (?,?,?,?,?)",
        (master_id, date_str, start, end, reason),
    )
    await db.commit()
    c2 = await db.execute("SELECT * FROM blocks WHERE id=?", (cur.lastrowid,))
    return _row(await c2.fetchone())


async def delete_block(db: aiosqlite.Connection, block_id: int):
    await db.execute("DELETE FROM blocks WHERE id=?", (block_id,))
    await db.commit()


# ──────────────────────── APPOINTMENTS ────────────────────────

async def get_appointment_by_id(
    db: aiosqlite.Connection, apt_id: int
) -> dict | None:
    cur = await db.execute(
        """SELECT a.*,
                  u.tg_id  AS client_tg_id,
                  u.full_name AS client_full_name,
                  u.username  AS client_username,
                  m.display_name AS master_display_name,
                  mu.tg_id AS master_tg_id,
                  s.title  AS service_title
           FROM appointments a
           JOIN users u   ON a.client_id  = u.id
           JOIN masters m ON a.master_id  = m.id
           JOIN users mu  ON m.user_id    = mu.id
           JOIN services s ON a.service_id = s.id
           WHERE a.id=?""",
        (apt_id,),
    )
    return _row(await cur.fetchone())


async def get_appointments_for_client(
    db: aiosqlite.Connection, client_id: int
) -> list[dict]:
    cur = await db.execute(
        """SELECT a.*,
                  m.display_name AS master_display_name,
                  s.title        AS service_title
           FROM appointments a
           JOIN masters m  ON a.master_id  = m.id
           JOIN services s ON a.service_id = s.id
           WHERE a.client_id=? AND a.status NOT IN ('cancelled','declined','rescheduled')
           ORDER BY a.date DESC, a.start_time""",
        (client_id,),
    )
    return _rows(await cur.fetchall())


async def get_appointments_for_master(
    db: aiosqlite.Connection,
    master_id: int,
    date_str: str | None = None,
    status_filter: list | None = None,
) -> list[dict]:
    q = """SELECT a.*,
                  u.tg_id   AS client_tg_id,
                  u.full_name AS client_full_name,
                  u.username  AS client_username,
                  s.title    AS service_title
           FROM appointments a
           JOIN users u   ON a.client_id  = u.id
           JOIN services s ON a.service_id = s.id
           WHERE a.master_id=?"""
    params: list[Any] = [master_id]
    if date_str:
        q += " AND a.date=?"
        params.append(date_str)
    if status_filter:
        placeholders = ",".join("?" * len(status_filter))
        q += f" AND a.status IN ({placeholders})"
        params.extend(status_filter)
    q += " ORDER BY a.date, a.start_time"
    cur = await db.execute(q, params)
    return _rows(await cur.fetchall())


async def get_active_appointments_for_master_on_date(
    db: aiosqlite.Connection, master_id: int, date_str: str
) -> list[dict]:
    cur = await db.execute(
        """SELECT id, start_time, end_time FROM appointments
           WHERE master_id=? AND date=? AND status IN ('pending','confirmed','reschedule_offered')""",
        (master_id, date_str),
    )
    return _rows(await cur.fetchall())


async def create_appointment(
    db: aiosqlite.Connection,
    client_id: int,
    master_id: int,
    service_id: int,
    date_str: str,
    start_time: str,
    end_time: str,
    client_name: str,
    client_phone: str,
) -> tuple[dict | None, str]:
    """
    Returns (appointment_dict, 'ok') or (None, 'overlap') or (None, 'error').
    Uses BEGIN IMMEDIATE to serialize concurrent writes.
    """
    try:
        await db.execute("BEGIN IMMEDIATE")
        # Check overlap
        cur = await db.execute(
            """SELECT id FROM appointments
               WHERE master_id=? AND date=?
                 AND status IN ('pending','confirmed','reschedule_offered')
                 AND start_time < ? AND end_time > ?""",
            (master_id, date_str, end_time, start_time),
        )
        if await cur.fetchone():
            await db.execute("ROLLBACK")
            return None, "overlap"
        cur2 = await db.execute(
            """INSERT INTO appointments
               (client_id, master_id, service_id, date, start_time, end_time, client_name, client_phone)
               VALUES (?,?,?,?,?,?,?,?)""",
            (client_id, master_id, service_id, date_str, start_time, end_time, client_name, client_phone),
        )
        await db.commit()
        apt = await get_appointment_by_id(db, cur2.lastrowid)
        return apt, "ok"
    except Exception as exc:
        try:
            await db.execute("ROLLBACK")
        except Exception:
            pass
        return None, str(exc)


async def update_appointment_status(
    db: aiosqlite.Connection, apt_id: int, status: str
):
    await db.execute("UPDATE appointments SET status=? WHERE id=?", (status, apt_id))
    await db.commit()


async def offer_reschedule(
    db: aiosqlite.Connection,
    apt_id: int,
    proposed_date: str,
    proposed_start: str,
    proposed_end: str,
):
    cur = await db.execute("SELECT status FROM appointments WHERE id=?", (apt_id,))
    row = await cur.fetchone()
    prev = row["status"] if row else "pending"
    await db.execute(
        """UPDATE appointments
           SET status='reschedule_offered',
               status_before_reschedule=?,
               proposed_date=?,
               proposed_start_time=?,
               proposed_end_time=?
           WHERE id=?""",
        (prev, proposed_date, proposed_start, proposed_end, apt_id),
    )
    await db.commit()


async def accept_reschedule(
    db: aiosqlite.Connection, apt_id: int
) -> dict | None:
    """
    Creates a new confirmed appointment from the proposed slot.
    Marks original as 'rescheduled'.
    Returns the new appointment dict.
    """
    old = await get_appointment_by_id(db, apt_id)
    if not old or not old.get("proposed_date"):
        return None
    try:
        await db.execute("BEGIN IMMEDIATE")
        # Overlap check for proposed slot
        cur = await db.execute(
            """SELECT id FROM appointments
               WHERE master_id=? AND date=?
                 AND status IN ('pending','confirmed','reschedule_offered')
                 AND start_time < ? AND end_time > ?
                 AND id != ?""",
            (
                old["master_id"],
                old["proposed_date"],
                old["proposed_end_time"],
                old["proposed_start_time"],
                apt_id,
            ),
        )
        if await cur.fetchone():
            await db.execute("ROLLBACK")
            return None
        cur2 = await db.execute(
            """INSERT INTO appointments
               (client_id, master_id, service_id, date, start_time, end_time,
                client_name, client_phone, status)
               VALUES (?,?,?,?,?,?,?,?,'confirmed')""",
            (
                old["client_id"],
                old["master_id"],
                old["service_id"],
                old["proposed_date"],
                old["proposed_start_time"],
                old["proposed_end_time"],
                old["client_name"],
                old["client_phone"],
            ),
        )
        new_id = cur2.lastrowid
        await db.execute(
            "UPDATE appointments SET status='rescheduled' WHERE id=?", (apt_id,)
        )
        await db.commit()
        return await get_appointment_by_id(db, new_id)
    except Exception:
        try:
            await db.execute("ROLLBACK")
        except Exception:
            pass
        return None


async def decline_reschedule(db: aiosqlite.Connection, apt_id: int):
    cur = await db.execute(
        "SELECT status_before_reschedule FROM appointments WHERE id=?", (apt_id,)
    )
    row = await cur.fetchone()
    prev = (row["status_before_reschedule"] if row and row["status_before_reschedule"] else "declined")
    if prev == "confirmed":
        new_status = "confirmed"
    else:
        new_status = "declined"
    await db.execute(
        """UPDATE appointments
           SET status=?,
               proposed_date=NULL,
               proposed_start_time=NULL,
               proposed_end_time=NULL,
               status_before_reschedule=NULL
           WHERE id=?""",
        (new_status, apt_id),
    )
    await db.commit()


async def cancel_appointment(db: aiosqlite.Connection, apt_id: int):
    await db.execute(
        "UPDATE appointments SET status='cancelled' WHERE id=?", (apt_id,)
    )
    await db.commit()


async def get_all_appointments(db: aiosqlite.Connection) -> list[dict]:
    cur = await db.execute(
        """SELECT a.*,
                  u.full_name    AS client_full_name,
                  u.phone        AS client_phone_u,
                  m.display_name AS master_display_name,
                  s.title        AS service_title
           FROM appointments a
           JOIN users u   ON a.client_id  = u.id
           JOIN masters m ON a.master_id  = m.id
           JOIN services s ON a.service_id = s.id
           ORDER BY a.date, a.start_time"""
    )
    return _rows(await cur.fetchall())


async def get_pending_appointments(db: aiosqlite.Connection) -> list[dict]:
    cur = await db.execute(
        """SELECT a.*,
                  u.full_name    AS client_full_name,
                  m.display_name AS master_display_name,
                  s.title        AS service_title
           FROM appointments a
           JOIN users u   ON a.client_id  = u.id
           JOIN masters m ON a.master_id  = m.id
           JOIN services s ON a.service_id = s.id
           WHERE a.status='pending'
           ORDER BY a.date, a.start_time"""
    )
    return _rows(await cur.fetchall())


async def get_appointments_by_date(
    db: aiosqlite.Connection, date_str: str
) -> list[dict]:
    cur = await db.execute(
        """SELECT a.*,
                  u.full_name    AS client_full_name,
                  m.display_name AS master_display_name,
                  s.title        AS service_title
           FROM appointments a
           JOIN users u   ON a.client_id  = u.id
           JOIN masters m ON a.master_id  = m.id
           JOIN services s ON a.service_id = s.id
           WHERE a.date=?
           ORDER BY a.start_time""",
        (date_str,),
    )
    return _rows(await cur.fetchall())
