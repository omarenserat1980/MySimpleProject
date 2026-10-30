"""SQLite memory for the Honda e:NP1 Android-app/network activation project.

The database is private runtime state, not a repository artifact. VIN is read only
from BRAIN_VEHICLE_VIN and is never printed by this module.
"""
from __future__ import annotations

import argparse
import os
import sqlite3
from pathlib import Path

from . import __file__ as package_file

SCHEMA_PATH = Path(package_file).with_name("schema.sql")
DEFAULT_STATE_DIR = Path(os.environ.get("BRAIN_STATE_DIR", Path.home() / ".electronic_brain" / "state"))
DEFAULT_DB_PATH = Path(os.environ.get("BRAIN_HONDA_NETWORK_DB", DEFAULT_STATE_DIR / "honda_android_network.sqlite3"))


def connect(db_path: str | Path | None = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path else DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize(db_path: str | Path | None = None) -> Path:
    path = Path(db_path) if db_path else DEFAULT_DB_PATH
    with connect(path) as db:
        db.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        vin = os.environ.get("BRAIN_VEHICLE_VIN", "").strip()
        db.execute(
            """INSERT INTO vehicle_profile
               (id, make, model, model_year, vin, purchase_condition, purchase_country,
                market_origin, manufacturer_hypothesis, manufacturer_confidence)
               VALUES (1, 'Honda', 'e:NP1', 2023, ?, 'new', 'Jordan',
                       'China-market import', 'GAC Honda (unverified from VIN decode)',
                       'unverified')
               ON CONFLICT(id) DO UPDATE SET
                 vin = CASE WHEN excluded.vin IS NOT NULL AND excluded.vin <> ''
                            THEN excluded.vin ELSE vehicle_profile.vin END,
                 updated_at = CURRENT_TIMESTAMP""",
            (vin,),
        )
        db.execute(
            """INSERT INTO head_unit (id, software_version)
               VALUES (1, '01.000.400')
               ON CONFLICT(id) DO UPDATE SET
                 software_version = COALESCE(head_unit.software_version, excluded.software_version),
                 updated_at = CURRENT_TIMESTAMP"""
        )
        db.execute(
            """INSERT INTO device_profile
               (id, phone_model, android_version, carlife_app, carlife_version,
                usb_data_port_confirmed)
               VALUES (1, 'Realme RMX3710 / C66', 'Android 15', 'Baidu CarLife EX', '8.9.5', 1)
               ON CONFLICT(id) DO UPDATE SET updated_at = CURRENT_TIMESTAMP"""
        )
        _seed_observations(db)
        db.execute(
            """INSERT INTO goals (goal_key, title, priority, status, acceptance_criteria)
               VALUES ('android_app_network', 'Enable reliable Android app connectivity on the Honda head unit',
                       1, 'active',
                       'At least one supported, repeatable network path from the Realme phone to the head unit is verified; target Android apps are launched on the head unit only through a compatible, safe projection or supported installation path.')
               ON CONFLICT(goal_key) DO UPDATE SET priority=1, status='active',
                 updated_at=CURRENT_TIMESTAMP"""
        )
        db.execute(
            """INSERT INTO blockers (blocker_key, title, detail, safe_next_step)
               VALUES
               ('usb_tethering', 'USB tethering not established',
                'Phone readback remained accessory,adb; RNDIS was not verified. Head-unit RNDIS host support is also unknown.',
                'Identify head-unit hardware and test supported USB network modes without forcing privileged Android USB settings.'),
               ('carlife_video', 'CarLife video projection remains blank',
                'Super Cast unlock command reported success on the phone, but YouTube projection showed a white area and a projecting message.',
                'Identify the head-unit CarLife receiver version and verify compatibility before changing packages.'),
               ('connect_qr', 'Honda CONNECT activation QR absent',
                'The head unit shows owner-verification instructions but no QR code. No evidence yet confirms TCU fault or server provisioning state.',
                'Confirm exact vehicle manufacturer/market and request backend VIN/TCU provisioning check from the correct Honda entity.')
               ON CONFLICT(blocker_key) DO UPDATE SET detail=excluded.detail,
                 safe_next_step=excluded.safe_next_step, status='open',
                 updated_at=CURRENT_TIMESTAMP"""
        )
    return path


def _seed_observations(db: sqlite3.Connection) -> None:
    rows = [
        ("vehicle", "observed", "User identifies the vehicle as Honda e:NP1, model year 2023; purchased new in Jordan."),
        ("head_unit", "observed", "Head-unit software version shown as 01.000.400."),
        ("honda_connect", "observed", "Honda CONNECT 3.0 identity-verification instructions appear, but the vehicle-binding QR code never appears."),
        ("menus", "observed", "Previously inspected visible General Settings menus did not expose WLAN or Network settings."),
        ("usb", "observed", "Phone connected to the head unit DATA USB port; USB media screen recognized Realme C66."),
        ("usb", "failed", "USB tethering was not confirmed. Android USB state remained accessory,adb; RNDIS did not persist."),
        ("carlife", "observed", "Baidu CarLife EX is present; phone app version 8.9.5."),
        ("carlife", "failed", "After Super Cast unlock reported success, YouTube projection remained white and displayed a projecting status message."),
        ("phone", "observed", "Phone is Realme RMX3710 / C66 running Android 15; Termux diagnostics available."),
        ("manufacturer", "hypothesis", "GAC Honda is a working hypothesis based on model context; VIN/manufacturer decode has not been independently verified."),
        ("safety", "confirmed", "Do not factory-reset the head unit, flash generic firmware, or force privileged USB settings without exact compatibility and recovery evidence."),
    ]
    for topic, status, detail in rows:
        db.execute(
            "INSERT INTO observations(topic,status,detail,source) "
            "SELECT ?,?,?, 'conversation-derived baseline' "
            "WHERE NOT EXISTS (SELECT 1 FROM observations WHERE topic=? AND detail=?)",
            (topic, status, detail, topic, detail),
        )


def summary(db_path: str | Path | None = None) -> dict:
    with connect(db_path) as db:
        vehicle = db.execute(
            "SELECT make, model, model_year, purchase_condition, purchase_country, "
            "market_origin, manufacturer_hypothesis, manufacturer_confidence "
            "FROM vehicle_profile WHERE id=1"
        ).fetchone()
        head = db.execute("SELECT software_version, manufacturer, hardware_model FROM head_unit WHERE id=1").fetchone()
        phone = db.execute("SELECT phone_model, android_version, carlife_app, carlife_version FROM device_profile WHERE id=1").fetchone()
        goal = db.execute("SELECT title, status, acceptance_criteria FROM goals ORDER BY priority LIMIT 1").fetchone()
        blockers = db.execute("SELECT blocker_key,title,status,safe_next_step FROM blockers ORDER BY id").fetchall()
        return {
            "database": str(Path(db_path) if db_path else DEFAULT_DB_PATH),
            "vehicle": dict(vehicle) if vehicle else None,
            "head_unit": dict(head) if head else None,
            "phone": dict(phone) if phone else None,
            "primary_goal": dict(goal) if goal else None,
            "blockers": [dict(row) for row in blockers],
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize or inspect Brain's Honda Android network SQLite memory.")
    parser.add_argument("command", choices=("init", "status"))
    parser.add_argument("--db", dest="db_path")
    args = parser.parse_args()
    path = initialize(args.db_path) if args.command in {"init", "status"} else DEFAULT_DB_PATH
    if args.command == "status":
        data = summary(path)
        print(f"Database: {data['database']}")
        print(f"Vehicle: {data['vehicle']}")
        print(f"Head unit: {data['head_unit']}")
        print(f"Phone: {data['phone']}")
        print(f"Primary goal: {data['primary_goal']['title'] if data['primary_goal'] else 'not initialized'}")
        for blocker in data["blockers"]:
            print(f"- {blocker['blocker_key']}: {blocker['title']} [{blocker['status']}]")
    else:
        print(f"Initialized Brain Honda network memory: {path}")


if __name__ == "__main__":
    main()
