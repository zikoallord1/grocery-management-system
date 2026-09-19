import hashlib
import json
import os
import sys
from pathlib import Path

from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import DeclarativeBase, sessionmaker

PROJECT_ROOT = Path(__file__).resolve().parents[3]

if getattr(sys, "frozen", False):
    _local_app_data = os.environ.get("LOCALAPPDATA")
    DATA_DIR = Path(_local_app_data) / "GroceryManagementSystem" if _local_app_data else Path.home() / "AppData" / "Local" / "GroceryManagementSystem"
else:
    DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_PATH = DATA_DIR / "grocery.db"
DATABASE_URL = f"sqlite:///{DATABASE_PATH.as_posix()}"

engine = create_engine(DATABASE_URL, future=True, connect_args={"check_same_thread": False})


@event.listens_for(engine, "connect")
def set_sqlite_pragmas(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()


class Base(DeclarativeBase):
    pass


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_session():
    return SessionLocal()


def _ensure_default_login():
    """Guarantee a usable first-run administrator: admin / admin.

    Existing non-admin users are preserved. The built-in administrator is
    repaired on every startup so a stale/corrupt installation cannot leave
    the customer locked out after installing or updating the program.
    """
    users_file = DATA_DIR / "users.json"
    default_hash = hashlib.sha256("admin".encode("utf-8")).hexdigest()
    users = []

    if users_file.exists():
        try:
            data = json.loads(users_file.read_text(encoding="utf-8"))
            if isinstance(data, list):
                users = data
        except (OSError, ValueError):
            users = []

    admin = next((u for u in users if str(u.get("username", "")).casefold() == "admin"), None)
    if admin is None:
        users.insert(0, {
            "id": "admin",
            "username": "admin",
            "display_name": "مدير النظام",
            "role": "admin",
            "active": True,
            "password_hash": default_hash,
        })
    else:
        admin["id"] = admin.get("id") or "admin"
        admin["display_name"] = admin.get("display_name") or "مدير النظام"
        admin["role"] = "admin"
        admin["active"] = True
        admin["password_hash"] = default_hash

    users_file.write_text(json.dumps(users, ensure_ascii=False, indent=2), encoding="utf-8")


def _ensure_default_finance_setup():
    from backend.app.modules.finance.models import Cashbox, ExpenseCategory, PaymentMethod

    session = SessionLocal()
    try:
        defaults = [
            ("CASH", "النقد", "CASH", None),
            ("WALLET", "المحفظة الإلكترونية", "WALLET", "محفظة إلكترونية"),
            ("BANK", "الحساب البنكي", "BANK", "حساب بنكي"),
        ]
        cashboxes = {}
        for code, name, account_type, provider_name in defaults:
            cashbox = session.execute(select(Cashbox).where(Cashbox.code == code)).scalar_one_or_none()
            if cashbox is None:
                cashbox = Cashbox(code=code, name=name, account_type=account_type, currency="BASE", provider_name=provider_name)
                session.add(cashbox); session.flush()
            cashboxes[code] = cashbox

        payment_defaults = [("CASH", "نقد", "CASH", "CASH"), ("WALLET", "محفظة إلكترونية", "WALLET", "WALLET"), ("BANK", "تحويل بنكي", "BANK", "BANK")]
        for code, name, method_type, cashbox_code in payment_defaults:
            method = session.execute(select(PaymentMethod).where(PaymentMethod.code == code)).scalar_one_or_none()
            if method is None:
                session.add(PaymentMethod(code=code, name=name, method_type=method_type, cashbox_id=cashboxes[cashbox_code].id))
            elif method.cashbox_id is None:
                method.cashbox_id = cashboxes[cashbox_code].id; method.is_active = True

        credit = session.execute(select(PaymentMethod).where(PaymentMethod.code == "CREDIT")).scalar_one_or_none()
        if credit is None:
            session.add(PaymentMethod(code="CREDIT", name="آجل / غير مدفوع", method_type="CREDIT", cashbox_id=None))
        else:
            credit.name = "آجل / غير مدفوع"; credit.method_type = "CREDIT"; credit.cashbox_id = None; credit.is_active = True

        for name in ["مشتريات", "رواتب وأجور", "كهرباء وماء", "نقل ومواصلات", "صيانة", "اتصالات", "إيجار", "أخرى"]:
            category = session.execute(select(ExpenseCategory).where(ExpenseCategory.name == name)).scalar_one_or_none()
            if category is None:
                session.add(ExpenseCategory(name=name))

        from backend.app.core.models import StockLocation
        location = session.execute(select(StockLocation).where(StockLocation.code == "MAIN")).scalar_one_or_none()
        if location is None:
            session.add(StockLocation(code="MAIN", name="المخزن الرئيسي", location_type="STORE", is_active=True))
        session.commit()
    finally:
        session.close()


def initialize_database():
    from .audit_models import AuditLog
    from . import models  # noqa: F401
    from . import product_units  # noqa: F401
    from backend.app.modules.finance import models as finance_models  # noqa: F401
    from backend.app.modules.finance import revenue as revenue_model  # noqa: F401
    from . import daily_operations  # noqa: F401
    from . import sync_models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    AuditLog.__table__.create(bind=engine, checkfirst=True)
    _ensure_default_login()
    _ensure_default_finance_setup()
