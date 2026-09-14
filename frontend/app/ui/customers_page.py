from datetime import date
from decimal import Decimal
from uuid import uuid4

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox, QDoubleSpinBox, QFormLayout, QHBoxLayout, QLabel,
    QLineEdit, QMessageBox, QPushButton, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)
from sqlalchemy import case, func, select

from backend.app.core.database import get_session
from backend.app.core.models import Customer, CustomerAccountMovement
from backend.app.modules.customers.service import CustomerService
from backend.app.modules.finance.models import PaymentMethod


class CustomersPage(QWidget):
    back_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self.selected_customer_id = None
        self.code = QLineEdit()
        self.name = QLineEdit()
        self.phone = QLineEdit()
        self.address = QLineEdit()
        self.credit_limit = QDoubleSpinBox()
        self.credit_limit.setRange(0, 999999999)
        self.credit_limit.setDecimals(2)
        self.payment_amount = QDoubleSpinBox()
        self.payment_amount.setRange(0, 999999999)
        self.payment_amount.setDecimals(2)
        self.customer = QComboBox()
        self.payment_method = QComboBox()
        self.balance_label = QLabel("0.00")
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(["الرمز", "اسم العميل", "الهاتف", "الرصيد", "حد الائتمان", "الحالة", "الإجراء"])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._build()
        self.refresh()

    def _build(self):
        root = QVBoxLayout(self)
        title = QLabel("العملاء والتحصيل")
        title.setObjectName("pageTitle")
        root.addWidget(title)
        desc = QLabel("إدارة بيانات العملاء، متابعة الذمم، وتسجيل التحصيل مع ربطه بالصندوق ووسيلة الدفع.")
        desc.setWordWrap(True)
        desc.setObjectName("pageDescription")
        root.addWidget(desc)

        form = QFormLayout()
        form.addRow("رمز العميل", self.code)
        form.addRow("اسم العميل", self.name)
        form.addRow("الهاتف", self.phone)
        form.addRow("العنوان", self.address)
        form.addRow("حد الائتمان", self.credit_limit)
        root.addLayout(form)
        buttons = QHBoxLayout()
        save = QPushButton("حفظ العميل")
        save.setObjectName("primaryButton")
        save.clicked.connect(self.save_customer)
        update = QPushButton("تعديل العميل المحدد")
        update.clicked.connect(self.update_customer)
        clear = QPushButton("جديد")
        clear.clicked.connect(self.clear_form)
        refresh = QPushButton("تحديث")
        refresh.clicked.connect(self.refresh)
        buttons.addWidget(save); buttons.addWidget(update); buttons.addWidget(clear); buttons.addWidget(refresh); buttons.addStretch()
        root.addLayout(buttons)

        collect = QFormLayout()
        collect.addRow("العميل للتحصيل", self.customer)
        collect.addRow("المبلغ", self.payment_amount)
        collect.addRow("وسيلة الدفع", self.payment_method)
        collect.addRow("الرصيد الحالي", self.balance_label)
        root.addLayout(collect)
        collect_button = QPushButton("تسجيل تحصيل")
        collect_button.setObjectName("primaryButton")
        collect_button.clicked.connect(self.receive_payment)
        root.addWidget(collect_button)
        self.customer.currentIndexChanged.connect(self.customer_changed)
        root.addWidget(self.table, 1)
        back = QPushButton("العودة إلى الرئيسية")
        back.setObjectName("secondaryButton")
        back.clicked.connect(self.back_requested.emit)
        root.addWidget(back)
        self.table.cellClicked.connect(self.table_selected)

    def refresh(self):
        session = get_session()
        try:
            self._load_customers(session)
            self._load_payment_methods(session)
            self._load_table(session)
            self.customer_changed()
        finally:
            session.close()

    def _load_customers(self, session):
        current = self.customer.currentData()
        self.customer.blockSignals(True)
        self.customer.clear()
        self.customer.addItem("اختر العميل", None)
        rows = session.scalars(select(Customer).where(Customer.is_active.is_(True)).order_by(Customer.name)).all()
        for item in rows:
            self.customer.addItem(f"{item.name} — {item.code}", item.id)
        if current is not None:
            idx = self.customer.findData(current)
            if idx >= 0:
                self.customer.setCurrentIndex(idx)
        self.customer.blockSignals(False)

    def _load_payment_methods(self, session):
        current = self.payment_method.currentData()
        self.payment_method.clear()
        methods = session.scalars(select(PaymentMethod).where(PaymentMethod.is_active.is_(True)).order_by(PaymentMethod.name)).all()
        for method in methods:
            self.payment_method.addItem(method.name, method.code)
        if current is not None:
            idx = self.payment_method.findData(current)
            if idx >= 0:
                self.payment_method.setCurrentIndex(idx)

    def _balance(self, session, customer_id):
        signed = case((CustomerAccountMovement.direction == "DEBIT", CustomerAccountMovement.amount), (CustomerAccountMovement.direction == "CREDIT", -CustomerAccountMovement.amount), else_=0)
        value = session.execute(select(func.coalesce(func.sum(signed), 0)).where(CustomerAccountMovement.customer_id == customer_id)).scalar_one()
        return Decimal(str(value))

    def _load_table(self, session):
        customers = session.scalars(select(Customer).order_by(Customer.name)).all()
        self.table.setRowCount(len(customers))
        for r, customer in enumerate(customers):
            balance = self._balance(session, customer.id)
            values = [customer.code, customer.name, customer.phone or "", f"{balance:,.2f}", f"{Decimal(str(customer.credit_limit)):,.2f}" if customer.credit_limit is not None else "غير محدد", "نشط" if customer.is_active else "موقوف", "اختيار"]
            for c, value in enumerate(values):
                self.table.setItem(r, c, QTableWidgetItem(str(value)))
        self.table.resizeColumnsToContents()

    def table_selected(self, row, _column):
        code = self.table.item(row, 0)
        if code is None:
            return
        session = get_session()
        try:
            customer = session.scalar(select(Customer).where(Customer.code == code.text()))
            if customer is None:
                return
            self.selected_customer_id = customer.id
            self.code.setText(customer.code)
            self.name.setText(customer.name)
            self.phone.setText(customer.phone or "")
            self.address.setText(customer.address or "")
            self.credit_limit.setValue(float(customer.credit_limit or 0))
        finally:
            session.close()

    def clear_form(self):
        self.selected_customer_id = None
        self.code.clear(); self.name.clear(); self.phone.clear(); self.address.clear(); self.credit_limit.setValue(0)

    def save_customer(self):
        code, name = self.code.text().strip(), self.name.text().strip()
        if not code or not name:
            QMessageBox.warning(self, "بيانات ناقصة", "رمز العميل واسم العميل مطلوبان.")
            return
        session = get_session()
        try:
            if session.scalar(select(Customer).where(Customer.code == code)):
                raise ValueError("رمز العميل مستخدم مسبقًا.")
            customer = Customer(code=code, name=name, phone=self.phone.text().strip() or None, address=self.address.text().strip() or None, credit_limit=Decimal(str(self.credit_limit.value())) if self.credit_limit.value() > 0 else None, is_active=True)
            session.add(customer); session.commit()
            self.clear_form(); self.refresh()
        except Exception as exc:
            session.rollback(); QMessageBox.critical(self, "تعذر الحفظ", str(exc))
        finally:
            session.close()

    def update_customer(self):
        if self.selected_customer_id is None:
            QMessageBox.warning(self, "لم يتم الاختيار", "اختر عميلًا من الجدول أولًا.")
            return
        session = get_session()
        try:
            customer = session.get(Customer, self.selected_customer_id)
            if customer is None:
                raise ValueError("العميل غير موجود.")
            duplicate = session.scalar(select(Customer).where(Customer.code == self.code.text().strip(), Customer.id != customer.id))
            if duplicate:
                raise ValueError("رمز العميل مستخدم مسبقًا.")
            customer.code = self.code.text().strip(); customer.name = self.name.text().strip(); customer.phone = self.phone.text().strip() or None; customer.address = self.address.text().strip() or None; customer.credit_limit = Decimal(str(self.credit_limit.value())) if self.credit_limit.value() > 0 else None
            session.commit(); self.refresh()
        except Exception as exc:
            session.rollback(); QMessageBox.critical(self, "تعذر التعديل", str(exc))
        finally:
            session.close()

    def customer_changed(self):
        customer_id = self.customer.currentData()
        if customer_id is None:
            self.balance_label.setText("0.00")
            return
        session = get_session()
        try:
            balance = CustomerService(session).get_balance(customer_id)
            self.balance_label.setText(f"{balance:,.2f}")
            self.payment_amount.setMaximum(float(balance) if balance > 0 else 0)
        finally:
            session.close()

    def receive_payment(self):
        customer_id = self.customer.currentData()
        amount = Decimal(str(self.payment_amount.value()))
        method = self.payment_method.currentData()
        if customer_id is None or amount <= 0 or not method:
            QMessageBox.warning(self, "بيانات ناقصة", "اختر العميل ووسيلة الدفع وأدخل مبلغًا صحيحًا.")
            return
        session = get_session()
        try:
            payment = CustomerService(session).receive_payment(customer_id=customer_id, amount=amount, business_date=date.today().isoformat(), payment_method=method, idempotency_key=str(uuid4()), reference_no=f"CP-{date.today().strftime('%Y%m%d')}-{uuid4().hex[:8].upper()}")
            session.commit()
            QMessageBox.information(self, "تم التحصيل", f"تم تسجيل التحصيل بمبلغ {payment.amount:,.2f}.")
            self.payment_amount.setValue(0); self.refresh()
        except Exception as exc:
            session.rollback(); QMessageBox.critical(self, "تعذر تسجيل التحصيل", str(exc))
        finally:
            session.close()
