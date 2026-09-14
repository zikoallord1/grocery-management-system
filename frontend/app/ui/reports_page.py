from datetime import date, timedelta

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from backend.app.core.database import get_session
from backend.app.modules.reports.service import ReportService


class ReportsPage(QWidget):
    back_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self.cards = {}
        self.period_label = QLabel()
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["المؤشر", "القيمة"])
        self._build()
        self.show_today()

    def _build(self):
        root = QVBoxLayout(self)
        title = QLabel("التقارير"); title.setObjectName("pageTitle"); root.addWidget(title)
        desc = QLabel("ملخص تشغيلي ومالي للفترة المحددة، مبني مباشرة على العمليات المسجلة في النظام."); desc.setWordWrap(True); root.addWidget(desc)
        buttons = QHBoxLayout()
        for text, slot in [("اليوم", self.show_today), ("هذا الأسبوع", self.show_week), ("هذا الشهر", self.show_month)]:
            b=QPushButton(text); b.clicked.connect(slot); buttons.addWidget(b)
        back=QPushButton("العودة إلى الرئيسية"); back.clicked.connect(self.back_requested.emit); buttons.addWidget(back); root.addLayout(buttons)
        self.period_label.setObjectName("pageDescription"); root.addWidget(self.period_label)
        grid=QGridLayout(); grid.setSpacing(10)
        for i,key in enumerate(["sales","purchases","expenses","profit","receivables","payables","cash","low"]):
            card=QWidget(); lay=QVBoxLayout(card); label=QLabel(key); value=QLabel("0"); value.setObjectName("cardValue"); lay.addWidget(label); lay.addWidget(value); self.cards[key]=value; grid.addWidget(card,i//4,i%4)
        root.addLayout(grid)
        root.addWidget(self.table,1)

    def _load(self, start, end, label):
        session=get_session()
        try:
            r=ReportService(session); s=r.dashboard_summary(date_from=start.isoformat(),date_to=end.isoformat())
            values={"sales":s.sales_total,"purchases":s.purchases_total,"expenses":s.expenses_total,"profit":s.gross_profit-s.expenses_total,"receivables":s.customer_receivables,"payables":s.supplier_payables,"cash":s.cash_balance,"low":r.low_stock_count()}
            names={"sales":"إجمالي المبيعات","purchases":"إجمالي المشتريات","expenses":"إجمالي المصروفات","profit":"صافي الربح التشغيلي","receivables":"ذمم العملاء","payables":"ذمم الموردين","cash":"رصيد الصندوق","low":"أصناف منخفضة"}
            for k,v in values.items(): self.cards[k].setText(str(int(v)) if k=="low" else f"{v:,.2f}")
            self.period_label.setText(f"الفترة: {label} ({start.isoformat()} إلى {end.isoformat()})")
            self.table.setRowCount(0)
            for k in ["sales","purchases","expenses","profit","receivables","payables","cash","low"]:
                row=self.table.rowCount(); self.table.insertRow(row); self.table.setItem(row,0,QTableWidgetItem(names[k])); self.table.setItem(row,1,QTableWidgetItem(self.cards[k].text()))
        finally: session.close()

    def show_today(self):
        d=date.today(); self._load(d,d,"اليوم")
    def show_week(self):
        d=date.today(); start=d-timedelta(days=d.weekday()); self._load(start,d,"هذا الأسبوع")
    def show_month(self):
        d=date.today(); start=d.replace(day=1); self._load(start,d,"هذا الشهر")
    def refresh(self): self.show_today()
