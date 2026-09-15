from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLabel, QPushButton
from frontend.app.ui.main_window import MainWindow

class AuthenticatedMainWindow(MainWindow):
    logout_requested = Signal()
    def __init__(self, user=None):
        self.current_user = user or {}
        super().__init__()
        header = self.centralWidget().layout().itemAt(0).widget()
        header.layout().addWidget(QLabel(f"المستخدم: {self.current_user.get('full_name') or self.current_user.get('username', '')}"))
        self.logout_button = QPushButton("⎋ خروج")
        self.logout_button.setObjectName("logoutButton")
        self.logout_button.clicked.connect(self.logout_requested.emit)
        header.layout().addWidget(self.logout_button)
        from frontend.app.ui.products_page import ProductsPage
        page = ProductsPage()
        if hasattr(page, "back_requested"):
            page.back_requested.connect(self._show_dashboard)
        self._pages["الأصناف"] = page
        self._specs["الأصناف"] = ("الأصناف", "إضافة وتعديل الأصناف والباركود والأسعار والمخزون.", [])
        self.stack.addWidget(page)
        nav = self.centralWidget().layout().itemAt(1).widget()
        button = QPushButton("الأصناف")
        button.setObjectName("navButton")
        button.clicked.connect(lambda checked=False: self._show_page("الأصناف"))
        nav.layout().insertWidget(0, button)
        self._nav_buttons["الأصناف"] = button
