from datetime import datetime

import pytest

from backend.app.core.database import SessionLocal, initialize_database
from backend.app.core.daily_operations import (
    DailyClose,
    close_previous_day,
    ensure_business_date_open,
)


def test_daily_close_is_idempotent_and_creates_backup(tmp_path, monkeypatch):
    import backend.app.core.daily_operations as daily

    initialize_database()
    monkeypatch.setattr(daily, "BACKUP_DIR", tmp_path)

    now = datetime(2098, 5, 20, 23, 59, 0)
    first = close_previous_day(now)
    second = close_previous_day(now)

    assert first is not None
    assert first.exists()
    assert first.suffix == ".zip"
    assert second == first

    session = SessionLocal()
    try:
        record = session.query(DailyClose).filter_by(business_date="2098-05-19").one()
        assert record.status == "CLOSED"
        assert record.backup_path == str(first)
    finally:
        session.close()


def test_closed_business_date_rejects_new_business_transaction():
    initialize_database()
    session = SessionLocal()
    target = "2098-05-21"
    try:
        session.query(DailyClose).filter_by(business_date=target).delete()
        session.add(
            DailyClose(
                business_date=target,
                closed_at=datetime(2098, 5, 22, 0, 1),
                status="CLOSED",
            )
        )
        session.commit()

        with pytest.raises(RuntimeError, match="مقفل"):
            ensure_business_date_open(session, target)
    finally:
        session.query(DailyClose).filter_by(business_date=target).delete()
        session.commit()
        session.close()
