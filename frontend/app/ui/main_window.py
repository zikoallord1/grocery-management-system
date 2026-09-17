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

from backend.app.core.database import get_session
from backend.app.modules.reports.service import ReportService
from frontend.app.branding import BRANDING
from frontend.app.ui.cashboxes_page import CashboxesPage
from frontend.app.ui.customers_page import CustomersPage
from frontend.app.ui.expenses_page import ExpensesPage
from frontend.app.ui.inventory_page import InventoryPage
from frontend.app.ui.products_page import ProductsPage
from frontend.app.ui.purchases_page import PurchasesPage
from frontend.app.ui.reports_page import ReportsPage
from frontend.app.ui.returns_page import ReturnsPage
from frontend.app.ui.sales_page import SalesPage
from frontend.app.ui.settings_page import SettingsPage
from frontend.app.ui.suppliers_page import SuppliersPage


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
    """Main RTL shell: RIGHT navigation, LEFT content, with a true scrolling ticker."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle(BRANDING.program_name)
        self.resize(1180, 760)
        self.setMinimumSize(900, 600)
        self.setLayoutDirection(Qt.RightToLeft)
        self._cards = {}
        self._pages = {}
        self._nav_buttons = {}
        self._notification_offset = 0
        self._notification_index = 0
        self._notification_x = 0
        self._build_ui()
        self._notification_timer = QTimer(self)
        self._notification_timer.timeout.connect(self._move_notification)
        self._notification_timer.start(35)
        self.refresh_dashboard()

    def _build_ui(self):
        root = QWidget()
        root.setLayoutDirection(Qt.RightToLeft)
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(16, 14, 16, 10)
        root_layout.setSpacing(10)

        header = QFrame()
        header.setObjectName("header")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(20, 13, 20, 13)
        hl.setSpacing(12)
        identity = QVBoxLayout()
        identity.setSpacing(2)
        title = QLabel(BRANDING.program_name)
        title.setObjectName("appTitle")
        identity.addWidget(title)
        subtitle = QLabel("إدارة المبيعات والمشتريات والمخزون والحسابات من مكان واحد")
        subtitle.setObjectName("appSubtitle")
        subtitle.setWordWrap(True)
        identity.addWidget(subtitle)
        hl.addLayout(identity, 1)
        refresh = QPushButton("تحديث البيانات")
        refresh.setObjectName("primaryButton")
        refresh.clicked.connect(self.refresh_dashboard)
        hl.addWidget(refresh)
        root_layout.addWidget(header)

        specs = {
            "الرئيسية": ("الرئيسية", "لوحة المتابعة والعمليات الرئيسية.", []),
            "المبيعات": ("المبيعات", "إنشاء وإدارة فواتير البيع والتحصيل والمرتجعات.", ["فاتورة بيع جديدة", "مرتجع مبيعات", "سجل المبيعات"]),
            "المشتريات": ("المشتريات", "إدارة فواتير الشراء والموردين والمدفوعات.", ["فاتورة شراء جديدة", "مرتجع مشتريات", "سجل المشتريات"]),
            "الأصناف": ("الأصناف", "إضافة وتعديل الأصناف والباركود والأسعار والحد الأدنى للمخزون.", ["إضافة صنف", "تعديل صنف", "بحث عن صنف"]),
            "المخزون": ("المخزون", "متابعة الكميات والحركات وتكلفة المخزون والجرد.", ["حركة المخزون", "جرد المخزون", "تحويل مخزني"]),
            "العملاء": ("العملاء", "إدارة بيانات العملاء والأرصدة والتحصيلات.", ["عميل جديد", "قبض من عميل", "كشف حساب"]),
            "الموردون": ("الموردون", "إدارة بيانات الموردين والأرصدة والمدفوعات.", ["مورد جديد", "سداد مورد", "كشف حساب"]),
            "المصروفات": ("المصروفات", "تسجيل ومراجعة المصروفات وربطها بوسيلة الدفع.", ["مصروف جديد", "تصنيفات المصروفات", "سجل المصروفات"]),
            "الصناديق والحسابات": ("الصناديق والحسابات", "متابعة النقد والمحفظة والحساب البنكي والتحويلات بين الحسابات.", ["أرصدة الحسابات", "تحويل بين الحسابات", "سجل الحركات"]),
            "المرتجعات": ("المرتجعات والإلغاءات", "إرجاع المبيعات والمشتريات مع عكس المخزون والحركة المالية دون حذف الفاتورة الأصلية.", ["مرتجع مبيعات", "مرتجع مشتريات", "سجل المرتجعات"]),
            "التقارير": ("التقارير", "تقارير تشغيلية ومالية قابلة للتوسع والطباعة والتصدير.", ["ملخص يومي", "الأرباح والخسائر", "أرصدة العملاء والموردين"]),
            "الإعدادات": ("الإعدادات", "إعدادات البقالة والمستخدمين والصلاحيات وتسجيل النسخة.", ["بيانات البقالة", "المستخدمون والصلاحيات", "تسجيل النسخة"]),
        }
        self._specs = specs

        ticker = QFrame()
        ticker.setObjectName("notificationBar")
        ticker_layout = QHBoxLayout(ticker)
        ticker_layout.setContentsMargins(10, 4, 10, 4)
        ticker_layout.setSpacing(8)
        notification_title = QLabel("التنبيهات")
        notification_title.setObjectName("notificationTitle")
        ticker_layout.addWidget(notification_title)

        self._notification_viewport = QFrame()
        self._notification_viewport.setObjectName("notificationViewport")
        self._notification_viewport.setMinimumHeight(26)
        self._notification_viewport.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        ticker_layout.addWidget(self._notification_viewport, 1)

        self._notification_label = QLabel()
        self._notification_label.setObjectName("notificationText")
        self._notification_label.setWordWrap(False)
        self._notification_label.setAlignment(Qt.AlignVCenter | Qt.AlignRight)
        self._notification_label.setParent(self._notification_viewport)

        root_layout.addWidget(ticker)
        self._notification_messages = [
            "مرحبًا بك في نظام إدارة البقالات — تابع المبيعات والمشتريات والمخزون والحسابات من مكان واحد",
            "تذكير: راجع الأصناف منخفضة المخزون قبل بدء يوم البيع",
            "تنبيه: احفظ الفواتير واعتمد العمليات المالية بعد مراجعتها",
            f"{BRANDING.program_name} — {BRANDING.designer_credit}",
            f"حقوق التصميم والتنفيذ محفوظة — {BRANDING.contact_text}",
            f"للتواصل وطلب البرنامج أو المساعدة: {BRANDING.phone_display} — واتساب متاح",
        ]
        self._notification_text = self._notification_messages[0]
        self._notification_label.setText(self._notification_text)

        # RTL shell: adding navigation first and content second places the navigation rail physically on the RIGHT.
        shell = QHBoxLayout()
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(12)
        shell.setDirection(QHBoxLayout.RightToLeft)

        nav_scroll = QScrollArea()
        nav_scroll.setObjectName("topNavigationScroll")
        nav_scroll.setWidgetResizable(True)
        nav_scroll.setFrameShape(QFrame.NoFrame)
        nav_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        nav_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        nav_scroll.setFixedWidth(205)

        nav = QFrame()
        nav.setObjectName("topNavigation")
        nav.setLayoutDirection(Qt.RightToLeft)
        nav_layout = QVBoxLayout(nav)
        nav_layout.setContentsMargins(8, 8, 8, 8)
        nav_layout.setSpacing(6)
        for label in specs:
            button = QPushButton(label)
            button.setObjectName("navButton")
            button.setProperty("active", label == "الرئيسية")
            button.setMinimumHeight(45)
            button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            button.clicked.connect(lambda checked=False, name=label: self._show_page(name))
            nav_layout.addWidget(button)
            self._nav_buttons[label] = button
        nav_layout.addStretch(1)
        nav_scroll.setWidget(nav)

        content_panel = QFrame()
        content_panel.setObjectName("contentPanel")
        content_panel.setLayoutDirection(Qt.RightToLeft)
        content_layout = QVBoxLayout(content_panel)
        content_layout.setContentsMargins(0, 0, 0, 0)

        self.stack = QStackedWidget()
        self.dashboard = self._dashboard_page()
        self.stack.addWidget(self.dashboard)
        self._pages["الرئيسية"] = self.dashboard

        content_scroll = QScrollArea()
        content_scroll.setObjectName("contentScroll")
        content_scroll.setWidgetResizable(True)
        content_scroll.setFrameShape(QFrame.NoFrame)
        content_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        content_scroll.setWidget(self.stack)
        content_layout.addWidget(content_scroll)

        # Physical layout required by the reference: content on LEFT, navigation on RIGHT.
        shell.addWidget(content_panel, 1)
        shell.addWidget(nav_scroll, 0)
        root_layout.addLayout(shell, 1)

        footer = QFrame()
        footer.setObjectName("footerPanel")
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(8, 3, 8, 3)
        credit = QLabel(f"{BRANDING.designer_credit} | {BRANDING.contact_text}")
        credit.setWordWrap(False)
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
        self._reset_notification_position()

    def _create_page(self, name):
        if name in self._pages:
            return self._pages[name]
        ptitle, desc, actions = self._specs[name]
        if name == "الأصناف":
            page = ProductsPage()
        elif name == "المخزون":
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
        elif name == "الإعدادات":
            page = SettingsPage()
        else:
            page = ModulePage(ptitle, desc, actions)
        if hasattr(page, "back_requested"):
            page.back_requested.connect(self._show_dashboard)
        self._pages[name] = page
        self.stack.addWidget(page)
        return page

    def _dashboard_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(10, 10, 10, 18)
        layout.setSpacing(16)
        cards = QGridLayout()
        cards.setHorizontalSpacing(12)
        cards.setVerticalSpacing(12)
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
        ql.setContentsMargins(18, 16, 18, 16)
        ql.setSpacing(12)
        h = QLabel("العمليات الرئيسية")
        h.setObjectName("pageTitle")
        ql.addWidget(h)
        row = QGridLayout()
        row.setHorizontalSpacing(10)
        row.setVerticalSpacing(10)
        for i, (label, target) in enumerate([
            ("فاتورة بيع جديدة", "المبيعات"),
            ("فاتورة شراء جديدة", "المشتريات"),
            ("إضافة صنف", "الأصناف"),
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

    def _reset_notification_position(self):
        if not hasattr(self, "_notification_viewport"):
            return
        self._notification_label.adjustSize()
        self._notification_x = self._notification_viewport.width()
        self._notification_label.move(self._notification_x, 0)

    def _move_notification(self):
        if not self._notification_messages or not hasattr(self, "_notification_viewport"):
            return
        viewport_width = self._notification_viewport.width()
        if viewport_width <= 0:
            return
        self._notification_label.adjustSize()
        label_width = self._notification_label.width()
        if label_width <= 0:
            return
        self._notification_x -= 2
        if self._notification_x + label_width < 0:
            self._notification_index = (self._notification_index + 1) % len(self._notification_messages)
            self._notification_text = self._notification_messages[self._notification_index]
            self._notification_label.setText(self._notification_text)
            self._notification_label.adjustSize()
            label_width = self._notification_label.width()
            self._notification_x = viewport_width
        self._notification_label.move(int(self._notification_x), 0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "_notification_viewport"):
            if self._notification_x > self._notification_viewport.width():
                self._notification_x = self._notification_viewport.width()
            self._notification_label.adjustSize()
            self._notification_label.move(int(self._notification_x), 0)

    def refresh_dashboard(self):
        session = get_session()
        try:
            today = date.today().isoformat()
            s = ReportService(session).dashboard_summary(date_from=today, date_to=today)
            reports = ReportService(session)
            values = {
                "sales": s.sales_total,
                "purchases": s.purchases_total,
                "expenses": s.expenses_total,
                "profit": s.gross_profit - s.expenses_total,
                "receivables": s.customer_receivables,
                "payables": s.supplier_payables,
                "cash": s.cash_balance,
                "low": reports.low_stock_count(),
            }
            for key, value in values.items():
                self._cards[key].value_label.setText(
                    str(int(value)) if key == "low" else f"{value:,.2f}"
                )
        finally:
            session.close()

    def closeEvent(self, event):
        if hasattr(self, "_notification_timer"):
            self._notification_timer.stop()
        super().closeEvent(event)

    @staticmethod
    def _stylesheet():
        return """
        QWidget { font-family: 'Noto Sans Arabic', 'Segoe UI', Tahoma, Arial; font-size: 14px; }
        QMainWindow { background: #f5f7fb; }
        #header { background: #17324d; border-radius: 12px; }
        #appTitle { color: white; font-size: 24px; font-weight: 700; }
        #appSubtitle { color: #dce8f2; font-size: 13px; }
        #topNavigationScroll { background: transparent; border: none; }
        #topNavigation { background: white; border: 1px solid #dbe3ec; border-radius: 11px; }
        #navButton { min-height: 45px; padding: 0 10px; border-radius: 8px; background: #17324d; color: white; border: none; text-align: right; }
        #navButton:hover { background: #254b6c; }
        #navButton[active="true"] { background: #2d6a9f; font-weight: 700; }
        #notificationBar { background: #eaf1f7; border: 1px solid #cbd9e6; border-radius: 8px; min-height: 34px; }
        #notificationViewport { background: transparent; border: none; min-height: 26px; max-height: 26px; overflow: hidden; }
        #notificationTitle { color: #17324d; font-weight: 700; min-width: 65px; }
        #notificationText { color: #294b67; font-size: 13px; min-width: 1px; }
        #contentPanel { background: transparent; }
        #summaryCard, #panel { background: white; border: 1px solid #dbe3ec; border-radius: 10px; }
        #summaryCard { min-height: 88px; }
        #summaryLabel { color: #61758a; }
        #cardValue { font-size: 22px; font-weight: 700; color: #17324d; }
        #pageTitle { font-size: 20px; font-weight: 700; color: #17324d; }
        #pageDescription { color: #61758a; font-size: 14px; }
        QPushButton { min-height: 40px; padding: 0 14px; border-radius: 7px; border: 1px solid #cbd5df; background: white; }
        QPushButton:hover { border-color: #8fa6b8; }
        #primaryButton { background: #17324d; color: white; border: none; }
        #secondaryButton { background: #eef2f6; }
        #actionButton { min-height: 48px; padding: 0 12px; }
        #linkButton { border: none; background: transparent; color: #17324d; }
        #dangerButton { background: #fff0f0; border-color: #e0a4a4; }
        #footerPanel { min-height: 28px; max-height: 34px; }
        """
