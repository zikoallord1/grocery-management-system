from pathlib import Path

from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import DeclarativeBase, sessionmaker

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_PATH = DATA_DIR / "grocery.db"
DATABASE_URL = f"sqlite:///{DATABASE_PATH.as_posix()}"

engine = create_engine(
    DATABASE_URL,
    future=True,
    connect_args={"check_same_thread": False},
)


@event.listens_for(engine, "connect")
def set_sqlite_pragmas(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()


class Base(DeclarativeBase):
    pass


SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


def get_session():
    return SessionLocal()


def _ensure_default_finance_setup():
    from backend.app.modules.finance.models import Cashbox, PaymentMethod

    session = SessionLocal()

    try:
        cash = session.execute(
            select(Cashbox).where(Cashbox.code == "CASH")
        ).scalar_one_or_none()

        if cash is None:
            cash = Cashbox(
                code="CASH",
                name="النقد",
                account_type="CASH",
                currency="BASE",
            )
            session.add(cash)
            session.flush()

        method = session.execute(
            select(PaymentMethod).where(PaymentMethod.code == "CASH")
        ).scalar_one_or_none()

        if method is None:
            session.add(
                PaymentMethod(
                    code="CASH",
                    name="نقد",
                    method_type="CASH",
                    cashbox_id=cash.id,
                )
            )

        session.commit()

    finally:
        session.close()


def initialize_database():
    from . import models  # noqa: F401
    from backend.app.modules.finance import models as finance_models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _ensure_default_finance_setup()
