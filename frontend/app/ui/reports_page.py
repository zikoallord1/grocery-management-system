from datetime import date, timedelta

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QDateEdit,
)
from PySide6.QtCore import QDate

from backend.app.core.database import get_session
from backend.app.modules.reports.service import ReportService


class ReportsPage(QWidget):
    back_requested = Signal()

    _INDICATORS = [
        ("sales", "إجمالي المبيعات"),
        ("purchases", "إجمالي المشتريات"),
        ("expenses", "إجمالي المصروفات"),
        ("profit", "صافي الربح التشغيلي"),
        ("receivables", "ذمم العملاء"),
        ("payables", "ذمم الموردين"),
        ("cash", "رصيد الصندوق"),
        ("low", "أصناف منخفضة"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self.cards = {}
        self.period_label = QLabel()
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["المؤشر", "القيمة"])
        self.table.setAlternatingRowColors(True)
        self._build()
        self.show_today()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(12)

        title = QLabel("التقارير")
        title.setObjectName("pageTitle")
        root.addWidget(title)

        desc = QLabel(
            "ملخص تشغيلي ومالي للفترة المحددة، مبني مباشرة على العمليات المسجلة في النظام."
        )
        desc.setWordWrap(True)
        root.addWidget(desc)

        buttons = QHBoxLayout()
        for text, slot in [
            ("اليوم", self.show_today),
            ("هذا الأسبوع", self.show_week),
            ("هذا الشهر", self.show_month),
        ]:
            button = QPushButton(text)
            button.clicked.connect(slot)
            buttons.addWidget(button)
        self.date_from = QDateEdit(QDate.currentDate())
        self.date_from.setCalendarPopup(True)
        self.date_to = QDateEdit(QDate.currentDate())
        self.date_to.setCalendarPopup(True)
        custom = QPushButton("تطبيق فترة مخصصة")
        custom.clicked.connect(self.show_custom)
        buttons.addWidget(QLabel("من"))
        buttons.addWidget(self.date_from)
        buttons.addWidget(QLabel("إلى"))
        buttons.addWidget(self.date_to)
        buttons.addWidget(custom)

        back = QPushButton("العودة إلى الرئيسية")
        back.clicked.connect(self.back_requested.emit)
        buttons.addWidget(back)
        root.addLayout(buttons)

        self.period_label.setObjectName("pageDescription")
        root.addWidget(self.period_label)

        grid = QGridLayout()
        grid.setSpacing(10)
        for i, (key, name) in enumerate(self._INDICATORS):
            card = QWidget()
            card.setObjectName("summaryCard")
            lay = QVBoxLayout(card)
            lay.setContentsMargins(14, 10, 14, 10)
            label = QLabel(name)
            label.setObjectName("reportCardLabel")
            value = QLabel("0.00")
            value.setObjectName("cardValue")
            lay.addWidget(label)
            lay.addWidget(value)
            self.cards[key] = value
            grid.addWidget(card, i // 4, i % 4)
        root.addLayout(grid)

        root.addWidget(self.table, 1)
        self.table.resizeColumnsToContents()

    def _load(self, start, end, label):
        session = get_session()
        try:
            report_service = ReportService(session)
            summary = report_service.dashboard_summary(
                date_from=start.isoformat(),
                date_to=end.isoformat(),
            )
            values = {
                "sales": summary.sales_total,
                "purchases": summary.purchases_total,
                "expenses": summary.expenses_total,
                "profit": summary.gross_profit - summary.expenses_total,
                "receivables": summary.customer_receivables,
                "payables": summary.supplier_payables,
                "cash": summary.cash_balance,
                "low": report_service.low_stock_count(),
            }

            for key, value in values.items():
                self.cards[key].setText(
                    str(int(value)) if key == "low" else f"{value:,.2f}"
                )

            self.period_label.setText(
                f"الفترة: {label} ({start.isoformat()} إلى {end.isoformat()})"
            )

            self.table.setRowCount(0)
            for key, name in self._INDICATORS:
                row = self.table.rowCount()
                self.table.insertRow(row)
                self.table.setItem(row, 0, QTableWidgetItem(name))
                self.table.setItem(row, 1, QTableWidgetItem(self.cards[key].text()))
            self.table.resizeColumnsToContents()
        finally:
            session.close()

    def show_today(self):
        current = date.today()
        self._load(current, current, "اليوم")

    def show_week(self):
        current = date.today()
        start = current - timedelta(days=current.weekday())
        self._load(start, current, "هذا الأسبوع")

    def show_month(self):
        current = date.today()
        start = current.replace(day=1)
        self._load(start, current, "هذا الشهر")

    def refresh(self):
        self.show_today()

    def show_custom(self):
        start = self.date_from.date().toPython()
        end = self.date_to.date().toPython()
        if start > end:
            self.period_label.setText("الفترة غير صحيحة: يجب أن يسبق تاريخ البداية تاريخ النهاية.")
            return
        self._load(start, end, "فترة مخصصة")
