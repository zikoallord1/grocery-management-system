import os
from datetime import date
from uuid import uuid4

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QMessageBox
from sqlalchemy import select

from backend.app.core.database import get_session, initialize_database
from backend.app.core.models import Customer, Product, Supplier, StockLocation
from backend.app.modules.finance.models import Cashbox, Expense, ExpenseCategory, PaymentMethod
from frontend.app.ui.cashboxes_page import CashboxesPage
from frontend.app.ui.customers_page import CustomersPage
from frontend.app.ui.expenses_page import ExpensesPage
from frontend.app.ui.inventory_page import InventoryPage
from frontend.app.ui.products_page import ProductsPage
from frontend.app.ui.purchases_page import PurchasesPage
from frontend.app.ui.reports_page import ReportsPage
from frontend.app.ui.returns_page import ReturnsPage
from frontend.app.ui.sales_page import SalesPage
from frontend.app.ui.suppliers_page import SuppliersPage


def _silent_message_boxes(monkeypatch):
    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *args, **kwargs: QMessageBox.Ok))
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *args, **kwargs: QMessageBox.Ok))
    monkeypatch.setattr(QMessageBox, "critical", staticmethod(lambda *args, **kwargs: QMessageBox.Ok))


def test_real_data_entry_across_business_tabs(monkeypatch):
    initialize_database()
    app = QApplication.instance() or QApplication([])
    _silent_message_boxes(monkeypatch)
    token = uuid4().hex[:10].upper()
    today = date.today().isoformat()

    # 1) Product entry
    products = ProductsPage()
    products.name.setText(f"صنف اختبار {token}")
    products.sku.setText(f"TEST-{token}")
    products.barcode.setText(f"990{token[:10]}")
    products.purchase.setValue(10)
    products.sale.setValue(15)
    products.minimum.setValue(2)
    products.save_product()

    session = get_session()
    try:
        product = session.scalar(select(Product).where(Product.sku == f"TEST-{token}"))
        assert product is not None
        product_id = product.id
    finally:
        session.close()

    # 2) Customer entry
    customers = CustomersPage()
    customers.code.setText(f"CUS-{token}")
    customers.name.setText(f"عميل اختبار {token}")
    customers.phone.setText("777000000")
    customers.save_customer()

    # 3) Supplier entry
    suppliers = SuppliersPage()
    suppliers.code.setText(f"SUP-{token}")
    suppliers.name.setText(f"مورد اختبار {token}")
    suppliers.phone.setText("777111111")
    suppliers.save_supplier()

    # 4) Expense entry using the intentionally supported unpaid/credit method,
    # so the test does not depend on an existing cash balance.
    expenses = ExpensesPage()
    expenses.refresh()
    expenses.category.setCurrentIndex(0)
    credit_index = expenses.payment_method.findData(next(
        (expenses.payment_method.itemData(i) for i in range(expenses.payment_method.count())
         if "آجل" in expenses.payment_method.itemText(i)),
        None,
    ))
    if credit_index >= 0:
        expenses.payment_method.setCurrentIndex(credit_index)
    expenses.description.setText(f"مصروف اختبار {token}")
    expenses.amount.setValue(25)
    expenses.save_expense()

    session = get_session()
    try:
        assert session.scalar(select(Expense).where(Expense.description == f"مصروف اختبار {token}")) is not None
    finally:
        session.close()

    # 5) Purchase entry: creates stock that the sales tab can consume.
    purchases = PurchasesPage()
    purchases.refresh()
    pidx = purchases.product.findData(product_id)
    assert pidx >= 0
    purchases.product.setCurrentIndex(pidx)
    purchases.quantity.setValue(20)
    purchases.unit_cost.setValue(10)
    # Use the default cash payment; purchase service is responsible for the accounting link.
    purchases.add_line()
    assert purchases.lines.rowCount() == 1
    purchases.save_purchase()

    # 6) Sales entry against the stock created above.
    sales = SalesPage()
    sales.refresh_data()
    sidx = sales.product.findData(product_id)
    assert sidx >= 0
    sales.product.setCurrentIndex(sidx)
    sales.quantity.setValue(2)
    sales.add_line()
    assert len(sales.lines) == 1
    sales.create_sale()

    session = get_session()
    try:
        stock_location = session.scalar(select(StockLocation).where(StockLocation.is_active.is_(True)).order_by(StockLocation.id))
        assert stock_location is not None
    finally:
        session.close()

    # 7) Remaining tabs must at least load their real data models after entries.
    inventory = InventoryPage()
    inventory.refresh()
    assert inventory.balance_table.rowCount() >= 1

    cashboxes = CashboxesPage()
    cashboxes.refresh()
    assert cashboxes.cashboxes_table.rowCount() >= 3

    returns = ReturnsPage()
    returns.refresh()

    reports = ReportsPage()
    reports.refresh()

    for widget in (products, customers, suppliers, expenses, purchases, sales, inventory, cashboxes, returns, reports):
        widget.close()
    app.processEvents()
