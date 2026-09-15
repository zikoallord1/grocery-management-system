from __future__ import annotations

import sqlite3
import threading
import zipfile
from datetime import date, datetime, timedelta
from pathlib import Path

from PySide6.QtCore import QObject, QTimer
from sqlalchemy import event, select
from sqlalchemy.orm import Session

from backend.app.core.database import Base, DATABASE_PATH, SessionLocal


class DailyClose(Base):
    __tablename__ = "daily_closes"

    id = Base.metadata.tables.get("daily_closes")
    # The table is declared below through a small declarative class factory to
    # keep this module independent from the large core models file.


# Replace the placeholder above with a normal mapped class at import time.
from sqlalchemy import DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column


class DailyClose(Base):
    __tablename__ = "daily_closes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    business_date: Mapped[str] = mapped_column(String(10), nullable=False, unique=True, index=True)
    closed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="CLOSED")
    backup_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(2000), nullable=True)


BACKUP_DIR = DATABASE_PATH.parent / "backups" / "daily"
_MAINTENANCE_LOCK = threading.Lock()


def ensure_daily_close_table() -> None:
    DailyClose.__table__.create(bind=Base.metadata.bind or SessionLocal.kw["bind"], checkfirst=True)


def ensure_business_date_open(session: Session, business_date: str) -> None:
    """Reject new business transactions dated on a completed day."""
    closed = session.execute(
        select(DailyClose.id).where(
            DailyClose.business_date == str(business_date),
            DailyClose.status == "CLOSED",
        )
    ).scalar_one_or_none()
    if closed is not None:
        raise RuntimeError(f"اليوم {business_date} مقفل ولا يمكن إضافة حركة جديدة عليه.")


@event.listens_for(Session, "before_flush")
def _prevent_writes_to_closed_days(session: Session, flush_context, instances) -> None:
    dates = set()
    for obj in session.new:
        value = getattr(obj, "business_date", None)
        if value is not None and not isinstance(obj, DailyClose):
            dates.add(str(value))

    if not dates:
        return

    # The table is created during application startup before normal writes.
    for business_date in dates:
        ensure_business_date_open(session, business_date)


def _sqlite_backup(destination_db: Path) -> None:
    source = sqlite3.connect(str(DATABASE_PATH), timeout=10)
    destination = sqlite3.connect(str(destination_db), timeout=10)
    try:
        source.backup(destination)
    finally:
        destination.close()
        source.close()


def create_daily_backup(business_date: str) -> Path:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    temporary_db = BACKUP_DIR / f".daily_close_{business_date}_{stamp}.db"
    archive_path = BACKUP_DIR / f"daily_close_{business_date}_{stamp}.zip"

    _sqlite_backup(temporary_db)
    try:
        with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.write(temporary_db, arcname="grocery.db")
    finally:
        temporary_db.unlink(missing_ok=True)

    return archive_path


def close_previous_day(now: datetime | None = None) -> Path | None:
    """Close yesterday once and create its automatic backup.

    If the application was not running at midnight, the next startup performs
    the same operation safely. A failed backup leaves the day in FAILED state
    so the next maintenance pass retries it.
    """
    current = now or datetime.now()
    target = current.date() - timedelta(days=1)
    target_text = target.isoformat()

    with _MAINTENANCE_LOCK:
        session = SessionLocal()
        try:
            ensure_daily_close_table()
            record = session.execute(
                select(DailyClose).where(DailyClose.business_date == target_text)
            ).scalar_one_or_none()

            if record is not None and record.status == "CLOSED" and record.backup_path:
                return Path(record.backup_path)

            if record is None:
                record = DailyClose(
                    business_date=target_text,
                    closed_at=current,
                    status="CLOSING",
                )
                session.add(record)
            else:
                record.status = "CLOSING"
                record.error_message = None
                record.closed_at = current
            session.commit()

            try:
                backup_path = create_daily_backup(target_text)
            except Exception as exc:
                record = session.execute(
                    select(DailyClose).where(DailyClose.business_date == target_text)
                ).scalar_one()
                record.status = "FAILED"
                record.error_message = str(exc)[:2000]
                session.commit()
                return None

            record = session.execute(
                select(DailyClose).where(DailyClose.business_date == target_text)
            ).scalar_one()
            record.status = "CLOSED"
            record.backup_path = str(backup_path)
            record.error_message = None
            session.commit()
            return backup_path
        finally:
            session.close()


def run_daily_maintenance() -> Path | None:
    return close_previous_day()


class DailyMaintenanceController(QObject):
    """Keeps daily closing active while the desktop program is running."""

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._timer = QTimer(self)
        self._timer.setInterval(60_000)
        self._timer.timeout.connect(self.check_now)

    def start(self) -> None:
        self.check_now()
        self._timer.start()

    def check_now(self) -> None:
        try:
            run_daily_maintenance()
        except Exception:
            # Maintenance must never stop the sales application. A subsequent
            # timer tick retries the operation.
            return

    def stop(self) -> None:
        self._timer.stop()
