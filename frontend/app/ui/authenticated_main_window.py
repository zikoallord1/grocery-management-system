from datetime import datetime

from PySide6.QtCore import QTimer, Signal, Qt
from PySide6.QtWidgets import QLabel, QCompleter

from frontend.app.ui.main_window import MainWindow


class AuthenticatedMainWindow(MainWindow):
    logout_requested = Signal()

    def __init__(self, user=None):
        self.current_user = user or {}
        super().__init__()

        header = self.findChild(QLabel, "appTitle")
        if header is not None:
            parent_layout = header.parentWidget().parentWidget().layout()
            parent_layout.addWidget(QLabel(f"المستخدم: {self.current_user.get('full_name') or self.current_user.get('username', '')}"))
            from PySide6.QtWidgets import QPushButton
            self.logout_button = QPushButton("⎋ خروج من المستخدم")
            self.logout_button.setObjectName("logoutButton")
            self.logout_button.clicked.connect(self.logout_requested.emit)
            parent_layout.addWidget(self.logout_button)

        # Products are a first-class top navigation tab immediately after Purchases.
        nav = self.findChild(QFrame, "topNavigation")
        if nav is not None and "الأصناف" in self._nav_buttons:
            nav_layout = nav.layout()
            product_button = self._nav_buttons["الأصناف"]
            nav_layout.removeWidget(product_button)
            purchases_button = self._nav_buttons.get("المشتريات")
            if purchases_button is not None:
                index = nav_layout.indexOf(purchases_button)
                nav_layout.insertWidget(index + 1, product_button)

        # Product selectors accept normal typing and USB barcode scanners as keyboard input.
        sales_page = self._create_page("المبيعات")
        sales_page.product.setEditable(True)
        sales_page.product.setInsertPolicy(sales_page.product.NoInsert)
        sales_page.product.lineEdit().setPlaceholderText("اكتب اسم الصنف أو استخدم قارئ الباركود الخارجي...")
        completer = QCompleter(sales_page.product.model(), sales_page.product)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setFilterMode(Qt.MatchContains)
        sales_page.product.setCompleter(completer)

        inventory_page = self._create_page("المخزون")
        for selector in (inventory_page.product, inventory_page.transfer_product, inventory_page.adjustment_product):
            selector.setEditable(True)
            selector.setInsertPolicy(selector.NoInsert)
            selector.lineEdit().setPlaceholderText("اكتب اسم الصنف أو اختره من القائمة...")
            selector_completer = QCompleter(selector.model(), selector)
            selector_completer.setCaseSensitivity(Qt.CaseInsensitive)
            selector_completer.setFilterMode(Qt.MatchContains)
            selector.setCompleter(selector_completer)

        footer = self.centralWidget().layout().itemAt(self.centralWidget().layout().count() - 1).widget()
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
