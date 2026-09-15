from datetime import datetime

from PySide6.QtCore import QTimer, Signal, Qt
from PySide6.QtWidgets import QLabel, QPushButton, QCompleter

from frontend.app.ui.main_window import MainWindow


class AuthenticatedMainWindow(MainWindow):
    logout_requested = Signal()

    def __init__(self, user=None):
        self.current_user = user or {}
        super().__init__()

        # Current session controls: user identity + explicit logout.
        header = self.centralWidget().layout().itemAt(0).widget()
        header.layout().addWidget(QLabel(f"المستخدم: {self.current_user.get('full_name') or self.current_user.get('username', '')}"))
        self.logout_button = QPushButton("⎋ خروج من المستخدم")
        self.logout_button.setObjectName("logoutButton")
        self.logout_button.clicked.connect(self.logout_requested.emit)
        header.layout().addWidget(self.logout_button)

        # Always expose product management as a first-class navigation item.
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

        # Sales and inventory selectors support direct typing/search by product name.
        sales_page = self._create_page("المبيعات")
        for selector in (sales_page.product,):
            selector.setEditable(True)
            selector.setInsertPolicy(selector.NoInsert)
            selector.lineEdit().setPlaceholderText("اكتب اسم الصنف أو اختره من القائمة...")
            completer = QCompleter(selector.model(), selector)
            completer.setCaseSensitivity(Qt.CaseInsensitive)
            completer.setFilterMode(Qt.MatchContains)
            selector.setCompleter(completer)

        inventory_page = self._create_page("المخزون")
        for selector in (inventory_page.product, inventory_page.transfer_product, inventory_page.adjustment_product):
            selector.setEditable(True)
            selector.setInsertPolicy(selector.NoInsert)
            selector.lineEdit().setPlaceholderText("اكتب اسم الصنف أو اختره من القائمة...")
            completer = QCompleter(selector.model(), selector)
            completer.setCaseSensitivity(Qt.CaseInsensitive)
            completer.setFilterMode(Qt.MatchContains)
            selector.setCompleter(completer)

        # Compact footer: credit on the left, live date/time on the other side.
        root_layout = self.centralWidget().layout()
        footer = root_layout.itemAt(root_layout.count() - 1).widget()
        footer.setMaximumHeight(36)
        footer_layout = footer.layout()
        if footer_layout is not None:
            footer_layout.setContentsMargins(8, 2, 8, 2)
            while footer_layout.count() > 1:
                item = footer_layout.takeAt(1)
                widget = item.widget()
                if widget is not None:
                    widget.hide()
                    widget.deleteLater()
            credit = footer_layout.itemAt(0).widget()
            if credit is not None:
                credit.setText(f"{self._safe_credit()}")
                credit.setWordWrap(False)
                credit.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.clock_label = QLabel()
            self.clock_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.clock_label.setObjectName("footerClock")
            footer_layout.addWidget(self.clock_label, 0)
            self._clock_timer = QTimer(self)
            self._clock_timer.timeout.connect(self._update_footer_clock)
            self._clock_timer.start(1000)
            self._update_footer_clock()

    def _safe_credit(self):
        from frontend.app.branding import BRANDING
        return f"{BRANDING.designer_credit} | {BRANDING.contact_text}"

    def _update_footer_clock(self):
        now = datetime.now()
        self.clock_label.setText(f"{now:%Y-%m-%d}  |  {now:%H:%M:%S}")
