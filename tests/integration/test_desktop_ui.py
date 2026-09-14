import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from backend.app.core.database import initialize_database
from frontend.app.ui.cashboxes_page import CashboxesPage
from frontend.app.ui.customers_page import CustomersPage
from frontend.app.ui.expenses_page import ExpensesPage
from frontend.app.ui.inventory_page import InventoryPage
from frontend.app.ui.main_window import MainWindow
from frontend.app.ui.products_page import ProductsPage
from frontend.app.ui.purchases_page import PurchasesPage
from frontend.app.ui.reports_page import ReportsPage
from frontend.app.ui.returns_page import ReturnsPage
from frontend.app.ui.sales_page import SalesPage
from frontend.app.ui.suppliers_page import SuppliersPage


def test_main_window_builds_in_offscreen_mode():
    initialize_database()
    app = QApplication.instance() or QApplication([])
    window = MainWindow()

    assert window.windowTitle() == "نظام إدارة البقالات"
    assert window.layoutDirection() == Qt.RightToLeft
    assert isinstance(window._pages["المخزون"], InventoryPage)
    assert window._pages["المخزون"].balance_table.columnCount() == 6
    assert window._pages["المخزون"].movement_table.columnCount() == 7
    assert isinstance(window._pages["المبيعات"], SalesPage)
    assert window._pages["المبيعات"].product is not None
    assert isinstance(window._pages["المشتريات"], PurchasesPage)
    assert window._pages["المشتريات"].history.columnCount() == 7
    assert window._pages["المشتريات"].product is not None
    assert isinstance(window._pages["العملاء"], CustomersPage)
    assert isinstance(window._pages["الموردون"], SuppliersPage)
    assert window._pages["الموردون"].table.columnCount() == 5
    assert isinstance(window._pages["المصروفات"], ExpensesPage)
    assert window._pages["المصروفات"].table.columnCount() == 6
    assert isinstance(window._pages["الصناديق والحسابات"], CashboxesPage)
    assert window._pages["الصناديق والحسابات"].cashboxes_table.columnCount() == 5
    assert window._pages["الصناديق والحسابات"].movements_table.columnCount() == 6
    assert isinstance(window._pages["المرتجعات"], ReturnsPage)
    assert isinstance(window._pages["التقارير"], ReportsPage)
    assert window._pages["التقارير"].table.columnCount() == 2

    products = ProductsPage()
    assert products.table.columnCount() == 7
    assert products.barcode is not None
    assert products.category is not None
    assert products.selected_product_id is None
    products.close()

    window.close()
    app.processEvents()
