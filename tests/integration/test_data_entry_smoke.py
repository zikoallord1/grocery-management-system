import json
import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QMessageBox
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from backend.app.core.database import Base
from backend.app.core.models import Product, Unit
from backend.app.modules.finance.models import Expense, ExpenseCategory, PaymentMethod
from frontend.app.ui import expenses_page, permissions_page, products_page, users_page
from frontend.app.ui.expenses_page import ExpensesPage
from frontend.app.ui.permissions_page import PermissionsPage
from frontend.app.ui.products_page import ProductsPage
from frontend.app.ui.users_page import UsersPage


def _temp_session(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{(tmp_path / 'smoke.db').as_posix()}", future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    monkeypatch.setattr("frontend.app.ui.products_page.get_session", Session)
    monkeypatch.setattr("frontend.app.ui.expenses_page.get_session", Session)
    return Session


def test_product_and_expense_entry_accept_data(tmp_path, monkeypatch):
    Session = _temp_session(tmp_path, monkeypatch)
    session = Session()
    session.add(Unit(name="قطعة", symbol="قطعة", is_active=True))
    category = ExpenseCategory(name="أخرى", is_active=True)
    session.add(category)
    session.add(PaymentMethod(code="CREDIT", name="آجل / غير مدفوع", method_type="CREDIT", cashbox_id=None, is_active=True))
    session.commit()
    session.close()

    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(QMessageBox, "critical", staticmethod(lambda *args, **kwargs: None))
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *args, **kwargs: None))
    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *args, **kwargs: None))

    product = ProductsPage()
    product.name.setText("ماء معدني")
    product.purchase.setValue(100)
    product.sale.setValue(150)
    product.save_product()

    session = Session()
    saved_product = session.scalar(select(Product).where(Product.name == "ماء معدني"))
    assert saved_product is not None
    assert saved_product.sku.startswith("ITM-")
    session.close()

    expense = ExpensesPage()
    expense.amount.setValue(250)
    expense.description.setText("نقل")
    expense.save_expense()

    session = Session()
    saved_expense = session.scalar(select(Expense).order_by(Expense.id.desc()))
    assert saved_expense is not None
    assert saved_expense.amount == 250
    assert saved_expense.description == "نقل"
    session.close()
    product.close()
    expense.close()
    app.processEvents()


def test_users_and_role_permissions_persist(tmp_path, monkeypatch):
    users_file = tmp_path / "users.json"
    permissions_file = tmp_path / "permissions.json"
    monkeypatch.setattr(users_page, "USERS_FILE", users_file)
    monkeypatch.setattr(permissions_page, "PERMISSIONS_FILE", permissions_file)
    app = QApplication.instance() or QApplication([])

    users = UsersPage()
    users._new_user()
    users.username.setText("cashier1")
    users.full_name.setText("كاشير 1")
    users.password.setText("123456")
    users.role.setCurrentText("بائع")
    users._save_user()
    data = json.loads(users_file.read_text(encoding="utf-8"))
    assert any(item["username"] == "cashier1" for item in data)

    permissions = PermissionsPage()
    permissions.role.setCurrentText("بائع")
    permissions._set_module("المبيعات", True)
    permissions._save()
    saved = json.loads(permissions_file.read_text(encoding="utf-8"))
    assert saved["بائع"]["المبيعات"]["إضافة"] is True
    permissions._set_module("المبيعات", False)
    permissions._save()
    saved = json.loads(permissions_file.read_text(encoding="utf-8"))
    assert saved["بائع"]["المبيعات"]["إضافة"] is False
    users.close()
    permissions.close()
    app.processEvents()
