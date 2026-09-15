from uuid import uuid4

import pytest
from sqlalchemy import select

pytest.importorskip("PySide6")


def test_all_data_entry_pages_construct(qtbot):
    from frontend.app.ui.customers_page import CustomersPage
    from frontend.app.ui.expenses_page import ExpensesPage
    from frontend.app.ui.inventory_page import InventoryPage
    from frontend.app.ui.products_page import ProductsPage
    from frontend.app.ui.purchases_page import PurchasesPage
    from frontend.app.ui.revenues_page import RevenuesPage
    from frontend.app.ui.returns_page import ReturnsPage
    from frontend.app.ui.sales_page import SalesPage
    from frontend.app.ui.suppliers_page import SuppliersPage

    for page_type in (ProductsPage, InventoryPage, SalesPage, PurchasesPage, CustomersPage, SuppliersPage, ExpensesPage, RevenuesPage, ReturnsPage):
        page = page_type()
        qtbot.addWidget(page)
        page.show()
        assert page.isVisible()
        page.close()


def test_product_customer_supplier_expense_and_revenue_inputs(qtbot, monkeypatch):
    from frontend.app.ui.customers_page import CustomersPage
    from frontend.app.ui.expenses_page import ExpensesPage
    from frontend.app.ui.products_page import ProductsPage
    from frontend.app.ui.revenues_page import RevenuesPage
    from frontend.app.ui.suppliers_page import SuppliersPage
    from backend.app.core.database import get_session, initialize_database
    from backend.app.core.models import Customer, Product, ProductBarcode, Supplier
    from backend.app.modules.finance.models import Expense, ExpenseCategory, PaymentMethod
    from backend.app.modules.finance.revenue import Revenue

    initialize_database()
    for module in ("products_page", "customers_page", "suppliers_page", "expenses_page", "revenues_page"):
        monkeypatch.setattr(f"frontend.app.ui.{module}.QMessageBox.warning", lambda *a, **k: None)
        monkeypatch.setattr(f"frontend.app.ui.{module}.QMessageBox.critical", lambda *a, **k: None)
        monkeypatch.setattr(f"frontend.app.ui.{module}.QMessageBox.information", lambda *a, **k: None)

    suffix = uuid4().hex[:10].upper()

    product_page = ProductsPage(); qtbot.addWidget(product_page)
    product_page.name.setText(f"اختبار صنف {suffix}")
    product_page.barcode.setText(f"990{suffix[:10]}")
    product_page.purchase.setValue(10)
    product_page.sale.setValue(15)
    product_page.save_product()

    customer_page = CustomersPage(); qtbot.addWidget(customer_page)
    customer_page.code.setText(f"CUS-{suffix}")
    customer_page.name.setText(f"عميل اختبار {suffix}")
    customer_page.save_customer()

    supplier_page = SuppliersPage(); qtbot.addWidget(supplier_page)
    supplier_page.code.setText(f"SUP-{suffix}")
    supplier_page.name.setText(f"مورد اختبار {suffix}")
    supplier_page.save_supplier()

    expense_page = ExpensesPage(); qtbot.addWidget(expense_page)
    expense_page.amount.setValue(25)
    expense_page.description.setText(f"مصروف اختبار {suffix}")
    expense_page.save_expense()

    revenue_page = RevenuesPage(); qtbot.addWidget(revenue_page)
    revenue_page.amount.setValue(40)
    revenue_page.description.setText(f"إيراد اختبار {suffix}")
    revenue_page.save_revenue()

    session = get_session()
    try:
        assert session.scalar(select(Product).where(Product.name == f"اختبار صنف {suffix}")) is not None
        assert session.scalar(select(ProductBarcode).where(ProductBarcode.barcode == f"990{suffix[:10]}")) is not None
        assert session.scalar(select(Customer).where(Customer.code == f"CUS-{suffix}")) is not None
        assert session.scalar(select(Supplier).where(Supplier.code == f"SUP-{suffix}")) is not None
        assert session.scalar(select(Expense).where(Expense.description == f"مصروف اختبار {suffix}")) is not None
        assert session.scalar(select(Revenue).where(Revenue.description == f"إيراد اختبار {suffix}")) is not None
        assert session.scalar(select(ExpenseCategory)) is not None
        assert session.scalar(select(PaymentMethod).where(PaymentMethod.code == "CREDIT")) is not None
    finally:
        session.close()
