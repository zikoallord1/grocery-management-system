from datetime import date
from webbrowser import open as open_url

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QMainWindow, QPushButton, QSizePolicy, QStackedWidget, QVBoxLayout, QWidget

from backend.app.core.database import get_session
from backend.app.modules.reports.service import ReportService
from frontend.app.branding import BRANDING
from frontend.app.ui.inventory_page import InventoryPage
from frontend.app.ui.purchases_page import PurchasesPage
from frontend.app.ui.sales_page import SalesPage


class SummaryCard(QFrame):
    def __init__(self, title, value, parent=None):
        super().__init__(parent); self.setObjectName("summaryCard")
        layout = QVBoxLayout(self); layout.setContentsMargins(18, 14, 18, 14)
        layout.addWidget(QLabel(title)); self.value_label = QLabel(value); self.value_label.setObjectName("cardValue"); layout.addWidget(self.value_label)


class ModulePage(QFrame):
    back_requested = Signal()
    def __init__(self, title, description, actions, parent=None):
        super().__init__(parent); self.setObjectName("panel")
        layout = QVBoxLayout(self); layout.setContentsMargins(24, 22, 24, 22)
        heading = QLabel(title); heading.setObjectName("pageTitle"); layout.addWidget(heading)
        text = QLabel(description); text.setWordWrap(True); text.setObjectName("pageDescription"); layout.addWidget(text)
        grid = QGridLayout(); grid.setSpacing(10)
        for i, label in enumerate(actions):
            button = QPushButton(label); button.setObjectName("actionButton"); grid.addWidget(button, i // 3, i % 3)
        layout.addLayout(grid); layout.addStretch()
        back = QPushButton("العودة إلى الرئيسية"); back.setObjectName("secondaryButton"); back.clicked.connect(self.back_requested.emit); layout.addWidget(back, alignment=Qt.AlignLeft)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__(); self.setWindowTitle(BRANDING.program_name); self.resize(1180, 760); self.setMinimumSize(980, 650); self.setLayoutDirection(Qt.RightToLeft)
        self._cards = {}; self._build_ui()

    def _build_ui(self):
        root = QWidget(); root_layout = QVBoxLayout(root); root_layout.setContentsMargins(22, 18, 22, 12); root_layout.setSpacing(12)
        header = QFrame(); header.setObjectName("header"); hl = QHBoxLayout(header); hl.setContentsMargins(22, 16, 22, 16)
        identity = QVBoxLayout(); title = QLabel(BRANDING.program_name); title.setObjectName("appTitle"); identity.addWidget(title)
        subtitle = QLabel("إدارة المبيعات والمشتريات والمخزون والحسابات من مكان واحد"); subtitle.setObjectName("appSubtitle"); identity.addWidget(subtitle); hl.addLayout(identity); hl.addStretch()
        refresh = QPushButton("تحديث البيانات"); refresh.setObjectName("primaryButton"); refresh.clicked.connect(self.refresh_dashboard); hl.addWidget(refresh); root_layout.addWidget(header)
        self.stack = QStackedWidget(); self.dashboard = self._dashboard_page(); self.stack.addWidget(self.dashboard); self._pages = {}
        specs = {
            "المبيعات": ("المبيعات", "إنشاء وإدارة فواتير البيع والتحصيل والمرتجعات.", ["فاتورة بيع جديدة", "مرتجع مبيعات", "سجل المبيعات"]),
            "المشتريات": ("المشتريات", "إدارة فواتير الشراء والموردين والمدفوعات.", ["فاتورة شراء جديدة", "مرتجع مشتريات", "سجل المشتريات"]),
            "المخزون": ("المخزون", "متابعة الأصناف والكميات والحركات وتكلفة المخزون.", ["الأصناف", "حركة المخزون", "جرد المخزون"]),
            "العملاء": ("العملاء", "إدارة بيانات العملاء والأرصدة والتحصيلات.", ["عميل جديد", "قبض من عميل", "كشف حساب"]),
            "الموردون": ("الموردون", "إدارة بيانات الموردين والأرصدة والمدفوعات.", ["مورد جديد", "سداد مورد", "كشف حساب"]),
            "المصروفات": ("المصروفات", "تسجيل ومراجعة المصروفات وربطها بوسيلة الدفع.", ["مصروف جديد", "تصنيفات المصروفات", "سجل المصروفات"]),
            "التقارير": ("التقارير", "تقارير تشغيلية ومالية قابلة للتوسع والطباعة والتصدير.", ["ملخص يومي", "الأرباح والخسائر", "أرصدة العملاء والموردين"]),
        }
        for name, (ptitle, desc, actions) in specs.items():
            if name == "المخزون":
                page = InventoryPage()
            elif name == "المبيعات":
                page = SalesPage()
            elif name == "المشتريات":
                page = PurchasesPage()
            else:
                page = ModulePage(ptitle, desc, actions)
            if hasattr(page, "back_requested"): page.back_requested.connect(self._show_dashboard)
            self._pages[name] = page; self.stack.addWidget(page)
        root_layout.addWidget(self.stack, 1)
        nav = QHBoxLayout(); nav.setSpacing(7)
        for label in ["الرئيسية", *specs.keys()]:
            b = QPushButton(label); b.setObjectName("navButton"); b.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            b.clicked.connect(self._show_dashboard if label == "الرئيسية" else lambda checked=False, name=label: self._show_page(name)); nav.addWidget(b)
        root_layout.addLayout(nav)
        footer = QFrame(); footer.setObjectName("footerPanel"); fl = QHBoxLayout(footer); fl.setContentsMargins(10, 5, 10, 5)
        fl.addWidget(QLabel(f"{BRANDING.designer_credit} | {BRANDING.contact_text}"), 1)
        call = QPushButton("☎ اتصال"); call.setObjectName("linkButton"); call.clicked.connect(lambda: open_url(BRANDING.phone_uri)); fl.addWidget(call)
        wa = QPushButton("واتساب"); wa.setObjectName("linkButton"); wa.clicked.connect(lambda: open_url(BRANDING.whatsapp_uri)); fl.addWidget(wa); root_layout.addWidget(footer)
        self.setCentralWidget(root); self.setStyleSheet(self._stylesheet())

    def _dashboard_page(self):
        page = QWidget(); layout = QVBoxLayout(page); cards = QGridLayout(); cards.setSpacing(12)
        for i, (key, label) in enumerate([("sales", "مبيعات اليوم"), ("purchases", "مشتريات اليوم"), ("expenses", "المصروفات اليوم"), ("profit", "صافي الربح"), ("receivables", "ذمم العملاء"), ("payables", "ذمم الموردين"), ("cash", "رصيد الصندوق"), ("low", "أصناف منخفضة")]):
            card = SummaryCard(label, "0.00"); self._cards[key] = card; cards.addWidget(card, i // 4, i % 4)
        layout.addLayout(cards); quick = QFrame(); quick.setObjectName("panel"); ql = QVBoxLayout(quick); h = QLabel("العمليات الرئيسية"); h.setObjectName("pageTitle"); ql.addWidget(h); row = QHBoxLayout()
        for label, target in [("فاتورة بيع جديدة", "المبيعات"), ("فاتورة شراء جديدة", "المشتريات"), ("إضافة صنف", "المخزون"), ("قبض من عميل", "العملاء"), ("سداد مورد", "الموردون"), ("تسجيل مصروف", "المصروفات")]:
            b = QPushButton(label); b.setObjectName("actionButton"); b.clicked.connect(lambda checked=False, name=target: self._show_page(name)); row.addWidget(b)
        ql.addLayout(row); layout.addWidget(quick, 1); return page

    def _show_dashboard(self): self.stack.setCurrentWidget(self.dashboard); self.refresh_dashboard()
    def _show_page(self, name): self.stack.setCurrentWidget(self._pages[name])

    def refresh_dashboard(self):
        session = get_session()
        try:
            today = date.today().isoformat(); reports = ReportService(session); s = reports.dashboard_summary(date_from=today, date_to=today)
            values = {"sales": s.sales_total, "purchases": s.purchases_total, "expenses": s.expenses_total, "profit": s.gross_profit - s.expenses_total, "receivables": s.customer_receivables, "payables": s.supplier_payables, "cash": s.cash_balance, "low": reports.low_stock_count()}
            for key, value in values.items(): self._cards[key].value_label.setText(str(int(value)) if key == "low" else f"{value:,.2f}")
        finally: session.close()

    @staticmethod
    def _stylesheet():
        return """
        QWidget { font-family: 'Segoe UI'; font-size: 14px; }
        QMainWindow, QWidget { background: #f4f6f8; color: #1f2933; }
        #header, #summaryCard, #panel, #footerPanel { background: white; border: 1px solid #e1e6eb; border-radius: 12px; }
        #appTitle { font-size: 25px; font-weight: 700; } #appSubtitle, #pageDescription { color: #667085; }
        #pageTitle { font-size: 19px; font-weight: 700; } #primaryButton { background: #1769aa; color: white; border: 0; border-radius: 8px; padding: 10px 18px; font-weight: 600; }
        #navButton, #secondaryButton { background: white; border: 1px solid #d9e0e7; border-radius: 8px; padding: 9px 8px; } #navButton:hover, #actionButton:hover { background: #eef5fb; }
        #cardTitle { color: #667085; } #cardValue { font-size: 22px; font-weight: 700; margin-top: 6px; } #actionButton { background: #f8fafc; border: 1px solid #d9e0e7; border-radius: 8px; padding: 12px; }
        #linkButton { background: transparent; border: 0; font-weight: 600; padding: 5px 8px; } #footer { color: #667085; font-size: 12px; }
        """
