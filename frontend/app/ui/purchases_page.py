from datetime import date
from decimal import Decimal
from uuid import uuid4

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy import select

from backend.app.core.database import get_session
from backend.app.core.models import Product, Purchase, PurchaseItem, StockLocation, Supplier
from backend.app.modules.finance.models import PaymentMethod
from backend.app.modules.purchases.service import PurchaseService
from frontend.app.ui.invoice_preview import show_invoice_preview


class PurchasesPage(QWidget):
    back_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self.product = QComboBox()
        self.supplier = QComboBox()
        self.location = QComboBox()
        self.payment_method = QComboBox()
        self.quantity = QDoubleSpinBox(); self.quantity.setDecimals(3); self.quantity.setMinimum(0.001); self.quantity.setMaximum(999999999); self.quantity.setValue(1)
        self.unit_cost = QDoubleSpinBox(); self.unit_cost.setDecimals(2); self.unit_cost.setMaximum(999999999)
        self.payment = QDoubleSpinBox(); self.payment.setDecimals(2); self.payment.setMaximum(999999999)
        self.document_no = QLabel()
        self.total = QLabel("0.00")
        self.lines = QTableWidget(0, 5)
        self.lines.setHorizontalHeaderLabels(["الصنف", "الكمية", "تكلفة الوحدة", "الإجمالي", "المخزن"])
        self.lines.setEditTriggers(QTableWidget.NoEditTriggers)
        self.history = QTableWidget(0, 7)
        self.history.setHorizontalHeaderLabels(["التاريخ", "رقم الفاتورة", "المورد", "الصنف", "الكمية", "الإجمالي", "الحالة"])
        self.history.setEditTriggers(QTableWidget.NoEditTriggers)
        self._build()
        self.refresh()

    def _build(self):
        root = QVBoxLayout(self)
        title = QLabel("المشتريات"); title.setObjectName("pageTitle"); root.addWidget(title)
        root.addWidget(QLabel("أنشئ فاتورة شراء متعددة الأصناف، وسيقوم النظام بربطها تلقائيًا بالمخزون والمورد والصندوق."))

        form = QFormLayout()
        form.addRow("رقم الفاتورة", self.document_no)
        form.addRow("المورد", self.supplier)
        form.addRow("الصنف", self.product)
        form.addRow("المخزن", self.location)
        form.addRow("الكمية", self.quantity)
        form.addRow("تكلفة الوحدة", self.unit_cost)
        form.addRow("وسيلة الدفع", self.payment_method)
        form.addRow("المدفوع الآن", self.payment)
        root.addLayout(form)

        line_buttons = QHBoxLayout()
        add_line = QPushButton("إضافة الصنف إلى الفاتورة"); add_line.setObjectName("primaryButton"); add_line.clicked.connect(self.add_line)
        remove_line = QPushButton("حذف السطر المحدد"); remove_line.clicked.connect(self.remove_line)
        clear_lines = QPushButton("تفريغ الفاتورة"); clear_lines.clicked.connect(self.clear_lines)
        line_buttons.addWidget(add_line); line_buttons.addWidget(remove_line); line_buttons.addWidget(clear_lines); line_buttons.addStretch()
        root.addLayout(line_buttons)
        root.addWidget(QLabel("أصناف الفاتورة الحالية")); root.addWidget(self.lines)

        buttons = QHBoxLayout()
        save = QPushButton("حفظ وتأكيد فاتورة الشراء"); save.setObjectName("primaryButton"); save.clicked.connect(self.save_purchase)
        preview = QPushButton("معاينة/طباعة الفاتورة المحددة"); preview.clicked.connect(self.preview_selected)
        refresh = QPushButton("تحديث"); refresh.clicked.connect(self.refresh)
        back = QPushButton("العودة إلى الرئيسية"); back.setObjectName("secondaryButton"); back.clicked.connect(self.back_requested.emit)
        buttons.addWidget(save); buttons.addWidget(preview); buttons.addWidget(refresh); buttons.addStretch(); buttons.addWidget(back)
        root.addLayout(buttons)
        root.addWidget(QLabel("آخر فواتير الشراء")); root.addWidget(self.history, 1)

        self.product.currentIndexChanged.connect(self._product_changed)
        self.quantity.valueChanged.connect(self._update_total)
        self.unit_cost.valueChanged.connect(self._update_total)

    def _product_changed(self):
        session = get_session()
        try:
            product = session.get(Product, self.product.currentData()) if self.product.currentData() else None
            if product:
                self.unit_cost.setValue(float(product.purchase_price or 0))
        finally:
            session.close()
        self._update_total()

    def _update_total(self):
        self.total.setText(f"{self._invoice_total() + Decimal(str(self.quantity.value() * self.unit_cost.value())).quantize(Decimal('0.01')):,.2f}" if self.lines.rowCount() else f"{self.quantity.value() * self.unit_cost.value():,.2f}")

    def _invoice_total(self):
        total = Decimal("0")
        for row in range(self.lines.rowCount()):
            total += Decimal(self.lines.item(row, 3).data(Qt.UserRole) or "0")
        return total

    def add_line(self):
        product_id = self.product.currentData(); location_id = self.location.currentData()
        if product_id is None or location_id is None:
            QMessageBox.warning(self, "بيانات ناقصة", "اختر الصنف والمخزن أولًا."); return
        quantity = Decimal(str(self.quantity.value())); unit_cost = Decimal(str(self.unit_cost.value())).quantize(Decimal("0.01"))
        if quantity <= 0 or unit_cost < 0:
            QMessageBox.warning(self, "قيمة غير صحيحة", "تحقق من الكمية والتكلفة."); return
        session = get_session()
        try:
            product = session.get(Product, product_id); location = session.get(StockLocation, location_id)
            if product is None or location is None: return
            for row in range(self.lines.rowCount()):
                if self.lines.item(row, 0).data(Qt.UserRole) == product_id and self.lines.item(row, 4).data(Qt.UserRole) == location_id:
                    old_qty = Decimal(self.lines.item(row, 1).data(Qt.UserRole))
                    new_qty = old_qty + quantity
                    self.lines.item(row, 1).setText(f"{new_qty:,.3f}"); self.lines.item(row, 1).setData(Qt.UserRole, str(new_qty))
                    self.lines.item(row, 2).setText(f"{unit_cost:,.2f}"); self.lines.item(row, 2).setData(Qt.UserRole, str(unit_cost))
                    line_total = new_qty * unit_cost
                    self.lines.item(row, 3).setText(f"{line_total:,.2f}"); self.lines.item(row, 3).setData(Qt.UserRole, str(line_total))
                    self._update_total(); return
            row = self.lines.rowCount(); self.lines.insertRow(row)
            values = [product.name, f"{quantity:,.3f}", f"{unit_cost:,.2f}", f"{quantity * unit_cost:,.2f}", location.name]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value); self.lines.setItem(row, col, item)
            self.lines.item(row, 0).setData(Qt.UserRole, product_id)
            self.lines.item(row, 1).setData(Qt.UserRole, str(quantity))
            self.lines.item(row, 2).setData(Qt.UserRole, str(unit_cost))
            self.lines.item(row, 3).setData(Qt.UserRole, str(quantity * unit_cost))
            self.lines.item(row, 4).setData(Qt.UserRole, location_id)
            self.lines.resizeColumnsToContents(); self._update_total()
        finally:
            session.close()

    def remove_line(self):
        row = self.lines.currentRow()
        if row >= 0:
            self.lines.removeRow(row); self._update_total()

    def clear_lines(self):
        self.lines.setRowCount(0); self._update_total()

    def _build_items(self):
        items = []
        for row in range(self.lines.rowCount()):
            items.append({
                "product_id": self.lines.item(row, 0).data(Qt.UserRole),
                "quantity": Decimal(self.lines.item(row, 1).data(Qt.UserRole)),
                "unit_cost": Decimal(self.lines.item(row, 2).data(Qt.UserRole)),
                "discount": Decimal("0"),
                "stock_location_id": self.lines.item(row, 4).data(Qt.UserRole),
            })
        return items

    def save_purchase(self):
        if self.lines.rowCount() == 0:
            QMessageBox.warning(self, "الفاتورة فارغة", "أضف صنفًا واحدًا على الأقل إلى الفاتورة."); return
        supplier_id = self.supplier.currentData(); items = self._build_items()
        total = self._invoice_total().quantize(Decimal("0.01")); paid = Decimal(str(self.payment.value())).quantize(Decimal("0.01"))
        if total <= 0: QMessageBox.warning(self, "قيمة غير صحيحة", "يجب أن تكون قيمة الفاتورة أكبر من صفر."); return
        if paid > total: QMessageBox.warning(self, "مبلغ غير صحيح", "المدفوع لا يمكن أن يتجاوز إجمالي الفاتورة."); return
        if paid < total and supplier_id is None: QMessageBox.warning(self, "المورد مطلوب", "الفاتورة الآجلة أو الجزئية تحتاج إلى مورد."); return
        method = self.payment_method.currentData()
        if paid > 0 and method is None: QMessageBox.warning(self, "وسيلة الدفع مطلوبة", "اختر وسيلة الدفع للمبلغ المدفوع."); return
        session = get_session()
        try:
            document_no = f"P-{date.today().strftime('%Y%m%d')}-{uuid4().hex[:8].upper()}"
            PurchaseService(session).create_purchase(
                document_no=document_no,
                business_date=date.today().isoformat(),
                supplier_id=supplier_id,
                items=items,
                payments=([{"payment_method": method, "amount": paid, "currency": "BASE"}] if paid > 0 else []),
                idempotency_key=str(uuid4()),
            )
            session.commit(); QMessageBox.information(self, "تم الحفظ", f"تم تأكيد فاتورة الشراء {document_no} بإجمالي {total:,.2f} وربطها بالمخزون.")
            self.clear_lines(); self.payment.setValue(0); self.refresh()
        except Exception as exc:
            session.rollback(); QMessageBox.critical(self, "تعذر الحفظ", str(exc))
        finally:
            session.close()

    def _load_selectors(self, session):
        self.product.clear()
        for p in session.scalars(select(Product).where(Product.is_active.is_(True)).order_by(Product.name)).all(): self.product.addItem(f"{p.sku} — {p.name}", p.id)
        self.supplier.clear(); self.supplier.addItem("بدون مورد محدد / شراء نقدي", None)
        for s in session.scalars(select(Supplier).where(Supplier.is_active.is_(True)).order_by(Supplier.name)).all(): self.supplier.addItem(f"{s.code} — {s.name}", s.id)
        self.location.clear()
        for location in session.scalars(select(StockLocation).where(StockLocation.is_active.is_(True)).order_by(StockLocation.name)).all(): self.location.addItem(f"{location.code} — {location.name}", location.id)
        self.payment_method.clear(); self.payment_method.addItem("بدون دفع / آجل", None)
        for method in session.scalars(select(PaymentMethod).where(PaymentMethod.is_active.is_(True)).order_by(PaymentMethod.code)).all(): self.payment_method.addItem(f"{method.code} — {method.name}", method.code)

    def refresh(self):
        session = get_session()
        try:
            self._load_selectors(session)
            rows = session.execute(select(Purchase, Supplier, Product, PurchaseItem.quantity).outerjoin(Supplier, Supplier.id == Purchase.supplier_id).join(PurchaseItem, PurchaseItem.purchase_id == Purchase.id).join(Product, Product.id == PurchaseItem.product_id).order_by(Purchase.id.desc()).limit(100)).all()
            self.history.setRowCount(len(rows))
            for r, (purchase, supplier, product, quantity) in enumerate(rows):
                for c, value in enumerate([purchase.business_date, purchase.document_no, supplier.name if supplier else "نقدي", product.name, f"{quantity:,.3f}", f"{purchase.total:,.2f}", purchase.payment_status]): self.history.setItem(r, c, QTableWidgetItem(str(value)))
            self.history.resizeColumnsToContents()
        finally:
            session.close()
        self.document_no.setText("سيُولد تلقائيًا عند الحفظ")
        self._update_total()

    def preview_selected(self):
        row = self.history.currentRow()
        if row < 0:
            QMessageBox.information(self, "اختيار الفاتورة", "حدد فاتورة من سجل المشتريات أولًا."); return
        document_no = self.history.item(row, 1).text(); session = get_session()
        try:
            purchase = session.scalar(select(Purchase).where(Purchase.document_no == document_no))
            if purchase is None:
                QMessageBox.warning(self, "الفاتورة غير موجودة", "تعذر العثور على الفاتورة المحددة."); return
            supplier = session.get(Supplier, purchase.supplier_id) if purchase.supplier_id else None
            lines = session.execute(select(Product.name, PurchaseItem.quantity, PurchaseItem.unit_cost, PurchaseItem.line_total).join(Product, Product.id == PurchaseItem.product_id).where(PurchaseItem.purchase_id == purchase.id)).all()
            rows = [(name, f"{quantity:,.3f}", unit_cost, line_total) for name, quantity, unit_cost, line_total in lines]
            show_invoice_preview(self, title="فاتورة شراء", document_no=purchase.document_no, business_date=purchase.business_date, party_label="المورد", party_name=supplier.name if supplier else "شراء نقدي", rows=rows, total=purchase.total, paid=purchase.paid_amount, credit=purchase.credit_amount, kind="الشراء")
        finally:
            session.close()
