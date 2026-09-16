import pytest


def _reset_database():
    from backend.app.core.database import Base, engine, initialize_database
    Base.metadata.create_all(bind=engine)
    with engine.connect() as connection:
        connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
        tables = connection.exec_driver_sql("SELECT name FROM sqlite_master WHERE type='table'").scalars().all()
        for table in tables:
            if table != "sqlite_sequence":
                safe = table.replace('"', '""')
                connection.exec_driver_sql(f'DELETE FROM "{safe}"')
        connection.commit()
        connection.exec_driver_sql("PRAGMA foreign_keys=ON")
    initialize_database()


def pytest_sessionstart(session):
    _reset_database()


def pytest_runtest_teardown(item, nextitem):
    _reset_database()
