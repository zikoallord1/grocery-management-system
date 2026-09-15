from datetime import date
from decimal import Decimal
from uuid import uuid4

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QComboBox, QDoubleSpinBox, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget
from sqlalchemy import select

from backend.app.core.database import get_session
from backend.app.modules.finance.models import Expense, ExpenseCategory, PaymentMethod
from backend.app.modules.expenses.service import ExpenseService


class ExpensesPage(QWidget):
    back_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self.expense_no = QLineEdit()
        self.description = QLineEdit()
        self.category = QComboBox()
        self.payment_method = QComboBox()
        self.amount = QDoubleSpinBox()
        self.amount.setRange(0, 999999999)
        self.amount.setDecimals(2)
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["التاريخ", "رقم المصروف", "التصنيف", "البيان", "المبلغ", "الحالة"])
        self._build()
        self.refresh()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(14)
        title = QLabel("المصروفات")
        title.setObjectName("pageTitle")
        root.addWidget(title)
        desc = QLabel("سجل المصروف نقدًا عند توفر رصيد، أو اختر «آجل / غير مدفوع» لتسجيل المصروف دون سحب من الصندوق.")
        desc.setWordWrap(True)
        desc.setObjectName("pageDescription")
        root.addWidget(desc)
        form = QFormLayout()
        form.setSpacing(12)
        form.addRow("رقم المصروف", self.expense_no)
        form.addRow("تصنيف المصروف", self.category)
        form.addRow("البيان", self.description)
        form.addRow("المبلغ", self.amount)
        form.addRow("وسيلة الدفع", self.payment_method)
        root.addLayout(form)
        buttons = QHBoxLayout()
        save = QPushButton("حفظ وتأكيد المصروف")
        save.setObjectName("primaryButton")
        save.clicked.connect(self.save_expense)
        buttons.addWidget(save)
        refresh = QPushButton("تحديث")
        refresh.setObjectName("actionButton")
        refresh.clicked.connect(self.refresh)
        buttons.addWidget(refresh)
        back = QPushButton("العودة إلى الرئيسية")
        back.setObjectName("secondaryButton")
        back.clicked.connect(self.back_requested.emit)
        buttons.addWidget(back)
        root.addLayout(buttons)
        root.addWidget(self.table, 1)

    def refresh(self):
        session = get_session()
        try:
            self.category.clear()
            self.payment_method.clear()
            categories = session.scalars(select(ExpenseCategory).where(ExpenseCategory.is_active.is_(True)).order_by(ExpenseCategory.name)).all()
            for category in categories:
                self.category.addItem(category.name, category.id)
            methods = session.scalars(select(PaymentMethod).where(PaymentMethod.is_active.is_(True)).order_by(PaymentMethod.code)).all()
            for method in methods:
                self.payment_method.addItem(method.name, method.id)
            credit_index = self.payment_method.findData(next((m.id for m in methods if m.code == "CREDIT"), None))
            if credit_index >= 0:
                self.payment_method.setCurrentIndex(credit_index)
            self.table.setRowCount(0)
            rows = session.scalars(select(Expense).order_by(Expense.id.desc()).limit(100)).all()
            categories_map = {c.id: c.name for c in session.scalars(select(ExpenseCategory)).all()}
            for expense in rows:
                row = self.table.rowCount()
                self.table.insertRow(row)
                values = [expense.business_date, expense.expense_no, categories_map.get(expense.category_id, ""), expense.description, f"{expense.amount:,.2f}", expense.status]
                for col, value in enumerate(values):
                    self.table.setItem(row, col, QTableWidgetItem(str(value)))
            if not self.expense_no.text().strip():
                self.expense_no.setText(f"E-{date.today().strftime('%Y%m%d')}-{uuid4().hex[:8].upper()}")
        finally:
            session.close()

    def save_expense(self):
        no = self.expense_no.text().strip()
        description = self.description.text().strip()
        category_id = self.category.currentData()
        method_id = self.payment_method.currentData()
        amount = Decimal(str(self.amount.value()))
        if not no or not description or category_id is None:
            QMessageBox.warning(self, "بيانات ناقصة", "أدخل رقم المصروف والتصنيف والبيان.")
            return
        if amount <= 0:
            QMessageBox.warning(self, "مبلغ غير صحيح", "أدخل مبلغًا أكبر من صفر.")
            return
        if method_id is None:
            QMessageBox.warning(self, "وسيلة الدفع", "اختر وسيلة الدفع.")
            return
        session = get_session()
        try:
            ExpenseService(session).create_expense(
                expense_no=no,
                category_id=int(category_id),
                description=description,
                amount=amount,
                business_date=date.today().isoformat(),
                payment_method_id=int(method_id),
                idempotency_key=str(uuid4()),
            )
            session.commit()
        except Exception as exc:
            session.rollback()
            QMessageBox.critical(self, "تعذر الحفظ", f"لم يتم تسجيل المصروف.\n\nالسبب: {exc}")
            return
        finally:
            session.close()
        self.description.clear()
        self.amount.setValue(0)
        self.expense_no.clear()
        self.refresh()
        QMessageBox.information(self, "تم الحفظ", "تم تسجيل المصروف بنجاح.")
