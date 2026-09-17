from datetime import datetime

from PySide6.QtCore import QTimer, Signal, Qt
from PySide6.QtWidgets import QLabel, QPushButton, QCompleter, QScrollArea, QFrame, QHBoxLayout, QSizePolicy

from frontend.app.ui.main_window import MainWindow


class AuthenticatedMainWindow(MainWindow):
    logout_requested = Signal()

    def __init__(self, user=None):
        self.current_user = user or {}
        super().__init__()
        self._finish_authenticated_design()

    def _finish_authenticated_design(self):
        root = self.centralWidget()
        root_layout = root.layout()
        if root_layout is None:
            return

        header = root_layout.itemAt(0).widget()
        header_layout = header.layout()
        if header_layout is not None:
            header_layout.addWidget(QLabel(f"المستخدم: {self.current_user.get('full_name') or self.current_user.get('username', '')}"))
            self.license_button = QPushButton("🔑 الترخيص")
            self.license_button.setObjectName("licenseButton")
            self.license_button.clicked.connect(self._open_license_dialog)
            header_layout.addWidget(self.license_button)
            self.logout_button = QPushButton("⎋ خروج")
            self.logout_button.setObjectName("logoutButton")
            self.logout_button.clicked.connect(self.logout_requested.emit)
            header_layout.addWidget(self.logout_button)

        body = root_layout.itemAt(2).widget()
        body_layout = body.layout() if body else None
        if body_layout is not None:
            sidebar = body_layout.itemAt(0).widget()
            if sidebar:
                sidebar.hide()
            extra = body_layout.itemAt(2).layout()
            if extra:
                for i in range(extra.count()):
                    w = extra.itemAt(i).widget()
                    if w:
                        w.hide()

        self._specs["المصروفات"] = ("المصروفات", "إدارة المصروفات والحركات والمرفقات.", ["مصروف جديد", "سجل المصروفات", "كشف المصروفات"])

        nav_host = QWidget()
        nav_host.setObjectName("topNavigation")
        nav_layout = QHBoxLayout(nav_host)
        nav_layout.setContentsMargins(6, 5, 6, 5)
        nav_layout.setSpacing(5)
        nav_host.setLayoutDirection(Qt.RightToLeft)
        names = [
            "الرئيسية", "المبيعات", "المشتريات", "الأصناف", "المخزون",
            "العملاء", "الموردون", "المصروفات", "الصناديق والحسابات",
            "التقارير", "الإعدادات", "مراقبة الكاميرات"
        ]
        for name in names:
            b = QPushButton(name)
            b.setObjectName("topNavButton")
            b.setProperty("active", name == "الرئيسية")
            b.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
            b.clicked.connect(lambda checked=False, n=name: self._show_page(n))
            nav_layout.addWidget(b)
            self._nav_buttons[name] = b
        nav_layout.addStretch(1)

        nav_scroll = QScrollArea()
        nav_scroll.setObjectName("topNavScroll")
        nav_scroll.setWidgetResizable(True)
        nav_scroll.setFrameShape(QFrame.NoFrame)
        nav_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        nav_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        nav_scroll.setWidget(nav_host)
        root_layout.insertWidget(2, nav_scroll, 0)

        footer = root_layout.itemAt(root_layout.count() - 1).widget()
        if footer:
            footer.setMaximumHeight(36)
            fl = footer.layout()
            if fl:
                fl.setContentsMargins(8, 2, 8, 2)
                while fl.count() > 1:
                    item = fl.takeAt(1)
                    w = item.widget()
                    if w:
                        w.hide()
                        w.deleteLater()
                credit = fl.itemAt(0).widget()
                if credit:
                    credit.setText(self._safe_credit())
                    credit.setWordWrap(False)
                self.clock_label = QLabel()
                self.clock_label.setObjectName("footerClock")
                self.clock_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                fl.addWidget(self.clock_label)
                self._clock_timer = QTimer(self)
                self._clock_timer.timeout.connect(self._update_footer_clock)
                self._clock_timer.start(1000)
                self._update_footer_clock()

        sales_page = self._create_page("المبيعات")
        if hasattr(sales_page, "product"):
            selector = sales_page.product
            selector.setEditable(True)
            selector.setInsertPolicy(selector.NoInsert)
            selector.lineEdit().setPlaceholderText("اكتب اسم الصنف أو اختره من القائمة...")
            selector.setCompleter(self._completer(selector))
        inventory_page = self._create_page("المخزون")
        for selector in (getattr(inventory_page, "product", None), getattr(inventory_page, "transfer_product", None), getattr(inventory_page, "adjustment_product", None)):
            if selector is not None:
                selector.setEditable(True)
                selector.setInsertPolicy(selector.NoInsert)
                selector.lineEdit().setPlaceholderText("اكتب اسم الصنف أو اختره من القائمة...")
                selector.setCompleter(self._completer(selector))

        self.setStyleSheet(self.styleSheet() + self._authenticated_styles())

    @staticmethod
    def _completer(selector):
        c = QCompleter(selector.model(), selector)
        c.setCaseSensitivity(Qt.CaseInsensitive)
        c.setFilterMode(Qt.MatchContains)
        return c

    def _open_license_dialog(self):
        from frontend.app.ui.license_dialog import LicenseDialog
        dialog = LicenseDialog(self)
        dialog.setAttribute(Qt.WA_DeleteOnClose, True)
        dialog.setWindowModality(Qt.ApplicationModal)
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()
        self.license_dialog = dialog

    def _safe_credit(self):
        from frontend.app.branding import BRANDING
        return f"{BRANDING.designer_credit} | {BRANDING.contact_text}"

    def _update_footer_clock(self):
        self.clock_label.setText(f"{datetime.now():%Y-%m-%d  |  %H:%M:%S}")

    @staticmethod
    def _authenticated_styles():
        return """
        #topNavigation { background: #063b70; border: 1px solid #0a65ad; border-radius: 8px; }
        #topNavScroll { background: transparent; border: none; min-height: 52px; max-height: 58px; }
        #topNavButton { min-height: 40px; padding: 0 15px; background: transparent; color: white; border: 1px solid transparent; border-radius: 7px; font-weight: 700; }
        #topNavButton:hover { background: #0c5b9e; border-color: #2b9fff; }
        #topNavButton[active="true"] { background: #087cf2; border-color: #49b0ff; font-weight: 800; }
        #licenseButton, #logoutButton { min-height: 32px; background: #087cf2; color: white; border: 1px solid #49b0ff; border-radius: 6px; padding: 0 10px; }
        #logoutButton { background: #07559a; }
        #footerClock { color: white; font-weight: 700; font-size: 11px; }
        """
