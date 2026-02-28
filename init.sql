PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tg_id INTEGER UNIQUE NOT NULL,
    username TEXT,
    full_name TEXT,
    phone TEXT,
    role TEXT DEFAULT 'client',
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS masters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE NOT NULL REFERENCES users(id),
    display_name TEXT NOT NULL,
    is_active INTEGER DEFAULT 1,
    allow_personal_schedule INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS services (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    default_duration_min INTEGER NOT NULL DEFAULT 60,
    default_price_text TEXT DEFAULT '',
    is_active INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS master_services (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    master_id INTEGER NOT NULL REFERENCES masters(id),
    service_id INTEGER NOT NULL REFERENCES services(id),
    duration_min INTEGER,
    price_text TEXT,
    is_active INTEGER DEFAULT 1,
    UNIQUE(master_id, service_id)
);

CREATE TABLE IF NOT EXISTS work_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    weekday INTEGER NOT NULL UNIQUE,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    slot_step_min INTEGER DEFAULT 30
);

CREATE TABLE IF NOT EXISTS breaks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    weekday INTEGER NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS master_work_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    master_id INTEGER NOT NULL REFERENCES masters(id),
    weekday INTEGER NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    slot_step_min INTEGER DEFAULT 30,
    UNIQUE(master_id, weekday)
);

CREATE TABLE IF NOT EXISTS master_breaks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    master_id INTEGER NOT NULL REFERENCES masters(id),
    weekday INTEGER NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS blocks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    master_id INTEGER REFERENCES masters(id),
    date TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    reason TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS appointments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL REFERENCES users(id),
    master_id INTEGER NOT NULL REFERENCES masters(id),
    service_id INTEGER NOT NULL REFERENCES services(id),
    date TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    comment TEXT DEFAULT '',
    client_name TEXT DEFAULT '',
    client_phone TEXT DEFAULT '',
    proposed_date TEXT,
    proposed_start_time TEXT,
    proposed_end_time TEXT,
    status_before_reschedule TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(master_id, date, start_time)
);

CREATE TABLE IF NOT EXISTS fsm_data (
    storage_key TEXT PRIMARY KEY,
    state TEXT,
    data TEXT DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_appointments_master_date ON appointments(master_id, date);
CREATE INDEX IF NOT EXISTS idx_appointments_client ON appointments(client_id);
CREATE INDEX IF NOT EXISTS idx_appointments_status ON appointments(status);
CREATE INDEX IF NOT EXISTS idx_blocks_date ON blocks(date);

-- ============================================================
-- Тестовые данные: 5 услуг
-- ============================================================
INSERT OR IGNORE INTO services (id, title, default_duration_min, default_price_text, is_active) VALUES
(1, 'Маникюр',            60,  '1 500 ₽', 1),
(2, 'Педикюр',            90,  '2 000 ₽', 1),
(3, 'Покрытие гель-лак',  45,  '800 ₽',   1),
(4, 'Дизайн ногтей',      120, '2 500 ₽', 1),
(5, 'Снятие покрытия',    30,  '500 ₽',   1);

-- Базовое расписание Пн–Сб 09:00–19:00, шаг 30 мин (0=Пн … 5=Сб)
INSERT OR IGNORE INTO work_rules (weekday, start_time, end_time, slot_step_min) VALUES
(0, '09:00', '19:00', 30),
(1, '09:00', '19:00', 30),
(2, '09:00', '19:00', 30),
(3, '09:00', '19:00', 30),
(4, '09:00', '19:00', 30),
(5, '09:00', '19:00', 30);

-- Обед Пн–Сб 13:00–14:00
INSERT OR IGNORE INTO breaks (weekday, start_time, end_time) VALUES
(0, '13:00', '14:00'),
(1, '13:00', '14:00'),
(2, '13:00', '14:00'),
(3, '13:00', '14:00'),
(4, '13:00', '14:00'),
(5, '13:00', '14:00');
