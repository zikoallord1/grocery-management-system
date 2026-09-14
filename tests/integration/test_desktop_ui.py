import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from backend.app.core.database import initialize_database
from frontend.app.ui.inventory_page import InventoryPage
from frontend.app.ui.main_window import MainWindow
from frontend.app.ui.sales_page import SalesPage


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

    window.close()
    app.processEvents()
