from datetime import date
from webbrowser import open as open_url

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QMainWindow, QPushButton,
    QScrollArea, QSizePolicy, QStackedWidget, QVBoxLayout, QWidget
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
from frontend.app.ui.suppliers_page import SuppliersPage


class SummaryCard(QFrame):
    def __init__(self, title, value, tone="blue", parent=None):
        super().__init__(parent)
        self.setObjectName("summaryCard")
        self.setProperty("tone", tone)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 13, 16, 13)
        layout.setSpacing(5)
        label = QLabel(title)
        label.setObjectName("summaryLabel")
        layout.addWidget(label)
        self.value_label = QLabel(value)
        self.value_label.setObjectName("cardValue")
        layout.addWidget(self.value_label)


class ModulePage(QFrame):
    back_requested = Signal()

    def __init__(self, title, description, actions, parent=None):
        super().__init__(parent)
        self.setObjectName("panel")
        self.setLayoutDirection(Qt.RightToLeft)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
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


class SettingsPage(QFrame):
    back_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("panel")
        self.setLayoutDirection(Qt.RightToLeft)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(12)
        title = QLabel("الإعدادات")
        title.setObjectName("pageTitle")
        layout.addWidget(title)
        desc = QLabel("مركز إعداد النظام: بيانات البقالة، المستخدمون والصلاحيات، تسجيل النسخة، الطابعة والفواتير، النسخ الاحتياطي والمزامنة.")
        desc.setWordWrap(True)
        desc.setObjectName("pageDescription")
        layout.addWidget(desc)
        for text in [
            "بيانات البقالة والهوية", "المستخدمون والصلاحيات", "تسجيل النسخة والترخيص",
            "الطابعة والفواتير", "النسخ الاحتياطي والاستعادة", "المزامنة والاتصال"
        ]:
            b = QPushButton(text)
            b.setObjectName("actionButton")
            layout.addWidget(b)
        layout.addStretch()
        back = QPushButton("العودة إلى الرئيسية")
        back.setObjectName("secondaryButton")
        back.clicked.connect(self.back_requested.emit)
        layout.addWidget(back, alignment=Qt.AlignLeft)


class CameraPanel(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("cameraPanel")
        self.setLayoutDirection(Qt.RightToLeft)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)
        title_row = QHBoxLayout()
        title = QLabel("قائمة الكاميرات")
        title.setObjectName("sectionTitle")
        title_row.addWidget(title)
        title_row.addStretch()
        icon = QLabel("▣")
        icon.setObjectName("sectionIcon")
        title_row.addWidget(icon)
        layout.addLayout(title_row)
        for i, name in enumerate(["المدخل الرئيسي", "المخزن", "المواد الغذائية", "المر الخلفي", "صالة البيع"], 1):
            row = QFrame()
            row.setObjectName("cameraRow")
            rl = QHBoxLayout(row)
            rl.setContentsMargins(9, 7, 9, 7)
            dot = QLabel("●")
            dot.setObjectName("onlineDot")
            rl.addWidget(dot)
            text = QLabel(f"الكاميرا {i}\n{name}")
            text.setObjectName("cameraText")
            rl.addWidget(text, 1)
            view = QPushButton("▣")
            view.setObjectName("miniButton")
            rl.addWidget(view)
            layout.addWidget(row)
        layout.addStretch()
        quick = QLabel("العمليات السريعة")
        quick.setObjectName("sectionTitle")
        layout.addWidget(quick)
        quick_grid = QGridLayout()
        for i, text in enumerate(["المبيعات", "المشتريات", "إضافة صنف", "تقرير سريع"]):
            b = QPushButton(text)
            b.setObjectName("quickButton")
            quick_grid.addWidget(b, i // 2, i % 2)
        layout.addLayout(quick_grid)


class RecentSalesPanel(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("recentPanel")
        self.setLayoutDirection(Qt.RightToLeft)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)
        title = QLabel("المبيعات الأخيرة")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)
        for name, barcode, price in [
            ("شاي أسود 250 جم", "6281001234567", "1,500"),
            ("قهوة سريعة الذوبان", "6281009876543", "4,500"),
            ("سكر 1 كجم", "6281012345678", "950"),
            ("ماء معدني 600 مل", "6281023456789", "300"),
            ("بسكويت شاي", "6281034567890", "1,200"),
            ("زيت نباتي 1 لتر", "6281045678901", "2,500"),
        ]:
            row = QFrame()
            row.setObjectName("saleRow")
            rl = QHBoxLayout(row)
            rl.setContentsMargins(7, 5, 7, 5)
            item = QLabel(name)
            item.setObjectName("saleName")
            rl.addWidget(item, 1)
            bc = QLabel(barcode)
            bc.setObjectName("saleBarcode")
            rl.addWidget(bc)
            amount = QLabel(price)
            amount.setObjectName("salePrice")
            rl.addWidget(amount)
            layout.addWidget(row)
        layout.addStretch()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(BRANDING.program_name)
        self.resize(1400, 900)
        self.setMinimumSize(1080, 720)
        self.setLayoutDirection(Qt.RightToLeft)
        self._cards = {}
        self._pages = {}
        self._nav_buttons = {}
        self._notification_offset = 0
        self._build_ui()
        self._notification_timer = QTimer(self)
        self._notification_timer.timeout.connect(self._move_notification)
        self._notification_timer.start(6000)

    def _build_ui(self):
        root = QWidget()
        root.setObjectName("appRoot")
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(10, 8, 10, 8)
        root_layout.setSpacing(8)

        header = QFrame()
        header.setObjectName("topHeader")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(18, 10, 18, 10)
        brand = QLabel("▣")
        brand.setObjectName("brandIcon")
        hl.addWidget(brand)
        identity = QVBoxLayout()
        identity.setSpacing(1)
        title = QLabel("نظام البقالة المحاسبي")
        title.setObjectName("appTitle")
        identity.addWidget(title)
        subtitle = QLabel("إدارة شاملة .. لمتجرك بكل سهولة")
        subtitle.setObjectName("appSubtitle")
        identity.addWidget(subtitle)
        hl.addLayout(identity, 1)
        date_label = QLabel(date.today().strftime("%Y/%m/%d"))
        date_label.setObjectName("headerDate")
        hl.addWidget(date_label)
        user = QLabel("◉  مدير النظام")
        user.setObjectName("headerUser")
        hl.addWidget(user)
        root_layout.addWidget(header)

        ticker = QFrame()
        ticker.setObjectName("notificationBar")
        tl = QHBoxLayout(ticker)
        tl.setContentsMargins(10, 4, 10, 4)
        tl.setSpacing(8)
        bell = QLabel("♧")
        bell.setObjectName("notificationBell")
        tl.addWidget(bell)
        self._notification_label = QLabel()
        self._notification_label.setObjectName("notificationText")
        self._notification_label.setAlignment(Qt.AlignCenter)
        tl.addWidget(self._notification_label, 1)
        root_layout.addWidget(ticker)
        self._notification_messages = [
            "تم تسجيل عملية بيع جديدة بقيمة 12,450 ريال",
            "تنبيه: يوجد مخزون منخفض يحتاج إلى مراجعة",
            "تم استلام دفعة من المورد بقيمة 8,320 ريال",
            "نظام البقالة المحاسبي — إدارة متكاملة للمبيعات والمشتريات والمخزون والحسابات",
        ]
        self._notification_label.setText(self._notification_messages[0])

        body = QWidget()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(9)

        sidebar = QFrame()
        sidebar.setObjectName("sideNavigation")
        sidebar.setMinimumWidth(225)
        sidebar.setMaximumWidth(255)
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(10, 12, 10, 12)
        side_layout.setSpacing(4)
        side_brand = QLabel("نظام البقالة المحاسبي")
        side_brand.setObjectName("sideBrand")
        side_layout.addWidget(side_brand)
        side_sub = QLabel("القائمة الرئيسية")
        side_sub.setObjectName("sideSubtitle")
        side_layout.addWidget(side_sub)

        specs = {
            "الرئيسية": ("الرئيسية", "لوحة المتابعة والعمليات الرئيسية.", []),
            "المبيعات": ("المبيعات", "إنشاء وإدارة فواتير البيع والتحصيل والمرتجعات.", ["فاتورة بيع جديدة", "مرتجع مبيعات", "سجل المبيعات"]),
            "المشتريات": ("المشتريات", "إدارة فواتير الشراء والموردين والمدفوعات.", ["فاتورة شراء جديدة", "مرتجع مشتريات", "سجل المشتريات"]),
            "الأصناف": ("الأصناف", "إضافة وإدارة الأصناف والكميات والأسعار والباركود.", ["إضافة صنف", "بحث في الأصناف", "إدارة الأسعار"]),
            "المخزون": ("المخزون", "متابعة الكميات والحركات وتكلفة المخزون والجرد.", ["حركة المخزون", "جرد المخزون", "تحويل بين المخازن"]),
            "العملاء": ("العملاء", "إدارة بيانات العملاء والأرصدة والتحصيلات.", ["عميل جديد", "قبض من عميل", "كشف حساب"]),
            "الموردون": ("الموردون", "إدارة بيانات الموردين والأرصدة والمدفوعات.", ["مورد جديد", "سداد مورد", "كشف حساب"]),
            "الصناديق والحسابات": ("الصناديق والحسابات", "متابعة النقد والمحفظة والحساب البنكي والتحويلات.", ["أرصدة الحسابات", "تحويل بين الحسابات", "سجل الحركات"]),
            "التقارير": ("التقارير", "تقارير تشغيلية ومالية قابلة للطباعة والتصدير.", ["ملخص يومي", "الأرباح والخسائر", "أرصدة العملاء والموردين"]),
            "الإعدادات": ("الإعدادات", "إعدادات النظام والمستخدمين والصلاحيات والترخيص والنسخ الاحتياطي.", []),
        }
        self._specs = specs
        for label in specs:
            button = QPushButton(f"{label}")
            button.setObjectName("navButton")
            button.setProperty("active", label == "الرئيسية")
            button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            button.clicked.connect(lambda checked=False, name=label: self._show_page(name))
            side_layout.addWidget(button)
            self._nav_buttons[label] = button
        camera_button = QPushButton("مراقبة الكاميرات  ◉")
        camera_button.setObjectName("cameraNavButton")
        camera_button.clicked.connect(lambda: self._show_page("مراقبة الكاميرات"))
        side_layout.addWidget(camera_button)
        side_layout.addStretch()
        refresh_side = QPushButton("↻  تحديث البيانات")
        refresh_side.setObjectName("primaryButton")
        refresh_side.clicked.connect(self.refresh_dashboard)
        side_layout.addWidget(refresh_side)
        body_layout.addWidget(sidebar)

        center = QWidget()
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(9)
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
        center_layout.addWidget(scroll, 1)
        body_layout.addWidget(center, 1)

        left_column = QVBoxLayout()
        left_column.setContentsMargins(0, 0, 0, 0)
        left_column.setSpacing(9)
        left_column.addWidget(CameraPanel())
        left_column.addWidget(RecentSalesPanel(), 1)
        body_layout.addLayout(left_column)
        root_layout.addWidget(body, 1)

        footer = QFrame()
        footer.setObjectName("footerPanel")
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(12, 4, 12, 4)
        credit = QLabel(f"{BRANDING.designer_credit} | {BRANDING.contact_text}")
        credit.setObjectName("footerText")
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

    def _create_page(self, name):
        if name in self._pages:
            return self._pages[name]
        if name == "مراقبة الكاميرات":
            page = ModulePage("مراقبة الكاميرات", "الوصول إلى كاميرات البقالة ومتابعة حالتها من داخل النظام.", ["جميع الكاميرات", "الكاميرات المتصلة", "إعدادات الكاميرات"])
        else:
            ptitle, desc, actions = self._specs[name]
            if name == "المخزون": page = InventoryPage()
            elif name == "الأصناف": page = ProductsPage()
            elif name == "المبيعات": page = SalesPage()
            elif name == "المشتريات": page = PurchasesPage()
            elif name == "العملاء": page = CustomersPage()
            elif name == "الموردون": page = SuppliersPage()
            elif name == "المصروفات": page = ExpensesPage()
            elif name == "الصناديق والحسابات": page = CashboxesPage()
            elif name == "التقارير": page = ReportsPage()
            elif name == "الإعدادات": page = SettingsPage()
            else: page = ModulePage(ptitle, desc, actions)
        if hasattr(page, "back_requested"):
            page.back_requested.connect(self._show_dashboard)
        self._pages[name] = page
        self.stack.addWidget(page)
        return page

    def _dashboard_page(self):
        page = QWidget()
        page.setLayoutDirection(Qt.RightToLeft)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(5, 5, 5, 12)
        layout.setSpacing(10)
        welcome = QLabel("لوحة التحكم  |  الفرع الرئيسي")
        welcome.setObjectName("dashboardTitle")
        layout.addWidget(welcome)
        cards = QGridLayout()
        cards.setHorizontalSpacing(9)
        cards.setVerticalSpacing(9)
        data = [
            ("sales", "مبيعات اليوم", "0.00", "green"),
            ("purchases", "مشتريات اليوم", "0.00", "blue"),
            ("low", "المخزون الحالي", "0", "orange"),
            ("profit", "الأرباح اليوم", "0.00", "purple"),
            ("expenses", "المصروفات اليوم", "0.00", "red"),
            ("receivables", "ذمم العملاء", "0.00", "blue"),
            ("payables", "ذمم الموردين", "0.00", "orange"),
            ("cash", "رصيد الصندوق", "0.00", "green"),
        ]
        for i, (key, label, value, tone) in enumerate(data):
            card = SummaryCard(label, value, tone)
            self._cards[key] = card
            cards.addWidget(card, i // 4, i % 4)
        layout.addLayout(cards)
        quick = QFrame()
        quick.setObjectName("panel")
        ql = QVBoxLayout(quick)
        ql.setContentsMargins(14, 12, 14, 12)
        title = QLabel("العمليات السريعة")
        title.setObjectName("sectionTitle")
        ql.addWidget(title)
        row = QGridLayout()
        row.setHorizontalSpacing(9)
        row.setVerticalSpacing(9)
        for i, (label, target) in enumerate([
            ("＋ فاتورة بيع جديدة", "المبيعات"), ("＋ فاتورة شراء جديدة", "المشتريات"),
            ("＋ إضافة صنف", "الأصناف"), ("▣ العملاء", "العملاء"),
            ("▣ الموردون", "الموردون"), ("▣ المصروفات", "المصروفات"),
            ("▣ الصناديق والحسابات", "الصناديق والحسابات"), ("▣ التقارير", "التقارير")
        ]):
            b = QPushButton(label)
            b.setObjectName("actionButton")
            b.clicked.connect(lambda checked=False, name=target: self._show_page(name))
            row.addWidget(b, i // 4, i % 4)
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

    def _move_notification(self):
        if not self._notification_messages:
            return
        self._notification_label.setText(self._notification_messages[self._notification_offset % len(self._notification_messages)])
        self._notification_offset += 1

    def refresh_dashboard(self):
        session = get_session()
        try:
            today = date.today().isoformat()
            s = ReportService(session).dashboard_summary(date_from=today, date_to=today)
            reports = ReportService(session)
            values = {
                "sales": s.sales_total, "purchases": s.purchases_total,
                "expenses": s.expenses_total, "profit": s.gross_profit - s.expenses_total,
                "receivables": s.customer_receivables, "payables": s.supplier_payables,
                "cash": s.cash_balance, "low": reports.low_stock_count()
            }
            for key, value in values.items():
                self._cards[key].value_label.setText(str(int(value)) if key == "low" else f"{value:,.2f}")
        finally:
            session.close()

    def closeEvent(self, event):
        if hasattr(self, "_notification_timer"):
            self._notification_timer.stop()
        super().closeEvent(event)

    @staticmethod
    def _stylesheet():
        return """
        QWidget { font-family: 'Noto Sans Arabic', 'Segoe UI', Tahoma, Arial; font-size: 13px; color: #123b70; }
        QMainWindow, #appRoot { background: #eef5fb; }
        #topHeader { background: #06447f; border-radius: 9px; border: 1px solid #0a5da5; }
        #brandIcon { background: #087cff; color: white; border-radius: 20px; min-width: 42px; max-width: 42px; min-height: 42px; max-height: 42px; qproperty-alignment: AlignCenter; font-size: 24px; }
        #appTitle { color: white; font-size: 24px; font-weight: 800; }
        #appSubtitle { color: #dcecff; font-size: 12px; }
        #headerDate, #headerUser { color: white; font-weight: 700; padding: 8px 12px; }
        #notificationBar { background: #07559a; border: 1px solid #178cff; border-radius: 8px; min-height: 32px; }
        #notificationBell { color: white; font-size: 18px; }
        #notificationText { color: white; font-weight: 600; }
        #sideNavigation { background: #063b70; border-radius: 9px; border: 1px solid #0a65ad; }
        #sideBrand { color: white; font-size: 17px; font-weight: 800; padding: 7px; }
        #sideSubtitle { color: #bcdcff; padding: 2px 7px 8px; }
        #navButton { min-height: 40px; padding: 0 12px; text-align: right; border-radius: 7px; background: transparent; color: white; border: 1px solid transparent; font-weight: 600; }
        #navButton:hover { background: #0c5b9e; }
        #navButton[active="true"] { background: #087cf2; border-color: #2ba0ff; font-weight: 800; }
        #cameraNavButton { min-height: 42px; background: #087cf2; color: white; border: 1px solid #49b0ff; border-radius: 7px; font-weight: 800; }
        #primaryButton { min-height: 40px; background: #087cf2; color: white; border: none; border-radius: 7px; font-weight: 700; }
        #contentScroll { background: transparent; }
        #dashboardTitle { font-size: 20px; font-weight: 800; color: #073e76; padding: 4px 2px; }
        #summaryCard { min-height: 84px; background: white; border: 1px solid #c9dff1; border-radius: 9px; }
        #summaryCard[tone="green"] { border-right: 5px solid #12b878; }
        #summaryCard[tone="blue"] { border-right: 5px solid #087cf2; }
        #summaryCard[tone="orange"] { border-right: 5px solid #f39a08; }
        #summaryCard[tone="purple"] { border-right: 5px solid #7b4be0; }
        #summaryCard[tone="red"] { border-right: 5px solid #ef4d58; }
        #summaryLabel { color: #54718f; font-weight: 600; }
        #cardValue { color: #083f77; font-size: 21px; font-weight: 800; }
        #panel, #cameraPanel, #recentPanel { background: white; border: 1px solid #c9dff1; border-radius: 9px; }
        #sectionTitle { color: #073e76; font-size: 16px; font-weight: 800; }
        #sectionIcon { color: #087cf2; font-size: 20px; }
        #actionButton { min-height: 46px; background: #f8fbfe; color: #07539a; border: 1px solid #b9d8ef; border-radius: 7px; font-weight: 700; }
        #actionButton:hover, #quickButton:hover { background: #e8f4ff; border-color: #087cf2; }
        #quickButton { min-height: 38px; background: #f5faff; color: #0870cf; border: 1px solid #b9d8ef; border-radius: 6px; font-size: 11px; }
        #cameraRow, #saleRow { background: #fbfdff; border: 1px solid #d8e7f3; border-radius: 6px; }
        #onlineDot { color: #11b978; font-size: 10px; }
        #cameraText { color: #123f70; font-weight: 700; line-height: 1.4; }
        #miniButton { min-width: 30px; max-width: 30px; min-height: 30px; max-height: 30px; padding: 0; background: #e8f4ff; color: #087cf2; border: 1px solid #b9d8ef; border-radius: 5px; }
        #saleName { color: #174878; font-weight: 600; }
        #saleBarcode { color: #69839c; font-size: 10px; }
        #salePrice { color: #087cf2; font-weight: 800; min-width: 52px; }
        #pageTitle { font-size: 21px; font-weight: 800; color: #073e76; }
        #pageDescription { color: #5a748d; font-size: 13px; }
        QPushButton { min-height: 38px; padding: 0 12px; border-radius: 7px; border: 1px solid #bfd6e8; background: white; }
        QPushButton:hover { border-color: #087cf2; }
        #secondaryButton { background: #eef5fb; color: #315b80; }
        #linkButton { border: none; background: transparent; color: #0869bc; min-height: 28px; }
        #footerPanel { background: #063b70; border-radius: 8px; }
        #footerText { color: white; font-size: 11px; }
        QLineEdit, QComboBox, QDoubleSpinBox, QSpinBox { min-height: 38px; padding: 0 8px; border: 1px solid #bfd6e8; border-radius: 6px; background: white; }
        QTableWidget { gridline-color: #d6e5f1; alternate-background-color: #f6faff; background: white; }
        QHeaderView::section { background: #07559a; color: white; padding: 8px; font-weight: 800; border: none; }
        QScrollBar:vertical { width: 10px; background: #e5eff7; }
        QScrollBar::handle:vertical { background: #9fc5e3; border-radius: 5px; min-height: 30px; }
        """
