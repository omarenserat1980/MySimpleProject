PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS vehicle_profile (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    make TEXT NOT NULL DEFAULT 'Honda',
    model TEXT NOT NULL DEFAULT 'e:NP1',
    model_year INTEGER,
    vin TEXT,
    purchase_condition TEXT NOT NULL DEFAULT 'new',
    purchase_country TEXT NOT NULL DEFAULT 'Jordan',
    market_origin TEXT NOT NULL DEFAULT 'China-market import',
    manufacturer_hypothesis TEXT,
    manufacturer_confidence TEXT NOT NULL DEFAULT 'unverified',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS head_unit (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    software_version TEXT,
    manufacturer TEXT,
    hardware_model TEXT,
    operating_system TEXT,
    connectivity_module TEXT,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS device_profile (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    phone_model TEXT,
    android_version TEXT,
    carlife_app TEXT,
    carlife_version TEXT,
    usb_data_port_confirmed INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS observations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('confirmed','observed','failed','unknown','hypothesis')),
    detail TEXT NOT NULL,
    source TEXT,
    observed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS goals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    goal_key TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    priority INTEGER NOT NULL DEFAULT 100,
    status TEXT NOT NULL DEFAULT 'active',
    acceptance_criteria TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS blockers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    blocker_key TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    detail TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    safe_next_step TEXT,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS compatibility_checks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    component TEXT NOT NULL,
    capability TEXT NOT NULL,
    result TEXT NOT NULL CHECK (result IN ('supported','unsupported','partial','not_tested','unknown')),
    evidence TEXT,
    checked_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS action_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action TEXT NOT NULL,
    result TEXT NOT NULL,
    evidence TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_observations_topic ON observations(topic);
CREATE INDEX IF NOT EXISTS idx_blockers_status ON blockers(status);
CREATE INDEX IF NOT EXISTS idx_compatibility_component ON compatibility_checks(component);
