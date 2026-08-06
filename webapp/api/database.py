"""Database access for Stress Monitor.

Production:
    Set DATABASE_URL to a PostgreSQL connection string (for example Supabase).

Local development:
    If DATABASE_URL is not set, the API uses webapp/api/users.db.

All account/profile records and prediction history are stored server-side.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    and_,
    create_engine,
    func,
    inspect,
    insert,
    select,
    text,
    update,
)
from sqlalchemy.engine import Engine

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DEFAULT_SQLITE_PATH = os.path.join(BASE_DIR, "webapp", "api", "users.db")


def _database_url() -> str:
    raw = (os.environ.get("DATABASE_URL") or "").strip()
    if not raw:
        return f"sqlite:///{DEFAULT_SQLITE_PATH.replace(os.sep, '/')}"

    # Render/Supabase sometimes provide postgres://. Be explicit about psycopg2.
    if raw.startswith("postgres://"):
        return "postgresql+psycopg2://" + raw[len("postgres://"):]
    if raw.startswith("postgresql://"):
        return "postgresql+psycopg2://" + raw[len("postgresql://"):]
    return raw


DATABASE_URL = _database_url()
IS_SQLITE = DATABASE_URL.startswith("sqlite")

engine_options: dict[str, Any] = {"pool_pre_ping": True, "future": True}
if IS_SQLITE:
    os.makedirs(os.path.dirname(DEFAULT_SQLITE_PATH), exist_ok=True)
    engine_options["connect_args"] = {"check_same_thread": False}
else:
    # Helps recover cleanly when the hosted database closes an idle connection.
    engine_options.update({"pool_recycle": 300})

engine: Engine = create_engine(DATABASE_URL, **engine_options)
metadata = MetaData()

users = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("name", String(160), nullable=False),
    Column("email", String(320), nullable=False, unique=True, index=True),
    Column("password_hash", Text, nullable=False),
    Column("age", Integer),
    Column("occupation", String(200)),
    Column("user_type", String(50)),
    Column("primary_goal", String(80)),
    Column("wearable_device", String(80)),
    Column("research_notice_acknowledged", Boolean, nullable=False, server_default=text("false")),
    Column("is_active", Boolean, nullable=False, server_default=text("true")),
    Column("login_count", Integer, nullable=False, server_default=text("0")),
    Column("last_login_at", DateTime(timezone=True)),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True)),
)

predictions = Table(
    "predictions",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("sample_id", String(80)),
    Column("source_participant_id", String(30)),
    Column("expected_label", String(40)),
    Column("model_name", String(40), nullable=False, server_default=text("'xgboost'")),
    Column("predicted_label", String(40), nullable=False),
    Column("confidence", Float, nullable=False),
    Column("probabilities", JSON, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now(), index=True),
)


def _row_to_dict(row) -> dict[str, Any] | None:
    return dict(row._mapping) if row is not None else None


def _ensure_existing_user_columns() -> None:
    """Add analytics columns to older SQLite/Postgres user tables safely."""
    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        return

    existing = {column["name"] for column in inspector.get_columns("users")}
    dialect = engine.dialect.name

    definitions = {
        "user_type": "VARCHAR(50)",
        "primary_goal": "VARCHAR(80)",
        "wearable_device": "VARCHAR(80)",
        "research_notice_acknowledged": (
            "BOOLEAN NOT NULL DEFAULT FALSE" if dialect == "postgresql" else "BOOLEAN NOT NULL DEFAULT 0"
        ),
        "is_active": (
            "BOOLEAN NOT NULL DEFAULT TRUE" if dialect == "postgresql" else "BOOLEAN NOT NULL DEFAULT 1"
        ),
        "login_count": "INTEGER NOT NULL DEFAULT 0",
        "last_login_at": "TIMESTAMP",
        "updated_at": "TIMESTAMP",
    }

    with engine.begin() as conn:
        for column_name, definition in definitions.items():
            if column_name not in existing:
                conn.execute(text(f"ALTER TABLE users ADD COLUMN {column_name} {definition}"))

def _ensure_existing_prediction_columns() -> None:
    """Add model information to older prediction tables safely."""
    inspector = inspect(engine)

    if "predictions" not in inspector.get_table_names():
        return

    existing = {
        column["name"]
        for column in inspector.get_columns("predictions")
    }

    if "model_name" not in existing:
        with engine.begin() as conn:
            conn.execute(
                text(
                    "ALTER TABLE predictions "
                    "ADD COLUMN model_name VARCHAR(40) "
                    "NOT NULL DEFAULT 'xgboost'"
                )
            )
def init_db() -> None:
    metadata.create_all(engine)
    _ensure_existing_user_columns()
    _ensure_existing_prediction_columns()


def database_status() -> dict[str, str]:
    return {
        "backend": "sqlite" if IS_SQLITE else "postgresql",
        "location": "local" if IS_SQLITE else "hosted",
    }


def create_user(
    name,
    email,
    password_hash,
    age=None,
    occupation=None,
    user_type=None,
    primary_goal=None,
    wearable_device=None,
    research_notice_acknowledged=False,
):
    now = datetime.now(timezone.utc)
    statement = insert(users).values(
        name=name,
        email=email,
        password_hash=password_hash,
        age=age,
        occupation=occupation,
        user_type=user_type,
        primary_goal=primary_goal,
        wearable_device=wearable_device,
        research_notice_acknowledged=bool(research_notice_acknowledged),
        is_active=True,
        login_count=0,
        created_at=now,
        updated_at=now,
    )
    with engine.begin() as conn:
        result = conn.execute(statement)
        return result.inserted_primary_key[0]


def get_user_by_email(email):
    with engine.connect() as conn:
        row = conn.execute(select(users).where(func.lower(users.c.email) == email.lower())).first()
        return _row_to_dict(row)


def get_user_by_id(user_id):
    with engine.connect() as conn:
        row = conn.execute(select(users).where(users.c.id == user_id)).first()
        return _row_to_dict(row)


def update_user_profile(user_id, name, age, occupation, user_type, primary_goal, wearable_device):
    with engine.begin() as conn:
        conn.execute(
            update(users)
            .where(users.c.id == user_id)
            .values(
                name=name,
                age=age,
                occupation=occupation,
                user_type=user_type,
                primary_goal=primary_goal,
                wearable_device=wearable_device,
                updated_at=datetime.now(timezone.utc),
            )
        )


def update_password_by_email(email, new_password_hash):
    with engine.begin() as conn:
        conn.execute(
            update(users)
            .where(func.lower(users.c.email) == email.lower())
            .values(password_hash=new_password_hash, updated_at=datetime.now(timezone.utc))
        )


def record_login(user_id):
    now = datetime.now(timezone.utc)
    with engine.begin() as conn:
        conn.execute(
            update(users)
            .where(users.c.id == user_id)
            .values(
                login_count=func.coalesce(users.c.login_count, 0) + 1,
                last_login_at=now,
                updated_at=now,
            )
        )


def create_prediction(
    user_id,
    predicted_label,
    confidence,
    probabilities,
    model_name="xgboost",
    sample_id=None,
    source_participant_id=None,
    expected_label=None,
):
    with engine.begin() as conn:
        result = conn.execute(
            insert(predictions).values(
                user_id=user_id,
                sample_id=sample_id,
                source_participant_id=source_participant_id,
                expected_label=expected_label,
                model_name=model_name,
                predicted_label=predicted_label,
                confidence=float(confidence),
                probabilities=probabilities,
                created_at=datetime.now(timezone.utc),
            )
        )
        return result.inserted_primary_key[0]


def _count(conn, statement) -> int:
    return int(conn.execute(statement).scalar_one() or 0)


def admin_overview(limit=200) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    seven_days_ago = now - timedelta(days=7)
    thirty_days_ago = now - timedelta(days=30)

    required_profile = and_(
        users.c.user_type.is_not(None),
        users.c.user_type != "",
        users.c.primary_goal.is_not(None),
        users.c.primary_goal != "",
        users.c.wearable_device.is_not(None),
        users.c.wearable_device != "",
    )

    with engine.connect() as conn:
        total_users = _count(conn, select(func.count()).select_from(users))
        active_users = _count(
            conn,
            select(func.count()).select_from(users).where(users.c.is_active.is_(True)),
        )
        complete_profiles = _count(
            conn,
            select(func.count()).select_from(users).where(required_profile),
        )
        registrations_7d = _count(
            conn,
            select(func.count()).select_from(users).where(users.c.created_at >= seven_days_ago),
        )
        registrations_30d = _count(
            conn,
            select(func.count()).select_from(users).where(users.c.created_at >= thirty_days_ago),
        )
        total_predictions = _count(conn, select(func.count()).select_from(predictions))

        def grouped(column):
            rows = conn.execute(
                select(column.label("name"), func.count().label("count"))
                .select_from(users)
                .group_by(column)
                .order_by(func.count().desc())
            ).all()
            return [
                {"name": (row.name or "Not provided"), "count": int(row.count)}
                for row in rows
            ]

        by_user_type = grouped(users.c.user_type)
        by_primary_goal = grouped(users.c.primary_goal)
        by_wearable_device = grouped(users.c.wearable_device)

        recent_rows = conn.execute(
            select(
                predictions.c.id,
                predictions.c.user_id,
                users.c.name.label("user_name"),
                users.c.email.label("user_email"),
                predictions.c.sample_id,
                predictions.c.source_participant_id,
                predictions.c.expected_label,
                predictions.c.model_name,
                predictions.c.predicted_label,
                predictions.c.confidence,
                predictions.c.created_at,
            )
            .select_from(predictions.join(users, predictions.c.user_id == users.c.id))
            .order_by(predictions.c.created_at.desc())
            .limit(10)
        ).all()

    return {
        "totals": {
            "users": total_users,
            "active_users": active_users,
            "complete_profiles": complete_profiles,
            "registrations_7d": registrations_7d,
            "registrations_30d": registrations_30d,
            "predictions": total_predictions,
        },
        "by_user_type": by_user_type,
        "by_primary_goal": by_primary_goal,
        "by_wearable_device": by_wearable_device,
        "recent_predictions": [dict(row._mapping) for row in recent_rows],
        "database": database_status(),
    }


def list_users(limit=200):
    limit = max(1, min(int(limit), 500))
    with engine.connect() as conn:
        rows = conn.execute(
            select(
                users.c.id,
                users.c.name,
                users.c.email,
                users.c.age,
                users.c.occupation,
                users.c.user_type,
                users.c.primary_goal,
                users.c.wearable_device,
                users.c.research_notice_acknowledged,
                users.c.is_active,
                users.c.login_count,
                users.c.last_login_at,
                users.c.created_at,
                users.c.updated_at,
            )
            .order_by(users.c.created_at.desc())
            .limit(limit)
        ).all()
        return [dict(row._mapping) for row in rows]


def list_predictions(limit=200):
    limit = max(1, min(int(limit), 500))
    with engine.connect() as conn:
        rows = conn.execute(
            select(
                predictions.c.id,
                predictions.c.user_id,
                users.c.name.label("user_name"),
                users.c.email.label("user_email"),
                predictions.c.sample_id,
                predictions.c.source_participant_id,
                predictions.c.expected_label,
                predictions.c.predicted_label,
                predictions.c.confidence,
                predictions.c.probabilities,
                predictions.c.created_at,
            )
            .select_from(predictions.join(users, predictions.c.user_id == users.c.id))
            .order_by(predictions.c.created_at.desc())
            .limit(limit)
        ).all()
        return [dict(row._mapping) for row in rows]
