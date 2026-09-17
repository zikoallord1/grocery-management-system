from datetime import date
from webbrowser import open as open_url

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QMainWindow, QPushButton,
    QScrollArea, QSizePolicy, QStackedWidget, QVBoxLayout, QWidget,
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
        layout.setContentsMargins(16, 13, 16, 13)
        layout.setSpacing(5)
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
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(14)
        heading = QLabel(title); heading.setObjectName("pageTitle"); layout.addWidget(heading)
        text = QLabel(description); text.setWordWrap(True); text.setObjectName("pageDescription"); layout.addWidget(text)
        grid = QGridLayout(); grid.setHorizontalSpacing(10); grid.setVerticalSpacing(10)
        for i, label in enumerate(actions):
            button = QPushButton(label); button.setObjectName("actionButton"); grid.addWidget(button, i // 3, i % 3)
        layout.addLayout(grid); layout.addStretch()
        back = QPushButton("العودة إلى الرئيسية"); back.setObjectName("secondaryButton")
        back.clicked.connect(self.back_requested.emit); layout.addWidget(back, alignment=Qt.AlignLeft)


class MainWindow(QMainWindow):
    """Arabic RTL shell: content LEFT, navigation RIGHT, animated notifications."""
    def __init__(self):
        super().__init__()
        self.setWindowTitle(BRANDING.program_name)
        self.resize(1180, 760); self.setMinimumSize(900, 600)
        self.setLayoutDirection(Qt.RightToLeft)
        self._cards = {}; self._pages = {}; self._nav_buttons = {}
        self._notification_index = 0; self._notification_x = 0
        self._build_ui()
        self._notification_timer = QTimer(self); self._notification_timer.timeout.connect(self._move_notification); self._notification_timer.start(30)
        self.refresh_dashboard()

    def _build_ui(self):
        root = QWidget(); root.setLayoutDirection(Qt.RightToLeft)
        root_layout = QVBoxLayout(root); root_layout.setContentsMargins(12, 10, 12, 8); root_layout.setSpacing(8)

        header = QFrame(); header.setObjectName("header")
        hl = QHBoxLayout(header); hl.setContentsMargins(18, 11, 18, 11); hl.setSpacing(12)
        identity = QVBoxLayout(); identity.setSpacing(1)
        title = QLabel(BRANDING.program_name); title.setObjectName("appTitle"); identity.addWidget(title)
        subtitle = QLabel("إدارة المبيعات والمشتريات والمخزون والحسابات من مكان واحد"); subtitle.setObjectName("appSubtitle"); subtitle.setWordWrap(True); identity.addWidget(subtitle)
        hl.addLayout(identity, 1)
        refresh = QPushButton("↻  تحديث البيانات"); refresh.setObjectName("primaryButton"); refresh.clicked.connect(self.refresh_dashboard); hl.addWidget(refresh)
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

        ticker = QFrame(); ticker.setObjectName("notificationBar")
        tl = QHBoxLayout(ticker); tl.setContentsMargins(9, 3, 9, 3); tl.setSpacing(8)
        nt = QLabel("التنبيهات"); nt.setObjectName("notificationTitle"); tl.addWidget(nt)
        self._notification_viewport = QFrame(); self._notification_viewport.setObjectName("notificationViewport"); self._notification_viewport.setMinimumHeight(26); self._notification_viewport.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed); tl.addWidget(self._notification_viewport, 1)
        self._notification_label = QLabel(); self._notification_label.setObjectName("notificationText"); self._notification_label.setWordWrap(False); self._notification_label.setAlignment(Qt.AlignVCenter | Qt.AlignRight); self._notification_label.setParent(self._notification_viewport)
        root_layout.addWidget(ticker)
        self._notification_messages = [
            "مرحبًا بك في نظام إدارة البقالات — تابع المبيعات والمشتريات والمخزون والحسابات من مكان واحد",
            "تذكير: راجع الأصناف منخفضة المخزون قبل بدء يوم البيع",
            "تنبيه: احفظ الفواتير واعتمد العمليات المالية بعد مراجعتها",
            f"{BRANDING.program_name} — {BRANDING.designer_credit}",
            f"حقوق التصميم والتنفيذ محفوظة — {BRANDING.contact_text}",
            f"للتواصل وطلب البرنامج أو المساعدة: {BRANDING.phone_display} — واتساب متاح",
        ]
        self._notification_label.setText(self._notification_messages[0])

        shell = QHBoxLayout(); shell.setContentsMargins(0, 0, 0, 0); shell.setSpacing(10); shell.setDirection(QHBoxLayout.RightToLeft)
        nav_scroll = QScrollArea(); nav_scroll.setObjectName("topNavigationScroll"); nav_scroll.setWidgetResizable(True); nav_scroll.setFrameShape(QFrame.NoFrame); nav_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff); nav_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded); nav_scroll.setFixedWidth(210)
        nav = QFrame(); nav.setObjectName("topNavigation"); nav.setLayoutDirection(Qt.RightToLeft)
        nav_layout = QVBoxLayout(nav); nav_layout.setContentsMargins(7, 7, 7, 7); nav_layout.setSpacing(5)
        for label in specs:
            button = QPushButton(label); button.setObjectName("navButton"); button.setProperty("active", label == "الرئيسية"); button.setMinimumHeight(44); button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed); button.clicked.connect(lambda checked=False, name=label: self._show_page(name)); nav_layout.addWidget(button); self._nav_buttons[label] = button
        nav_layout.addStretch(1); nav_scroll.setWidget(nav)

        content_panel = QFrame(); content_panel.setObjectName("contentPanel"); content_panel.setLayoutDirection(Qt.RightToLeft)
        content_layout = QVBoxLayout(content_panel); content_layout.setContentsMargins(0, 0, 0, 0)
        self.stack = QStackedWidget(); self.dashboard = self._dashboard_page(); self.stack.addWidget(self.dashboard); self._pages["الرئيسية"] = self.dashboard
        content_scroll = QScrollArea(); content_scroll.setObjectName("contentScroll"); content_scroll.setWidgetResizable(True); content_scroll.setFrameShape(QFrame.NoFrame); content_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff); content_scroll.setWidget(self.stack); content_layout.addWidget(content_scroll)
        shell.addWidget(content_panel, 1); shell.addWidget(nav_scroll, 0); root_layout.addLayout(shell, 1)

        footer = QFrame(); footer.setObjectName("footerPanel"); fl = QHBoxLayout(footer); fl.setContentsMargins(6, 1, 6, 1)
        credit = QLabel(f"{BRANDING.designer_credit} | {BRANDING.contact_text}"); credit.setWordWrap(False); fl.addWidget(credit, 1)
        call = QPushButton("☎ اتصال"); call.setObjectName("linkButton"); call.clicked.connect(lambda: open_url(BRANDING.phone_uri)); fl.addWidget(call)
        wa = QPushButton("واتساب"); wa.setObjectName("linkButton"); wa.clicked.connect(lambda: open_url(BRANDING.whatsapp_uri)); fl.addWidget(wa)
        root_layout.addWidget(footer); self.setCentralWidget(root); self.setStyleSheet(self._stylesheet()); self._reset_notification_position()

    def _create_page(self, name):
        if name in self._pages: return self._pages[name]
        ptitle, desc, actions = self._specs[name]
        pages = {"الأصناف": ProductsPage, "المخزون": InventoryPage, "المبيعات": SalesPage, "المشتريات": PurchasesPage, "العملاء": CustomersPage, "الموردون": SuppliersPage, "المصروفات": ExpensesPage, "الصناديق والحسابات": CashboxesPage, "المرتجعات": ReturnsPage, "التقارير": ReportsPage, "الإعدادات": SettingsPage}
        page = pages[name]() if name in pages else ModulePage(ptitle, desc, actions)
        if hasattr(page, "back_requested"): page.back_requested.connect(self._show_dashboard)
        self._pages[name] = page; self.stack.addWidget(page); return page

    def _dashboard_page(self):
        page = QWidget(); layout = QVBoxLayout(page); layout.setContentsMargins(8, 8, 8, 16); layout.setSpacing(12)
        welcome = QFrame(); welcome.setObjectName("welcomePanel"); wl = QVBoxLayout(welcome); wl.setContentsMargins(18, 12, 18, 12); wl.setSpacing(2)
        w1 = QLabel("لوحة التحكم"); w1.setObjectName("pageTitle"); wl.addWidget(w1); w2 = QLabel("ملخص سريع لحالة البقالة والعمليات اليومية"); w2.setObjectName("pageDescription"); wl.addWidget(w2); layout.addWidget(welcome)
        cards = QGridLayout(); cards.setHorizontalSpacing(10); cards.setVerticalSpacing(10)
        for i, (key, label) in enumerate([("sales", "مبيعات اليوم"), ("purchases", "مشتريات اليوم"), ("expenses", "المصروفات اليوم"), ("profit", "صافي الربح"), ("receivables", "ذمم العملاء"), ("payables", "ذمم الموردين"), ("cash", "رصيد الصندوق"), ("low", "أصناف منخفضة")]):
            card = SummaryCard(label, "0.00"); self._cards[key] = card; cards.addWidget(card, i // 4, i % 4)
        layout.addLayout(cards)
        quick = QFrame(); quick.setObjectName("panel"); ql = QVBoxLayout(quick); ql.setContentsMargins(16, 14, 16, 14); ql.setSpacing(10)
        h = QLabel("العمليات الرئيسية"); h.setObjectName("sectionTitle"); ql.addWidget(h)
        row = QGridLayout(); row.setHorizontalSpacing(8); row.setVerticalSpacing(8)
        for i, (label, target) in enumerate([("فاتورة بيع جديدة", "المبيعات"), ("فاتورة شراء جديدة", "المشتريات"), ("إضافة صنف", "الأصناف"), ("قبض من عميل", "العملاء"), ("سداد مورد", "الموردون"), ("تسجيل مصروف", "المصروفات"), ("الصناديق والحسابات", "الصناديق والحسابات"), ("المرتجعات", "المرتجعات")]):
            b = QPushButton(label); b.setObjectName("actionButton"); b.clicked.connect(lambda checked=False, name=target: self._show_page(name)); row.addWidget(b, i // 4, i % 4)
        ql.addLayout(row); layout.addWidget(quick); layout.addStretch(); return page

    def _show_dashboard(self): self._show_page("الرئيسية")
    def _show_page(self, name):
        page = self._create_page(name)
        if hasattr(page, "refresh"): page.refresh()
        self.stack.setCurrentWidget(page)
        for label, button in self._nav_buttons.items():
            button.setProperty("active", label == name); button.style().unpolish(button); button.style().polish(button)

    def _reset_notification_position(self):
        if hasattr(self, "_notification_viewport"):
            self._notification_label.adjustSize(); self._notification_x = self._notification_viewport.width(); self._notification_label.move(int(self._notification_x), 0)
    def _move_notification(self):
        viewport_width = self._notification_viewport.width()
        if viewport_width <= 0: return
        self._notification_label.adjustSize(); label_width = self._notification_label.width()
        self._notification_x -= 2
        if self._notification_x + label_width < 0:
            self._notification_index = (self._notification_index + 1) % len(self._notification_messages); self._notification_label.setText(self._notification_messages[self._notification_index]); self._notification_label.adjustSize(); self._notification_x = viewport_width
        self._notification_label.move(int(self._notification_x), 0)
    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "_notification_viewport"):
            self._notification_label.adjustSize(); self._notification_label.move(int(min(self._notification_x, self._notification_viewport.width())), 0)

    def refresh_dashboard(self):
        session = get_session()
        try:
            today = date.today().isoformat(); s = ReportService(session).dashboard_summary(date_from=today, date_to=today); reports = ReportService(session)
            values = {"sales": s.sales_total, "purchases": s.purchases_total, "expenses": s.expenses_total, "profit": s.gross_profit - s.expenses_total, "receivables": s.customer_receivables, "payables": s.supplier_payables, "cash": s.cash_balance, "low": reports.low_stock_count()}
            for key, value in values.items(): self._cards[key].value_label.setText(str(int(value)) if key == "low" else f"{value:,.2f}")
        finally: session.close()

    def closeEvent(self, event):
        if hasattr(self, "_notification_timer"): self._notification_timer.stop()
        super().closeEvent(event)

    @staticmethod
    def _stylesheet():
        return """
        * { font-family: 'Noto Sans Arabic', 'Segoe UI', Tahoma, Arial; font-size: 13px; }
        QMainWindow, QWidget { background: #f3f5f7; color: #263746; }
        #header { background: #ffffff; border: 1px solid #d9e0e6; border-radius: 8px; }
        #appTitle { color: #263746; font-size: 22px; font-weight: 800; }
        #appSubtitle { color: #778692; font-size: 12px; }
        #topNavigationScroll { background: transparent; border: none; }
        #topNavigation { background: #ffffff; border: 1px solid #d7dee5; border-radius: 8px; }
        #navButton { min-height: 44px; padding: 0 13px; border-radius: 6px; background: #ffffff; color: #334654; border: 1px solid transparent; text-align: right; font-weight: 600; }
        #navButton:hover { background: #f0f4f7; border-color: #d5dee6; }
        #navButton[active="true"] { background: #e7eef4; color: #1e4f72; border-right: 4px solid #2d6a9f; font-weight: 800; }
        #notificationBar { background: #ffffff; border: 1px solid #d7dee5; border-radius: 6px; min-height: 32px; }
        #notificationViewport { background: transparent; border: none; min-height: 26px; max-height: 26px; }
        #notificationTitle { color: #1e4f72; font-weight: 800; min-width: 62px; }
        #notificationText { color: #566875; font-size: 12px; min-width: 1px; }
        #contentPanel, #contentScroll, QScrollArea > QWidget > QWidget { background: transparent; border: none; }
        #welcomePanel, #summaryCard, #panel { background: #ffffff; border: 1px solid #d8e0e6; border-radius: 8px; }
        #welcomePanel { border-right: 4px solid #2d6a9f; }
        #summaryCard { min-height: 82px; }
        #summaryLabel { color: #74838d; font-size: 12px; font-weight: 600; }
        #cardValue { font-size: 20px; font-weight: 800; color: #263746; }
        #pageTitle { font-size: 19px; font-weight: 800; color: #263746; }
        #sectionTitle { font-size: 16px; font-weight: 800; color: #334654; }
        #pageDescription { color: #778692; font-size: 12px; }
        QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit, QTextEdit { background: #ffffff; border: 1px solid #cfd8df; border-radius: 5px; padding: 6px 9px; min-height: 32px; selection-background-color: #2d6a9f; }
        QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus, QTextEdit:focus { border: 1px solid #2d6a9f; }
        QTableWidget, QTableView { background: #ffffff; border: 1px solid #d4dde4; border-radius: 6px; gridline-color: #e5eaee; alternate-background-color: #f8fafb; }
        QHeaderView::section { background: #edf2f5; color: #344854; padding: 7px 8px; border: none; border-bottom: 1px solid #d4dde4; font-weight: 800; }
        QPushButton { min-height: 36px; padding: 0 12px; border-radius: 5px; border: 1px solid #cbd5dc; background: #ffffff; color: #334654; font-weight: 600; }
        QPushButton:hover { background: #f1f5f8; border-color: #9fb0bc; }
        #primaryButton { background: #2d6a9f; color: #ffffff; border: none; min-width: 120px; }
        #primaryButton:hover { background: #255b89; }
        #secondaryButton { background: #edf2f5; }
        #actionButton { min-height: 43px; background: #f8fafb; border-color: #d3dce2; }
        #actionButton:hover { background: #eaf1f5; border-color: #9fb5c4; }
        #linkButton { border: none; background: transparent; color: #2d6a9f; min-height: 24px; }
        QGroupBox { background: #ffffff; border: 1px solid #d8e0e6; border-radius: 7px; margin-top: 12px; padding: 10px; font-weight: 800; }
        QGroupBox::title { subcontrol-origin: margin; right: 12px; padding: 0 6px; background: #ffffff; }
        QCheckBox, QRadioButton { spacing: 7px; }
        QToolTip { background: #263746; color: #ffffff; border: none; padding: 5px; }
        QScrollBar:vertical { width: 8px; background: transparent; margin: 0; }
        QScrollBar::handle:vertical { background: #c4ced5; border-radius: 4px; min-height: 25px; }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        #footerPanel { min-height: 24px; max-height: 28px; }
        """
