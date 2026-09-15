from pathlib import Path

from sqlalchemy import inspect

from backend.app.core.database import DATABASE_PATH, initialize_database


def test_database_initializes():
    initialize_database()

    assert DATABASE_PATH.exists()

    from backend.app.core.database import engine

    inspector = inspect(engine)
    tables = inspector.get_table_names()

    assert "products" in tables
