r"""Copy existing local Stress Monitor accounts into the hosted PostgreSQL DB.

Run from the project root after setting DATABASE_URL:

    set DATABASE_URL=postgresql://...
    python webapp\api\migrate_sqlite_to_postgres.py

The script preserves password hashes, so existing users can keep their passwords.
It never prints password hashes.
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import insert

API_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = API_DIR.parent.parent
SOURCE_PATH = Path(os.environ.get("SQLITE_SOURCE_PATH", API_DIR / "users.db"))

if not os.environ.get("DATABASE_URL"):
    raise SystemExit("DATABASE_URL is required and must point to the hosted PostgreSQL database.")
if os.environ["DATABASE_URL"].startswith("sqlite"):
    raise SystemExit("DATABASE_URL points to SQLite. Use the hosted PostgreSQL connection string.")
if not SOURCE_PATH.exists():
    raise SystemExit(f"Local SQLite database not found: {SOURCE_PATH}")

sys.path.insert(0, str(API_DIR))
import database  # noqa: E402


def parse_datetime(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def value(row, key, default=None):
    return row[key] if key in row.keys() and row[key] is not None else default


database.init_db()
source = sqlite3.connect(SOURCE_PATH)
source.row_factory = sqlite3.Row

source_users = source.execute("SELECT * FROM users ORDER BY id").fetchall()
source_tables = {
    row[0] for row in source.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
}

created = 0
skipped = 0
id_map = {}

with database.engine.begin() as target:
    for row in source_users:
        existing = database.get_user_by_email(row["email"])
        if existing:
            id_map[row["id"]] = existing["id"]
            skipped += 1
            continue

        result = target.execute(
            insert(database.users).values(
                name=row["name"],
                email=row["email"].lower(),
                password_hash=row["password_hash"],
                age=value(row, "age"),
                occupation=value(row, "occupation", ""),
                user_type=value(row, "user_type", ""),
                primary_goal=value(row, "primary_goal", ""),
                wearable_device=value(row, "wearable_device", ""),
                research_notice_acknowledged=bool(value(row, "research_notice_acknowledged", 0)),
                is_active=bool(value(row, "is_active", 1)),
                login_count=int(value(row, "login_count", 0)),
                last_login_at=parse_datetime(value(row, "last_login_at")),
                created_at=parse_datetime(value(row, "created_at")) or datetime.utcnow(),
                updated_at=parse_datetime(value(row, "updated_at")),
            )
        )
        id_map[row["id"]] = result.inserted_primary_key[0]
        created += 1

    copied_predictions = 0
    if "predictions" in source_tables:
        for row in source.execute("SELECT * FROM predictions ORDER BY id").fetchall():
            target_user_id = id_map.get(row["user_id"])
            if not target_user_id:
                continue
            target.execute(
                insert(database.predictions).values(
                    user_id=target_user_id,
                    sample_id=value(row, "sample_id"),
                    source_participant_id=value(row, "source_participant_id"),
                    expected_label=value(row, "expected_label"),
                    predicted_label=row["predicted_label"],
                    confidence=float(row["confidence"]),
                    probabilities=(
                        json.loads(value(row, "probabilities", "{}"))
                        if isinstance(value(row, "probabilities", {}), str)
                        else value(row, "probabilities", {})
                    ),
                    created_at=parse_datetime(value(row, "created_at")) or datetime.utcnow(),
                )
            )
            copied_predictions += 1

source.close()

print("Migration complete.")
print(f"Accounts copied: {created}")
print(f"Accounts already present: {skipped}")
print(f"Predictions copied: {copied_predictions}")
