from datetime import date
from decimal import Decimal
from webbrowser import open as open_url

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from backend.app.core.database import get_session, initialize_database
from backend.app.modules.reports.service import ReportService
from frontend.app.branding import BRANDING


class SummaryCard(QFrame):
    def __init__(self, title: str, value: str, parent=None):
        super().__init__(parent)
        self.setObjectName("summaryCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        title_label = QLabel(title)
        title_label.setObjectName("cardTitle")
        value_label = QLabel(value)
        value_label.setObjectName("cardValue")
        layout.addWidget(title_label)
        layout.addWidget(value_label)
        self.value_label = value_label


class ModulePage(QFrame):
    back_requested = Signal()

    def __init__(self, title: str, description: str, actions: list[str], parent=None):
        super().__init__(parent)
        self.setObjectName("panel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        heading = QLabel(title)
        heading.setObjectName("pageTitle")
        layout.addWidget(heading)
        text = QLabel(description)
        text.setObjectName("pageDescription")
        text.setWordWrap(True)
        layout.addWidget(text)
        actions_layout = QGridLayout()
        actions_layout.setSpacing(10)
        for index, label in enumerate(actions):
            button = QPushButton(label)
            button.setObjectName("actionButton")
            actions_layout.addWidget(button, index // 3, index % 3)
        layout.addLayout(actions_layout)
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
        initialize_database()
        self._cards: dict[str, SummaryCard] = {}
        self._build_ui()
        self.refresh_dashboard()

    def _build_ui(self):
        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(22, 18, 22, 12)
        root_layout.setSpacing(12)

        header = QFrame()
        header.setObjectName("header")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(22, 16, 22, 16)
        identity = QVBoxLayout()
        title = QLabel(BRANDING.program_name)
        title.setObjectName("appTitle")
        subtitle = QLabel("إدارة المبيعات والمشتريات والمخزون والحسابات من مكان واحد")
        subtitle.setObjectName("appSubtitle")
        identity.addWidget(title)
        identity.addWidget(subtitle)
        header_layout.addLayout(identity)
        header_layout.addStretch()
        refresh = QPushButton("تحديث البيانات")
        refresh.setObjectName("primaryButton")
        refresh.clicked.connect(self.refresh_dashboard)
        header_layout.addWidget(refresh)
        root_layout.addWidget(header)

        self.stack = QStackedWidget()
        self.dashboard = self._dashboard_page()
        self.stack.addWidget(self.dashboard)
        self._pages: dict[str, QWidget] = {}
        module_specs = {
            "المبيعات": ("المبيعات", "إنشاء وإدارة فواتير البيع والتحصيل والمرتجعات.", ["فاتورة بيع جديدة", "مرتجع مبيعات", "سجل المبيعات"]),
            "المشتريات": ("المشتريات", "إدارة فواتير الشراء والموردين والمدفوعات.", ["فاتورة شراء جديدة", "مرتجع مشتريات", "سجل المشتريات"]),
            "المخزون": ("المخزون", "متابعة الأصناف والكميات والحركات وتكلفة المخزون.", ["الأصناف", "حركة المخزون", "جرد المخزون"]),
            "العملاء": ("العملاء", "إدارة بيانات العملاء والأرصدة والتحصيلات.", ["عميل جديد", "قبض من عميل", "كشف حساب"]),
            "الموردون": ("الموردون", "إدارة بيانات الموردين والأرصدة والمدفوعات.", ["مورد جديد", "سداد مورد", "كشف حساب"]),
            "المصروفات": ("المصروفات", "تسجيل ومراجعة المصروفات وربطها بوسيلة الدفع.", ["مصروف جديد", "تصنيفات المصروفات", "سجل المصروفات"]),
            "التقارير": ("التقارير", "تقارير تشغيلية ومالية قابلة للتوسع والطباعة والتصدير.", ["ملخص يومي", "الأرباح والخسائر", "أرصدة العملاء والموردين"]),
        }
        for name, (title, description, actions) in module_specs.items():
            page = ModulePage(title, description, actions)
            page.back_requested.connect(lambda name=name: self._show_dashboard())
            self._pages[name] = page
            self.stack.addWidget(page)
        root_layout.addWidget(self.stack, 1)

        nav = QHBoxLayout()
        nav.setSpacing(7)
        for label in ["الرئيسية", *module_specs.keys()]:
            button = QPushButton(label)
            button.setObjectName("navButton")
            button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            if label == "الرئيسية":
                button.clicked.connect(self._show_dashboard)
            else:
                button.clicked.connect(lambda checked=False, name=label: self._show_page(name))
            nav.addWidget(button)
        root_layout.addLayout(nav)

        footer = QFrame()
        footer.setObjectName("footerPanel")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(10, 5, 10, 5)
        credit = QLabel(f"{BRANDING.designer_credit} | {BRANDING.contact_text}")
        credit.setObjectName("footer")
        footer_layout.addWidget(credit, 1)
        call = QPushButton("☎ اتصال")
        call.setObjectName("linkButton")
        call.clicked.connect(lambda: open_url(BRANDING.phone_uri))
        whatsapp = QPushButton("واتساب")
        whatsapp.setObjectName("linkButton")
        whatsapp.clicked.connect(lambda: open_url(BRANDING.whatsapp_uri))
        footer_layout.addWidget(call)
        footer_layout.addWidget(whatsapp)
        root_layout.addWidget(footer)

        self.setCentralWidget(root)
        self.setStyleSheet(self._stylesheet())

    def _dashboard_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        cards = QGridLayout()
        cards.setSpacing(12)
        for key, label in [
            ("sales", "مبيعات اليوم"),
            ("purchases", "مشتريات اليوم"),
            ("expenses", "المصروفات اليوم"),
            ("profit", "صافي الربح"),
            ("receivables", "ذمم العملاء"),
            ("payables", "ذمم الموردين"),
            ("cash", "رصيد الصندوق"),
            ("low", "أصناف منخفضة"),
        ]:
            card = SummaryCard(label, "0.00")
            self._cards[key] = card
            cards.addWidget(card, len(self._cards) // 5, (len(self._cards) - 1) % 4)
        layout.addLayout(cards)
        quick = QFrame()
        quick.setObjectName("panel")
        ql = QVBoxLayout(quick)
        heading = QLabel("العمليات الرئيسية")
        heading.setObjectName("pageTitle")
        ql.addWidget(heading)
        row = QHBoxLayout()
        for label, target in [("فاتورة بيع جديدة", "المبيعات"), ("فاتورة شراء جديدة", "المشتريات"), ("إضافة صنف", "المخزون"), ("قبض من عميل", "العملاء"), ("سداد مورد", "الموردون"), ("تسجيل مصروف", "المصروفات")]:
            button = QPushButton(label)
            button.setObjectName("actionButton")
            button.clicked.connect(lambda checked=False, name=target: self._show_page(name))
            row.addWidget(button)
        ql.addLayout(row)
        layout.addWidget(quick, 1)
        return page

    def _show_dashboard(self):
        self.stack.setCurrentWidget(self.dashboard)
        self.refresh_dashboard()

    def _show_page(self, name: str):
        self.stack.setCurrentWidget(self._pages[name])

    def refresh_dashboard(self):
        session = get_session()
        try:
            today = date.today().isoformat()
            summary = ReportService(session).dashboard_summary(date_from=today, date_to=today)
            values = {
                "sales": summary.sales_total,
                "purchases": summary.purchases_total,
                "expenses": summary.expenses_total,
                "profit": summary.gross_profit - summary.expenses_total,
                "receivables": summary.customer_receivables,
                "payables": summary.supplier_payables,
                "cash": summary.cash_balance,
                "low": Decimal("0"),
            }
            for key, value in values.items():
                if key == "low":
                    self._cards[key].value_label.setText(str(int(value)))
                else:
                    self._cards[key].value_label.setText(f"{Decimal(value):,.2f}")
        finally:
            session.close()

    @staticmethod
    def _stylesheet() -> str:
        return """
        QWidget { font-family: 'Segoe UI'; font-size: 14px; }
        QMainWindow, QWidget { background: #f4f6f8; color: #1f2933; }
        #header, #summaryCard, #panel, #footerPanel { background: white; border: 1px solid #e1e6eb; border-radius: 12px; }
        #appTitle { font-size: 25px; font-weight: 700; }
        #appSubtitle, #pageDescription { color: #667085; }
        #pageTitle { font-size: 19px; font-weight: 700; }
        #primaryButton { background: #1769aa; color: white; border: 0; border-radius: 8px; padding: 10px 18px; font-weight: 600; }
        #navButton, #secondaryButton { background: white; border: 1px solid #d9e0e7; border-radius: 8px; padding: 9px 8px; }
        #navButton:hover, #actionButton:hover { background: #eef5fb; }
        #cardTitle { color: #667085; }
        #cardValue { font-size: 22px; font-weight: 700; margin-top: 6px; }
        #actionButton { background: #f8fafc; border: 1px solid #d9e0e7; border-radius: 8px; padding: 12px; }
        #linkButton { background: transparent; border: 0; font-weight: 600; padding: 5px 8px; }
        #footer { color: #667085; font-size: 12px; }
        """
