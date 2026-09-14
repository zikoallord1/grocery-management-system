from datetime import date
from decimal import Decimal
from uuid import uuid4

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDoubleSpinBox, QFormLayout, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
    QComboBox,
)
from sqlalchemy import select

from backend.app.core.database import get_session
from backend.app.core.models import Supplier, SupplierAccountMovement
from backend.app.modules.finance.models import PaymentMethod
from backend.app.modules.suppliers.service import SupplierService


class SuppliersPage(QWidget):
    back_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self.selected_supplier_id = None
        self.code = QLineEdit()
        self.name = QLineEdit()
        self.phone = QLineEdit()
        self.address = QLineEdit()
        self.credit_limit = QDoubleSpinBox(); self.credit_limit.setRange(0, 999999999); self.credit_limit.setDecimals(2)
        self.search = QLineEdit(); self.search.setPlaceholderText("بحث باسم المورد أو الرمز...")
        self.payment_amount = QDoubleSpinBox(); self.payment_amount.setRange(0, 999999999); self.payment_amount.setDecimals(2)
        self.payment_method = QComboBox()
        self.balance_label = QLabel("0.00")
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["الرمز", "المورد", "الهاتف", "الرصيد", "الحالة"])
        self._build()
        self.refresh_data()

    def _build(self):
        root = QVBoxLayout(self)
        title = QLabel("الموردون"); title.setObjectName("pageTitle"); root.addWidget(title)
        desc = QLabel("إدارة الموردين وأرصدتهم وسداد المستحقات وربط السداد بالصندوق تلقائيًا."); desc.setWordWrap(True); desc.setObjectName("pageDescription"); root.addWidget(desc)
        form = QFormLayout()
        form.addRow("رمز المورد", self.code); form.addRow("اسم المورد", self.name); form.addRow("الهاتف", self.phone); form.addRow("العنوان", self.address); form.addRow("حد الائتمان", self.credit_limit)
        root.addLayout(form)
        buttons = QHBoxLayout()
        for text, slot, obj in [("حفظ المورد", self.save_supplier, "primaryButton"), ("تعديل المورد", self.update_supplier, "actionButton"), ("إيقاف المورد", self.deactivate_supplier, "actionButton"), ("تحديث", self.refresh_data, "actionButton")]:
            b = QPushButton(text); b.setObjectName(obj); b.clicked.connect(slot); buttons.addWidget(b)
        root.addLayout(buttons)
        root.addWidget(self.search)
        self.search.textChanged.connect(self.refresh_data)
        self.table.cellClicked.connect(self.select_supplier)
        root.addWidget(self.table, 1)
        pay = QFormLayout(); pay.addRow("رصيد المورد المحدد", self.balance_label); pay.addRow("مبلغ السداد", self.payment_amount); pay.addRow("وسيلة الدفع", self.payment_method); root.addLayout(pay)
        pay_buttons = QHBoxLayout(); b = QPushButton("سداد المورد"); b.setObjectName("primaryButton"); b.clicked.connect(self.make_payment); pay_buttons.addWidget(b); back = QPushButton("العودة إلى الرئيسية"); back.setObjectName("secondaryButton"); back.clicked.connect(self.back_requested.emit); pay_buttons.addWidget(back); root.addLayout(pay_buttons)

    def refresh_data(self):
        session = get_session()
        try:
            text = self.search.text().strip()
            stmt = select(Supplier).order_by(Supplier.name)
            if text:
                stmt = stmt.where((Supplier.name.contains(text)) | (Supplier.code.contains(text)))
            suppliers = session.scalars(stmt).all()
            self.table.setRowCount(0)
            for supplier in suppliers:
                row = self.table.rowCount(); self.table.insertRow(row)
                balance = SupplierService(session).get_balance(supplier.id)
                values = [supplier.code, supplier.name, supplier.phone or "", f"{balance:,.2f}", "نشط" if supplier.is_active else "موقوف"]
                for col, value in enumerate(values): self.table.setItem(row, col, QTableWidgetItem(str(value)))
                self.table.item(row, 0).setData(Qt.UserRole, supplier.id)
            self.payment_method.clear()
            methods = session.scalars(select(PaymentMethod).where(PaymentMethod.is_active.is_(True)).order_by(PaymentMethod.name)).all()
            for method in methods: self.payment_method.addItem(method.name, method.code)
            if self.selected_supplier_id:
                supplier = session.get(Supplier, self.selected_supplier_id)
                self.balance_label.setText(f"{SupplierService(session).get_balance(self.selected_supplier_id):,.2f}" if supplier else "0.00")
        finally: session.close()

    def _clear(self):
        self.selected_supplier_id = None; self.code.clear(); self.name.clear(); self.phone.clear(); self.address.clear(); self.credit_limit.setValue(0); self.balance_label.setText("0.00")

    def save_supplier(self):
        code, name = self.code.text().strip(), self.name.text().strip()
        if not code or not name: QMessageBox.warning(self, "بيانات ناقصة", "أدخل رمز المورد واسم المورد."); return
        session = get_session()
        try:
            if session.scalar(select(Supplier).where(Supplier.code == code)) is not None: raise ValueError("رمز المورد مستخدم مسبقًا.")
            session.add(Supplier(code=code, name=name, phone=self.phone.text().strip() or None, address=self.address.text().strip() or None, credit_limit=Decimal(str(self.credit_limit.value())) or None, is_active=True))
            session.commit(); self.refresh_data(); self._clear(); QMessageBox.information(self, "تم الحفظ", "تم حفظ المورد بنجاح.")
        except Exception as exc: session.rollback(); QMessageBox.critical(self, "تعذر الحفظ", str(exc))
        finally: session.close()

    def select_supplier(self, row, _column):
        item = self.table.item(row, 0); self.selected_supplier_id = item.data(Qt.UserRole) if item else None
        session = get_session()
        try:
            supplier = session.get(Supplier, self.selected_supplier_id)
            if supplier:
                self.code.setText(supplier.code); self.name.setText(supplier.name); self.phone.setText(supplier.phone or ""); self.address.setText(supplier.address or ""); self.credit_limit.setValue(float(supplier.credit_limit or 0)); self.balance_label.setText(f"{SupplierService(session).get_balance(supplier.id):,.2f}")
        finally: session.close()

    def update_supplier(self):
        if not self.selected_supplier_id: QMessageBox.warning(self, "اختيار المورد", "اختر موردًا من الجدول أولًا."); return
        session = get_session()
        try:
            supplier = session.get(Supplier, self.selected_supplier_id)
            if not supplier: raise ValueError("المورد غير موجود.")
            supplier.code=self.code.text().strip(); supplier.name=self.name.text().strip(); supplier.phone=self.phone.text().strip() or None; supplier.address=self.address.text().strip() or None; supplier.credit_limit=Decimal(str(self.credit_limit.value())) or None
            session.commit(); self.refresh_data(); QMessageBox.information(self, "تم التحديث", "تم تحديث بيانات المورد.")
        except Exception as exc: session.rollback(); QMessageBox.critical(self, "تعذر التحديث", str(exc))
        finally: session.close()

    def deactivate_supplier(self):
        if not self.selected_supplier_id: QMessageBox.warning(self, "اختيار المورد", "اختر موردًا من الجدول أولًا."); return
        session = get_session()
        try:
            supplier=session.get(Supplier,self.selected_supplier_id)
            if supplier: supplier.is_active=False; session.commit(); self.refresh_data(); QMessageBox.information(self,"تم الإيقاف","تم إيقاف المورد دون حذف سجله.")
        finally: session.close()

    def make_payment(self):
        if not self.selected_supplier_id: QMessageBox.warning(self, "اختيار المورد", "اختر المورد أولًا."); return
        amount=Decimal(str(self.payment_amount.value()))
        if amount <= 0: QMessageBox.warning(self,"مبلغ غير صحيح","أدخل مبلغ السداد."); return
        if self.payment_method.currentData() is None: QMessageBox.warning(self,"وسيلة الدفع","اختر وسيلة الدفع."); return
        session=get_session()
        try:
            balance=SupplierService(session).get_balance(self.selected_supplier_id)
            if amount > balance: raise ValueError(f"مبلغ السداد أكبر من رصيد المورد: {balance:,.2f}")
            SupplierService(session).make_payment(supplier_id=self.selected_supplier_id, amount=amount, business_date=date.today().isoformat(), payment_method=self.payment_method.currentData(), idempotency_key=str(uuid4()), reference_no=f"SP-{date.today().strftime('%Y%m%d')}-{uuid4().hex[:8].upper()}")
            session.commit(); self.payment_amount.setValue(0); self.refresh_data(); QMessageBox.information(self,"تم السداد","تم تسجيل سداد المورد وربطه بالصندوق.")
        except Exception as exc: session.rollback(); QMessageBox.critical(self,"تعذر السداد",str(exc))
        finally: session.close()
