from datetime import date
from decimal import Decimal
from uuid import uuid4

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QComboBox, QDoubleSpinBox, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget
from sqlalchemy import select

from backend.app.core.database import get_session
from backend.app.modules.finance.models import PaymentMethod
from backend.app.modules.finance.revenue import Revenue, RevenueService


class RevenuesPage(QWidget):
    back_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self.revenue_no = QLineEdit()
        self.description = QLineEdit()
        self.amount = QDoubleSpinBox(); self.amount.setRange(0, 999999999); self.amount.setDecimals(2)
        self.payment_method = QComboBox()
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["التاريخ", "الرقم", "البيان", "المبلغ", "الحالة"])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._build(); self.refresh()

    def _build(self):
        root = QVBoxLayout(self); root.setContentsMargins(28, 24, 28, 24); root.setSpacing(14)
        title = QLabel("الإيرادات الأخرى"); title.setObjectName("pageTitle"); root.addWidget(title)
        desc = QLabel("تسجيل أي إيراد غير ناتج عن فاتورة بيع وربطه مباشرة بوسيلة الدفع والحساب المالي."); desc.setWordWrap(True); desc.setObjectName("pageDescription"); root.addWidget(desc)
        form = QFormLayout(); form.setSpacing(12)
        self.revenue_no.setPlaceholderText("اختياري — يولد تلقائيًا")
        self.description.setPlaceholderText("بيان الإيراد")
        form.addRow("رقم الإيراد", self.revenue_no); form.addRow("البيان *", self.description); form.addRow("المبلغ *", self.amount); form.addRow("وسيلة الدفع *", self.payment_method)
        root.addLayout(form)
        row = QHBoxLayout()
        save = QPushButton("حفظ الإيراد"); save.setObjectName("primaryButton"); save.clicked.connect(self.save_revenue)
        new = QPushButton("جديد"); new.clicked.connect(self.clear_form)
        refresh = QPushButton("تحديث"); refresh.clicked.connect(self.refresh)
        back = QPushButton("العودة إلى الرئيسية"); back.setObjectName("secondaryButton"); back.clicked.connect(self.back_requested.emit)
        for b in (save, new, refresh, back): row.addWidget(b)
        root.addLayout(row); root.addWidget(self.table, 1)

    def refresh(self):
        session = get_session()
        try:
            current = self.payment_method.currentData(); self.payment_method.clear()
            for method in session.scalars(select(PaymentMethod).where(PaymentMethod.is_active.is_(True), PaymentMethod.cashbox_id.is_not(None)).order_by(PaymentMethod.name)).all():
                self.payment_method.addItem(method.name, method.id)
            if current is not None:
                idx = self.payment_method.findData(current)
                if idx >= 0: self.payment_method.setCurrentIndex(idx)
            self.table.setRowCount(0)
            for revenue in session.scalars(select(Revenue).order_by(Revenue.id.desc()).limit(100)).all():
                r = self.table.rowCount(); self.table.insertRow(r)
                vals = [revenue.business_date, revenue.revenue_no, revenue.description, f"{revenue.amount:,.2f}", revenue.status]
                for c, value in enumerate(vals): self.table.setItem(r, c, QTableWidgetItem(str(value)))
            if not self.revenue_no.text().strip(): self.revenue_no.setText(f"R-{date.today():%Y%m%d}-{uuid4().hex[:8].upper()}")
        except Exception as exc:
            session.rollback(); QMessageBox.critical(self, "تعذر التحميل", str(exc))
        finally: session.close()

    def clear_form(self):
        self.revenue_no.clear(); self.description.clear(); self.amount.setValue(0); self.refresh()

    def save_revenue(self):
        description = self.description.text().strip(); amount = Decimal(str(self.amount.value())).quantize(Decimal("0.01")); method_id = self.payment_method.currentData()
        if not description: QMessageBox.warning(self, "البيان", "أدخل بيان الإيراد."); self.description.setFocus(); return
        if amount <= 0: QMessageBox.warning(self, "المبلغ", "أدخل مبلغًا أكبر من صفر."); self.amount.setFocus(); return
        if method_id is None: QMessageBox.warning(self, "وسيلة الدفع", "اختر وسيلة الدفع."); return
        session = get_session()
        try:
            no = self.revenue_no.text().strip() or f"R-{date.today():%Y%m%d}-{uuid4().hex[:8].upper()}"
            RevenueService(session).create_revenue(revenue_no=no, description=description, amount=amount, business_date=date.today().isoformat(), payment_method_id=int(method_id), idempotency_key=str(uuid4()))
            session.commit(); self.description.clear(); self.amount.setValue(0); self.revenue_no.clear(); self.refresh(); QMessageBox.information(self, "تم الحفظ", "تم تسجيل الإيراد بنجاح.")
        except Exception as exc:
            session.rollback(); QMessageBox.critical(self, "تعذر الحفظ", str(exc))
        finally: session.close()
