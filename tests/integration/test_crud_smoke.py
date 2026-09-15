import os
from uuid import uuid4

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QMessageBox
from sqlalchemy import select

from backend.app.core.database import get_session, initialize_database
from backend.app.core.models import Customer, Product, StockLocation, Supplier, Unit
from backend.app.modules.finance.models import Expense, PaymentMethod
from backend.app.modules.finance.revenue import Revenue
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
from frontend.app.ui.revenues_page import RevenuesPage


def _silent_message_boxes(monkeypatch):
    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *args, **kwargs: QMessageBox.Ok))
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *args, **kwargs: QMessageBox.Ok))
    monkeypatch.setattr(QMessageBox, "critical", staticmethod(lambda *args, **kwargs: QMessageBox.Ok))


def test_real_data_entry_across_business_tabs(monkeypatch):
    initialize_database()
    app = QApplication.instance() or QApplication([])
    _silent_message_boxes(monkeypatch)
    token = uuid4().hex[:10].upper()

    products = ProductsPage()
    products.name.setText(f"صنف اختبار {token}")
    products.sku.setText(f"TEST-{token}")
    products.barcode.setText(f"990{token}")
    products.purchase.setValue(10)
    products.sale_price.setValue(15)
    products.minimum_stock.setValue(2)
    assert products.unit.currentData() is not None
    products.save_product()

    session = get_session()
    try:
        product = session.scalar(select(Product).where(Product.sku == f"TEST-{token}"))
        assert product is not None
        product_id = product.id
    finally:
        session.close()

    customers = CustomersPage()
    customers.code.setText(f"CUS-{token}")
    customers.name.setText(f"عميل اختبار {token}")
    customers.phone.setText("777000000")
    customers.save_customer()
    session = get_session()
    try:
        assert session.scalar(select(Customer).where(Customer.code == f"CUS-{token}")) is not None
    finally:
        session.close()

    suppliers = SuppliersPage()
    suppliers.code.setText(f"SUP-{token}")
    suppliers.name.setText(f"مورد اختبار {token}")
    suppliers.phone.setText("777111111")
    suppliers.save_supplier()
    session = get_session()
    try:
        assert session.scalar(select(Supplier).where(Supplier.code == f"SUP-{token}")) is not None
    finally:
        session.close()

    expenses = ExpensesPage()
    expenses.refresh()
    credit_index = next((i for i in range(expenses.payment_method.count()) if "آجل" in expenses.payment_method.itemText(i)), -1)
    assert credit_index >= 0
    expenses.payment_method.setCurrentIndex(credit_index)
    expenses.description.setText(f"مصروف اختبار {token}")
    expenses.amount.setValue(25)
    expenses.save_expense()
    session = get_session()
    try:
        assert session.scalar(select(Expense).where(Expense.description == f"مصروف اختبار {token}")) is not None
    finally:
        session.close()

    revenues = RevenuesPage()
    revenues.refresh()
    assert revenues.payment_method.count() >= 1
    revenues.description.setText(f"إيراد اختبار {token}")
    revenues.amount.setValue(40)
    revenues.save_revenue()
    session = get_session()
    try:
        assert session.scalar(select(Revenue).where(Revenue.description == f"إيراد اختبار {token}")) is not None
    finally:
        session.close()

    purchases = PurchasesPage()
    purchases.refresh()
    pidx = purchases.product.findData(product_id)
    assert pidx >= 0
    purchases.product.setCurrentIndex(pidx)
    supplier_idx = next((i for i in range(purchases.supplier.count()) if purchases.supplier.itemData(i) is not None), -1)
    assert supplier_idx >= 0
    purchases.supplier.setCurrentIndex(supplier_idx)
    purchases.quantity.setValue(20)
    purchases.unit_cost.setValue(10)
    purchases.add_line()
    assert purchases.lines.rowCount() == 1
    purchases.payment.setValue(0)
    purchases.save_purchase()

    session = get_session()
    try:
        location = session.scalar(select(StockLocation).where(StockLocation.is_active.is_(True)).order_by(StockLocation.id))
        assert location is not None
        from backend.app.modules.inventory.service import InventoryService
        assert InventoryService(session).get_balance(product_id, location.id) >= 20
    finally:
        session.close()

    sales = SalesPage()
    sales.refresh_data()
    sidx = sales.product.findData(product_id)
    assert sidx >= 0
    sales.product.setCurrentIndex(sidx)
    sales.quantity.setValue(2)
    sales.add_line()
    assert len(sales.lines) == 1
    sales.create_sale()

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

    for widget in (products, customers, suppliers, expenses, revenues, purchases, sales, inventory, cashboxes, returns, reports):
        widget.close()
    app.processEvents()
