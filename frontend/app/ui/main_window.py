from datetime import date
from webbrowser import open as open_url

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy import select

from backend.app.core.database import get_session
from backend.app.core.models import Product, ProductBarcode
from frontend.app.branding import BRANDING
from frontend.app.ui.barcode_scanner import BarcodeScannerWidget
from frontend.app.ui.cashboxes_page import CashboxesPage
from frontend.app.ui.customers_page import CustomersPage
from frontend.app.ui.expenses_page import ExpensesPage
from frontend.app.ui.inventory_page import InventoryPage
from frontend.app.ui.purchases_page import PurchasesPage
from frontend.app.ui.reports_page import ReportsPage
from frontend.app.ui.returns_page import ReturnsPage
from frontend.app.ui.sales_page import SalesPage
from frontend.app.ui.suppliers_page import SuppliersPage
from backend.app.modules.reports.service import ReportService


class SummaryCard(QFrame):
    def __init__(self, title, value, parent=None):
        super().__init__(parent)
        self.setObjectName("summaryCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(6)
        label = QLabel(title)
        label.setObjectName("summaryLabel")
        label.setWordWrap(True)
        layout.addWidget(label)
        self.value_label = QLabel(value)
        self.value_label.setObjectName("cardValue")
        layout.addWidget(self.value_label)


class ModulePage(QFrame):
    back_requested = Signal()

    def __init__(self, title, description, actions, parent=None):
        super().__init__(parent)
        self.setObjectName("panel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(26, 24, 26, 24)
        layout.setSpacing(16)
        heading = QLabel(title)
        heading.setObjectName("pageTitle")
        layout.addWidget(heading)
        text = QLabel(description)
        text.setWordWrap(True)
        text.setObjectName("pageDescription")
        layout.addWidget(text)
        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(12)
        for i, label in enumerate(actions):
            button = QPushButton(label)
            button.setObjectName("actionButton")
            grid.addWidget(button, i // 3, i % 3)
        layout.addLayout(grid)
        layout.addStretch()
        back = QPushButton("العودة إلى الرئيسية")
        back.setObjectName("secondaryButton")
        back.clicked.connect(self.back_requested.emit)
        layout.addWidget(back, alignment=Qt.AlignLeft)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(BRANDING.program_name)
        self.resize(1180, 760)
        self.setMinimumSize(980, 650)
        self.setLayoutDirection(Qt.RightToLeft)
        self._cards = {}
        self._pages = {}
        self._nav_buttons = {}
        self._notification_offset = 0
        self._build_ui()
        self._notification_timer = QTimer(self)
        self._notification_timer.timeout.connect(self._move_notification)
        # Notifications rotate slowly so the user can comfortably read each message.
        self._notification_timer.start(6000)

    def _build_ui(self):
        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(22, 18, 22, 14)
        root_layout.setSpacing(12)

        header = QFrame()
        header.setObjectName("header")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(22, 16, 22, 16)
        hl.setSpacing(12)

        identity = QVBoxLayout()
        identity.setSpacing(3)
        title = QLabel(BRANDING.program_name)
        title.setObjectName("appTitle")
        identity.addWidget(title)
        subtitle = QLabel("إدارة المبيعات والمشتريات والمخزون والحسابات من مكان واحد")
        subtitle.setObjectName("appSubtitle")
        subtitle.setWordWrap(True)
        identity.addWidget(subtitle)
        hl.addLayout(identity, 1)

        self.scanner_toggle = QPushButton("📷 قارئ الباركود")
        self.scanner_toggle.setObjectName("scannerToggle")
        self.scanner_toggle.clicked.connect(self._toggle_scanner)
        hl.addWidget(self.scanner_toggle)

        refresh = QPushButton("تحديث البيانات")
        refresh.setObjectName("primaryButton")
        refresh.clicked.connect(self.refresh_dashboard)
        hl.addWidget(refresh)
        root_layout.addWidget(header)

        nav = QFrame()
        nav.setObjectName("topNavigation")
        nav_layout = QHBoxLayout(nav)
        nav_layout.setContentsMargins(6, 6, 6, 6)
        nav_layout.setSpacing(6)

        specs = {
            "الرئيسية": ("الرئيسية", "لوحة المتابعة والعمليات الرئيسية.", []),
            "المبيعات": ("المبيعات", "إنشاء وإدارة فواتير البيع والتحصيل والمرتجعات.", ["فاتورة بيع جديدة", "مرتجع مبيعات", "سجل المبيعات"]),
            "المشتريات": ("المشتريات", "إدارة فواتير الشراء والموردين والمدفوعات.", ["فاتورة شراء جديدة", "مرتجع مشتريات", "سجل المشتريات"]),
            "المخزون": ("المخزون", "متابعة الأصناف والكميات والحركات وتكلفة المخزون.", ["الأصناف", "حركة المخزون", "جرد المخزون"]),
            "العملاء": ("العملاء", "إدارة بيانات العملاء والأرصدة والتحصيلات.", ["عميل جديد", "قبض من عميل", "كشف حساب"]),
            "الموردون": ("الموردون", "إدارة بيانات الموردين والأرصدة والمدفوعات.", ["مورد جديد", "سداد مورد", "كشف حساب"]),
            "المصروفات": ("المصروفات", "تسجيل ومراجعة المصروفات وربطها بوسيلة الدفع.", ["مصروف جديد", "تصنيفات المصروفات", "سجل المصروفات"]),
            "الصناديق والحسابات": ("الصناديق والحسابات", "متابعة النقد والمحفظة والحساب البنكي والتحويلات بين الحسابات.", ["أرصدة الحسابات", "تحويل بين الحسابات", "سجل الحركات"]),
            "المرتجعات": ("المرتجعات والإلغاءات", "إرجاع المبيعات والمشتريات مع عكس المخزون والحركة المالية دون حذف الفاتورة الأصلية.", ["مرتجع مبيعات", "مرتجع مشتريات", "سجل المرتجعات"]),
            "التقارير": ("التقارير", "تقارير تشغيلية ومالية قابلة للتوسع والطباعة والتصدير.", ["ملخص يومي", "الأرباح والخسائر", "أرصدة العملاء والموردين"]),
        }
        self._specs = specs

        for label in specs:
            button = QPushButton(label)
            button.setObjectName("navButton")
            button.setProperty("active", label == "الرئيسية")
            button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            button.clicked.connect(lambda checked=False, name=label: self._show_page(name))
            nav_layout.addWidget(button)
            self._nav_buttons[label] = button
        root_layout.addWidget(nav)

        ticker = QFrame()
        ticker.setObjectName("notificationBar")
        ticker_layout = QHBoxLayout(ticker)
        ticker_layout.setContentsMargins(12, 5, 12, 5)
        ticker_layout.setSpacing(8)
        notification_title = QLabel("التنبيهات")
        notification_title.setObjectName("notificationTitle")
        ticker_layout.addWidget(notification_title)
        self._notification_label = QLabel()
        self._notification_label.setObjectName("notificationText")
        self._notification_label.setAlignment(Qt.AlignCenter)
        ticker_layout.addWidget(self._notification_label, 1)
        root_layout.addWidget(ticker)
        self._notification_messages = [
            "مرحبًا بك في نظام إدارة البقالات — تابع المبيعات والمشتريات والمخزون والحسابات من مكان واحد",
            "تذكير: راجع الأصناف منخفضة المخزون قبل بدء يوم البيع",
            "تنبيه: احفظ الفواتير واعتمد العمليات المالية بعد مراجعتها",
        ]
        self._notification_label.setText(self._notification_messages[0])

        self.stack = QStackedWidget()
        self.dashboard = self._dashboard_page()
        self.stack.addWidget(self.dashboard)
        self._pages["الرئيسية"] = self.dashboard

        scroll = QScrollArea()
        scroll.setObjectName("contentScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setWidget(self.stack)
        root_layout.addWidget(scroll, 1)

        footer = QFrame()
        footer.setObjectName("footerPanel")
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(10, 5, 10, 5)
        credit = QLabel(f"{BRANDING.designer_credit} | {BRANDING.contact_text}")
        credit.setWordWrap(True)
        fl.addWidget(credit, 1)
        call = QPushButton("☎ اتصال")
        call.setObjectName("linkButton")
        call.clicked.connect(lambda: open_url(BRANDING.phone_uri))
        fl.addWidget(call)
        wa = QPushButton("واتساب")
        wa.setObjectName("linkButton")
        wa.clicked.connect(lambda: open_url(BRANDING.whatsapp_uri))
        fl.addWidget(wa)
        root_layout.addWidget(footer)

        self.setCentralWidget(root)
        self.setStyleSheet(self._stylesheet())

        self.barcode_scanner = BarcodeScannerWidget(root)
        self.barcode_scanner.barcode_detected.connect(self._handle_barcode)
        self.barcode_scanner.hide()

    def _create_page(self, name):
        if name in self._pages:
            return self._pages[name]
        ptitle, desc, actions = self._specs[name]
        if name == "المخزون":
            page = InventoryPage()
        elif name == "المبيعات":
            page = SalesPage()
        elif name == "المشتريات":
            page = PurchasesPage()
        elif name == "العملاء":
            page = CustomersPage()
        elif name == "الموردون":
            page = SuppliersPage()
        elif name == "المصروفات":
            page = ExpensesPage()
        elif name == "الصناديق والحسابات":
            page = CashboxesPage()
        elif name == "المرتجعات":
            page = ReturnsPage()
        elif name == "التقارير":
            page = ReportsPage()
        else:
            page = ModulePage(ptitle, desc, actions)
        if hasattr(page, "back_requested"):
            page.back_requested.connect(self._show_dashboard)
        self._pages[name] = page
        self.stack.addWidget(page)
        return page

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "barcode_scanner"):
            self._position_scanner()

    def _position_scanner(self):
        margin = 18
        x = self.centralWidget().width() - self.barcode_scanner.width() - margin
        y = 210
        self.barcode_scanner.move(max(margin, x), y)
        self.barcode_scanner.raise_()

    def _toggle_scanner(self):
        self._show_page("المبيعات")
        self.barcode_scanner.toggle()
        if self.barcode_scanner.isVisible():
            self._position_scanner()

    def _handle_barcode(self, code):
        sales_page = self._pages.get("المبيعات")
        if sales_page is None or self.stack.currentWidget() is not sales_page:
            return
        session = get_session()
        try:
            product = session.scalar(
                select(Product)
                .join(ProductBarcode, ProductBarcode.product_id == Product.id)
                .where(
                    Product.is_active.is_(True),
                    ProductBarcode.is_active.is_(True),
                    ProductBarcode.barcode == code,
                )
            )
            if product is None:
                self.barcode_scanner.status.setText("الباركود غير مسجل")
                return
            index = sales_page.product.findData(product.id)
            if index < 0:
                self.barcode_scanner.status.setText("الصنف غير متاح للبيع")
                return
            sales_page.product.setCurrentIndex(index)
            sales_page.quantity.setValue(1)
            sales_page.add_line()
            self.barcode_scanner.status.setText(f"تمت إضافة: {product.name}")
            sales_page.product.setFocus()
        finally:
            session.close()

    def _dashboard_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(10, 10, 10, 18)
        layout.setSpacing(18)
        cards = QGridLayout()
        cards.setHorizontalSpacing(14)
        cards.setVerticalSpacing(14)
        for i, (key, label) in enumerate([
            ("sales", "مبيعات اليوم"),
            ("purchases", "مشتريات اليوم"),
            ("expenses", "المصروفات اليوم"),
            ("profit", "صافي الربح"),
            ("receivables", "ذمم العملاء"),
            ("payables", "ذمم الموردين"),
            ("cash", "رصيد الصندوق"),
            ("low", "أصناف منخفضة"),
        ]):
            card = SummaryCard(label, "0.00")
            self._cards[key] = card
            cards.addWidget(card, i // 4, i % 4)
        layout.addLayout(cards)

        quick = QFrame()
        quick.setObjectName("panel")
        ql = QVBoxLayout(quick)
        ql.setContentsMargins(20, 18, 20, 18)
        ql.setSpacing(14)
        h = QLabel("العمليات الرئيسية")
        h.setObjectName("pageTitle")
        ql.addWidget(h)
        row = QGridLayout()
        row.setHorizontalSpacing(12)
        row.setVerticalSpacing(12)
        for i, (label, target) in enumerate([
            ("فاتورة بيع جديدة", "المبيعات"),
            ("فاتورة شراء جديدة", "المشتريات"),
            ("إضافة صنف", "المخزون"),
            ("قبض من عميل", "العملاء"),
            ("سداد مورد", "الموردون"),
            ("تسجيل مصروف", "المصروفات"),
            ("الصناديق والحسابات", "الصناديق والحسابات"),
            ("المرتجعات", "المرتجعات"),
        ]):
            button = QPushButton(label)
            button.setObjectName("actionButton")
            button.clicked.connect(lambda checked=False, name=target: self._show_page(name))
            row.addWidget(button, i // 4, i % 4)
        ql.addLayout(row)
        layout.addWidget(quick)
        layout.addStretch()
        return page

    def _show_dashboard(self):
        self._show_page("الرئيسية")

    def _show_page(self, name):
        page = self._create_page(name)
        if hasattr(page, "refresh"):
            page.refresh()
        self.stack.setCurrentWidget(page)
        for label, button in self._nav_buttons.items():
            button.setProperty("active", label == name)
            button.style().unpolish(button)
            button.style().polish(button)
        if name == "المبيعات" and self.barcode_scanner.isVisible():
            self._position_scanner()
        elif name != "المبيعات":
            self.barcode_scanner.hide()

    def _move_notification(self):
        if not self._notification_messages:
            return
        text = self._notification_messages[self._notification_offset % len(self._notification_messages)]
        self._notification_label.setText(text)
        self._notification_offset += 1

    def refresh_dashboard(self):
        session = get_session()
        try:
            today = date.today().isoformat()
            s = ReportService(session).dashboard_summary(date_from=today, date_to=today)
            reports = ReportService(session).dashboard_summary(date_from=today, date_to=today)
            self._cards["sales"].value_label.setText(f"{s['sales_total']:.2f}")
            self._cards["purchases"].value_label.setText(f"{s['purchases_total']:.2f}")
            self._cards["expenses"].value_label.setText(f"{s['expenses_total']:.2f}")
            self._cards["profit"].value_label.setText(f"{s['profit']:.2f}")
            self._cards["receivables"].value_label.setText(f"{s['receivables']:.2f}")
            self._cards["payables"].value_label.setText(f"{s['payables']:.2f}")
            self._cards["cash"].value_label.setText(f"{s['cash_balance']:.2f}")
            self._cards["low"].value_label.setText(str(s['low_stock_count']))
        finally:
            session.close()

    def _stylesheet(self):
        return """
        QWidget { font-family: 'Noto Sans Arabic'; font-size: 13px; }
        QMainWindow { background: #f4f7fb; }
        #header { background: #0f4c81; border-radius: 12px; }
        #appTitle { color: white; font-size: 24px; font-weight: 700; }
        #appSubtitle { color: #e6eef7; font-size: 13px; }
        #topNavigation { background: white; border: 1px solid #d7e0ea; border-radius: 10px; }
        #navButton { min-height: 42px; padding: 8px 12px; border: none; border-radius: 8px; background: #eef3f8; color: #19324d; font-weight: 600; }
        #navButton[active="true"] { background: #0f4c81; color: white; }
        #notificationBar { background: #fff8e1; border: 1px solid #efd27b; border-radius: 8px; min-height: 34px; }
        #notificationTitle { font-weight: 700; color: #7a5a00; }
        #notificationText { color: #5b4700; font-size: 13px; }
        #contentScroll { background: transparent; }
        #panel { background: white; border: 1px solid #d7e0ea; border-radius: 12px; }
        #summaryCard { background: white; border: 1px solid #d7e0ea; border-radius: 12px; }
        #summaryLabel { color: #5c6b7a; font-weight: 600; }
        #cardValue { color: #153b5c; font-size: 21px; font-weight: 700; }
        #pageTitle { color: #173b5c; font-size: 20px; font-weight: 700; }
        #pageDescription { color: #617386; font-size: 13px; }
        QPushButton { min-height: 38px; padding: 8px 14px; border-radius: 8px; }
        #primaryButton { background: #1f7a4d; color: white; border: none; }
        #scannerToggle { background: #ffffff; color: #173b5c; border: 1px solid #cbd7e3; }
        #actionButton { background: #e9f1f8; color: #173b5c; border: 1px solid #c7d6e4; }
        #secondaryButton { background: #f1f4f7; color: #3f5368; border: 1px solid #cbd7e3; }
        #footerPanel { background: white; border-top: 1px solid #d7e0ea; }
        #linkButton { background: transparent; color: #0f4c81; border: none; min-height: 30px; }
        QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit, QTableWidget, QPlainTextEdit, QTextEdit {
            min-height: 36px; padding: 6px 8px; border: 1px solid #c7d6e4; border-radius: 7px; background: white;
        }
        QHeaderView::section { padding: 8px; font-weight: 700; }
        QTableWidget { gridline-color: #dce5ee; }
        """
