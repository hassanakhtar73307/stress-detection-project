import importlib
import os
import sys
from pathlib import Path

import pytest


API_DIRECTORY = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def flask_app(tmp_path_factory):
    """Load the Flask API using a temporary SQLite test database."""
    database_path = (
        tmp_path_factory.mktemp("database")
        / "stress_api_test.db"
    )

    # Force tests to use an isolated database.
    # This prevents tests from changing Supabase data.
    os.environ["DATABASE_URL"] = (
        f"sqlite:///{database_path.as_posix()}"
    )
    os.environ["SECRET_KEY"] = (
        "pytest-development-secret"
    )
    os.environ["ADMIN_EMAILS"] = (
        "admin@example.com"
    )

    if str(API_DIRECTORY) not in sys.path:
        sys.path.insert(
            0,
            str(API_DIRECTORY),
        )

    app_module = importlib.import_module("app")

    app_module.app.config.update(
        TESTING=True,
    )

    return app_module.app


@pytest.fixture()
def client(flask_app):
    """Provide a Flask test client to each test."""
    with flask_app.test_client() as test_client:
        yield test_client