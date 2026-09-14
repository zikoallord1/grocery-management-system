from datetime import date
from decimal import Decimal
from uuid import uuid4

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox, QDoubleSpinBox, QFormLayout, QHBoxLayout, QLabel,
    QMessageBox, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)
from sqlalchemy import select

from backend.app.core.database import get_session
from backend.app.modules.finance.models import Cashbox, CashboxMovement
from backend.app.modules.finance.service import CashboxService


class CashboxesPage(QWidget):
    back_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self.selected_cashbox_id = None
        self.source = QComboBox()
        self.target = QComboBox()
        self.amount = QDoubleSpinBox()
        self.amount.setRange(0, 999999999)
        self.amount.setDecimals(2)
        self.balance_label = QLabel("0.00")
        self.cashboxes_table = QTableWidget(0, 5)
        self.cashboxes_table.setHorizontalHeaderLabels(["الرمز", "الحساب", "النوع", "العملة", "الرصيد"])
        self.movements_table = QTableWidget(0, 6)
        self.movements_table.setHorizontalHeaderLabels(["التاريخ", "الحساب", "الحركة", "الاتجاه", "المبلغ", "المرجع"])
        self._build()
        self.refresh()

    def _build(self):
        root = QVBoxLayout(self)
        title = QLabel("الصناديق والحسابات النقدية")
        title.setObjectName("pageTitle")
        root.addWidget(title)
        desc = QLabel("متابعة أرصدة النقد والمحفظة والحساب البنكي وتحويل الأموال بينها مع منع الصرف بأكثر من الرصيد المتاح.")
        desc.setWordWrap(True)
        desc.setObjectName("pageDescription")
        root.addWidget(desc)
        root.addWidget(self.cashboxes_table, 1)
        self.cashboxes_table.cellClicked.connect(self.select_cashbox)
        root.addWidget(QLabel("رصيد الحساب المحدد"))
        root.addWidget(self.balance_label)
        form = QFormLayout()
        form.addRow("من حساب", self.source)
        form.addRow("إلى حساب", self.target)
        form.addRow("مبلغ التحويل", self.amount)
        root.addLayout(form)
        buttons = QHBoxLayout()
        transfer = QPushButton("تحويل بين الحسابات")
        transfer.setObjectName("primaryButton")
        transfer.clicked.connect(self.transfer)
        buttons.addWidget(transfer)
        refresh = QPushButton("تحديث")
        refresh.clicked.connect(self.refresh)
        buttons.addWidget(refresh)
        back = QPushButton("العودة إلى الرئيسية")
        back.setObjectName("secondaryButton")
        back.clicked.connect(self.back_requested.emit)
        buttons.addWidget(back)
        root.addLayout(buttons)
        root.addWidget(QLabel("آخر الحركات النقدية"))
        root.addWidget(self.movements_table, 1)

    def refresh(self):
        session = get_session()
        try:
            cashboxes = session.scalars(select(Cashbox).order_by(Cashbox.name)).all()
            self.cashboxes_table.setRowCount(0)
            service = CashboxService(session)
            for cashbox in cashboxes:
                row = self.cashboxes_table.rowCount()
                self.cashboxes_table.insertRow(row)
                values = [cashbox.code, cashbox.name, cashbox.account_type, cashbox.currency, f"{service.get_balance(cashbox.id):,.2f}"]
                for col, value in enumerate(values):
                    self.cashboxes_table.setItem(row, col, QTableWidgetItem(str(value)))
                self.cashboxes_table.item(row, 0).setData(Qt.UserRole, cashbox.id)

            self.source.clear()
            self.target.clear()
            for cashbox in cashboxes:
                label = f"{cashbox.name} ({cashbox.currency})"
                self.source.addItem(label, cashbox.id)
                self.target.addItem(label, cashbox.id)

            self.movements_table.setRowCount(0)
            stmt = select(CashboxMovement, Cashbox).join(Cashbox, Cashbox.id == CashboxMovement.cashbox_id).order_by(CashboxMovement.id.desc()).limit(100)
            for movement, cashbox in session.execute(stmt).all():
                row = self.movements_table.rowCount()
                self.movements_table.insertRow(row)
                values = [movement.business_date, cashbox.name, movement.movement_type, "داخل" if movement.direction == "IN" else "خارج", f"{movement.amount:,.2f}", movement.reference_type or ""]
                for col, value in enumerate(values):
                    self.movements_table.setItem(row, col, QTableWidgetItem(str(value)))

            if self.selected_cashbox_id:
                cashbox = session.get(Cashbox, self.selected_cashbox_id)
                self.balance_label.setText(f"{service.get_balance(self.selected_cashbox_id):,.2f}" if cashbox else "0.00")
        finally:
            session.close()

    def select_cashbox(self, row, _column):
        item = self.cashboxes_table.item(row, 0)
        self.selected_cashbox_id = item.data(Qt.UserRole) if item else None
        if self.selected_cashbox_id:
            index = self.source.findData(self.selected_cashbox_id)
            if index >= 0:
                self.source.setCurrentIndex(index)
            session = get_session()
            try:
                self.balance_label.setText(f"{CashboxService(session).get_balance(self.selected_cashbox_id):,.2f}")
            finally:
                session.close()

    def transfer(self):
        source_id = self.source.currentData()
        target_id = self.target.currentData()
        amount = Decimal(str(self.amount.value()))
        if source_id is None or target_id is None:
            QMessageBox.warning(self, "الحسابات", "اختر حساب المصدر وحساب الهدف.")
            return
        if source_id == target_id:
            QMessageBox.warning(self, "حساب غير صحيح", "يجب أن يكون حساب المصدر مختلفًا عن حساب الهدف.")
            return
        if amount <= 0:
            QMessageBox.warning(self, "مبلغ غير صحيح", "أدخل مبلغ التحويل.")
            return
        session = get_session()
        try:
            CashboxService(session).transfer(
                source_cashbox_id=source_id,
                target_cashbox_id=target_id,
                amount=amount,
                business_date=date.today().isoformat(),
                idempotency_key=str(uuid4()),
            )
            session.commit()
            self.amount.setValue(0)
            self.refresh()
            QMessageBox.information(self, "تم التحويل", "تم تسجيل التحويل بين الحسابين بنجاح.")
        except Exception as exc:
            session.rollback()
            QMessageBox.critical(self, "تعذر التحويل", str(exc))
        finally:
            session.close()
