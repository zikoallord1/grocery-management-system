from datetime import date
from decimal import Decimal
from uuid import uuid4

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPageSize, QTextDocument
from PySide6.QtPrintSupport import QPrintPreviewDialog, QPrinter
from PySide6.QtWidgets import (
    QComboBox, QDoubleSpinBox, QFormLayout, QFrame, QGridLayout,
    QHBoxLayout, QLabel, QMessageBox, QPushButton, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget, QLineEdit,
)
from sqlalchemy import select

from backend.app.core.database import get_session
from backend.app.core.models import Customer, Product, Sale, SaleItem, StockLocation
from backend.app.modules.finance.models import PaymentMethod
from backend.app.modules.sales.service import SaleService


class SalesPage(QWidget):
    back_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self.product = QComboBox()
        self.quantity = QDoubleSpinBox()
        self.quantity.setRange(0.001, 999999999)
        self.quantity.setDecimals(3)
        self.quantity.setValue(1)
        self.price = QDoubleSpinBox()
        self.price.setRange(0, 999999999)
        self.price.setDecimals(2)
        self.payment_method = QComboBox()
        self.payment = QDoubleSpinBox()
        self.payment.setRange(0, 999999999)
        self.payment.setDecimals(2)
        self.customer = QComboBox()
        self.customer.addItem("بدون عميل / بيع نقدي", None)
        self.total_label = QLabel("0.00")
        self.paid_label = QLabel("0.00")
        self.remaining_label = QLabel("0.00")
        self.stock_label = QLabel("-")
        self.location_id = None
        self.lines = []
        self.payment_lines = []
        self.lines_table = QTableWidget(0, 6)
        self.lines_table.setHorizontalHeaderLabels(["#", "الصنف", "الباركود", "الكمية", "سعر الوحدة", "الإجمالي"])
        self.lines_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.lines_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.payments_table = QTableWidget(0, 2)
        self.payments_table.setHorizontalHeaderLabels(["وسيلة الدفع", "المبلغ"])
        self.payments_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.history = QTableWidget(0, 7)
        self.history.setHorizontalHeaderLabels(["التاريخ", "رقم الفاتورة", "العميل", "الصنف", "الكمية", "الإجمالي", "الحالة"])
        self.history.setEditTriggers(QTableWidget.NoEditTriggers)
        self._build()
        self.refresh_data()

    def _panel(self, title):
        panel = QFrame()
        panel.setObjectName("referencePanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        heading = QLabel(title)
        heading.setObjectName("referencePanelTitle")
        layout.addWidget(heading)
        return panel, layout

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        toolbar = QFrame()
        toolbar.setObjectName("referenceToolbar")
        tb = QHBoxLayout(toolbar)
        tb.setContentsMargins(12, 8, 12, 8)
        tb.setSpacing(8)
        title = QLabel("فاتورة بيع جديدة")
        title.setObjectName("pageTitle")
        tb.addWidget(title, 1)
        refresh = QPushButton("↻ تحديث")
        refresh.setObjectName("secondaryButton")
        refresh.clicked.connect(self.refresh_data)
        tb.addWidget(refresh)
        preview = QPushButton("👁 معاينة")
        preview.setObjectName("secondaryButton")
        preview.clicked.connect(self.preview_selected)
        tb.addWidget(preview)
        root.addWidget(toolbar)

        workspace = QHBoxLayout()
        workspace.setSpacing(8)

        # Left side: invoice total, payment details and related controls.
        left_panel, left = self._panel("إجمالي الفاتورة")
        total_grid = QGridLayout()
        total_grid.setHorizontalSpacing(8)
        total_grid.setVerticalSpacing(6)
        total_grid.addWidget(QLabel("إجمالي الأصناف"), 0, 1)
        total_grid.addWidget(self.total_label, 0, 0)
        total_grid.addWidget(QLabel("الخصم الكلي"), 1, 1)
        discount_label = QLabel("0.00")
        discount_label.setObjectName("summaryValue")
        total_grid.addWidget(discount_label, 1, 0)
        total_grid.addWidget(QLabel("الضريبة"), 2, 1)
        tax_label = QLabel("0.00")
        tax_label.setObjectName("summaryValue")
        total_grid.addWidget(tax_label, 2, 0)
        total_grid.addWidget(QLabel("الإجمالي الكلي"), 3, 1)
        total_grid.addWidget(self.total_label, 3, 0)
        left.addLayout(total_grid)

        payment_title = QLabel("تفاصيل الدفع")
        payment_title.setObjectName("sectionTitle")
        left.addWidget(payment_title)

        left.addWidget(QLabel("طريقة الدفع"))
        left.addWidget(self.payment_method)
        left.addWidget(QLabel("المبلغ"))
        left.addWidget(self.payment)
        add_payment = QPushButton("＋ إضافة دفعة")
        add_payment.setObjectName("secondaryButton")
        add_payment.clicked.connect(self.add_payment)
        left.addWidget(add_payment)
        left.addWidget(self.payments_table)

        paid_box = QFrame()
        paid_box.setObjectName("totalsPanel")
        paid_layout = QGridLayout(paid_box)
        paid_layout.setContentsMargins(8, 6, 8, 6)
        paid_layout.addWidget(QLabel("المدفوع"), 0, 1)
        paid_layout.addWidget(self.paid_label, 0, 0)
        paid_layout.addWidget(QLabel("المتبقي"), 1, 1)
        paid_layout.addWidget(self.remaining_label, 1, 0)
        left.addWidget(paid_box)

        left.addWidget(QLabel("ملاحظات الفاتورة"))
        self.invoice_notes = QLineEdit()
        self.invoice_notes.setPlaceholderText("أضف ملاحظات إن وجدت...")
        left.addWidget(self.invoice_notes)

        self.auto_print = QPushButton("🖨 طباعة الفاتورة تلقائياً")
        self.auto_print.setCheckable(True)
        self.auto_print.setChecked(False)
        self.auto_print.setObjectName("secondaryButton")
        left.addWidget(self.auto_print)

        complete = QPushButton("✓ إتمام البيع")
        complete.setObjectName("successButton")
        complete.setMinimumHeight(52)
        complete.clicked.connect(self.create_sale)
        left.addWidget(complete)
        left.addStretch(1)
        workspace.addWidget(left_panel, 1)

        # Center: invoice details only; no recent-products side tab.
        center_panel, center = self._panel("تفاصيل الفاتورة")
        header_form = QGridLayout()
        header_form.setHorizontalSpacing(8)
        header_form.setVerticalSpacing(7)
        header_form.addWidget(QLabel("العميل"), 0, 3)
        header_form.addWidget(self.customer, 0, 2)
        header_form.addWidget(QLabel("التاريخ"), 0, 1)
        date_edit = QLineEdit(date.today().isoformat())
        date_edit.setReadOnly(True)
        header_form.addWidget(date_edit, 0, 0)
        header_form.addWidget(QLabel("رقم الفاتورة"), 1, 3)
        invoice_no = QLabel("سيُنشأ تلقائياً عند الحفظ")
        invoice_no.setObjectName("summaryValue")
        header_form.addWidget(invoice_no, 1, 2)
        header_form.addWidget(QLabel("الصنف / الباركود"), 1, 1)
        header_form.addWidget(self.product, 1, 0)
        center.addLayout(header_form)

        barcode = QLineEdit()
        barcode.setPlaceholderText("امسح الباركود أو اكتب اسم الصنف...")
        barcode.setObjectName("barcodeSearch")
        center.addWidget(barcode)

        line_buttons = QHBoxLayout()
        for label, slot, obj in [
            ("＋ إضافة صنف", self.add_line, "primaryButton"),
            ("تعديل", self.product_changed, "secondaryButton"),
            ("مسح", self.clear_lines, "secondaryButton"),
            ("حذف المحدد", self.remove_selected_line, "dangerButton"),
        ]:
            button = QPushButton(label)
            button.setObjectName(obj)
            button.clicked.connect(slot)
            line_buttons.addWidget(button)
        center.addLayout(line_buttons)
        center.addWidget(self.lines_table, 1)

        item_box = QFrame()
        item_box.setObjectName("itemDetailsPanel")
        item_layout = QGridLayout(item_box)
        item_layout.setContentsMargins(8, 7, 8, 7)
        item_layout.addWidget(QLabel("الكمية"), 0, 3)
        item_layout.addWidget(self.quantity, 0, 2)
        item_layout.addWidget(QLabel("سعر الوحدة"), 0, 1)
        item_layout.addWidget(self.price, 0, 0)
        item_layout.addWidget(QLabel("المخزون المتاح"), 1, 3)
        item_layout.addWidget(self.stock_label, 1, 2)
        center.addWidget(item_box)
        workspace.addWidget(center_panel, 3)

        root.addLayout(workspace, 1)

        bottom = QHBoxLayout()
        bottom.setSpacing(8)
        for label, slot, name in [
            ("حفظ الفاتورة", self.create_sale, "primaryButton"),
            ("معاينة / طباعة", self.preview_selected, "secondaryButton"),
            ("إخلاء الفاتورة", self.clear_lines, "dangerButton"),
        ]:
            b = QPushButton(label)
            b.setObjectName(name)
            b.clicked.connect(slot)
            bottom.addWidget(b)
        root.addLayout(bottom)

        self.product.currentIndexChanged.connect(self.product_changed)
        self.quantity.valueChanged.connect(self.product_changed)
        self.price.valueChanged.connect(self.recalculate)
        self.payment.valueChanged.connect(self.recalculate)

    def _filter_history(self, value):
        value = value.strip().lower()
        for row in range(self.history.rowCount()):
            visible = not value or any(value in (self.history.item(row, c).text().lower() if self.history.item(row, c) else "") for c in range(self.history.columnCount()))
            self.history.setRowHidden(row, not visible)

    def refresh_data(self):
        session = get_session()
        try:
            current_product = self.product.currentData()
            self.product.blockSignals(True)
            self.product.clear()
            for product in session.scalars(select(Product).where(Product.is_active.is_(True)).order_by(Product.name)).all():
                self.product.addItem(f"{product.name} — {product.sku}", product.id)
            if current_product is not None:
                idx = self.product.findData(current_product)
                if idx >= 0:
                    self.product.setCurrentIndex(idx)
            self.product.blockSignals(False)
            current_customer = self.customer.currentData()
            self.customer.blockSignals(True)
            self.customer.clear()
            self.customer.addItem("بدون عميل / بيع نقدي", None)
            for customer in session.scalars(select(Customer).where(Customer.is_active.is_(True)).order_by(Customer.name)).all():
                self.customer.addItem(f"{customer.name} — {customer.code}", customer.id)
            if current_customer is not None:
                idx = self.customer.findData(current_customer)
                if idx >= 0:
                    self.customer.setCurrentIndex(idx)
            self.customer.blockSignals(False)
            current_method = self.payment_method.currentData()
            self.payment_method.blockSignals(True)
            self.payment_method.clear()
            for method in session.scalars(select(PaymentMethod).where(PaymentMethod.is_active.is_(True)).order_by(PaymentMethod.code)).all():
                self.payment_method.addItem(f"{method.code} — {method.name}", method.code)
            if current_method is not None:
                idx = self.payment_method.findData(current_method)
                if idx >= 0:
                    self.payment_method.setCurrentIndex(idx)
            self.payment_method.blockSignals(False)
            location = session.scalar(select(StockLocation).where(StockLocation.is_active.is_(True)).order_by(StockLocation.id).limit(1))
            self.location_id = location.id if location else None
            rows = session.execute(select(Sale, Customer, Product, SaleItem.quantity).outerjoin(Customer, Customer.id == Sale.customer_id).join(SaleItem, SaleItem.sale_id == Sale.id).join(Product, Product.id == SaleItem.product_id).order_by(Sale.id.desc()).limit(100)).all()
            self.history.setRowCount(len(rows))
            for r, (sale, customer, product, quantity) in enumerate(rows):
                values = [sale.business_date, sale.document_no, customer.name if customer else "نقدي", product.name, f"{quantity:,.3f}", f"{sale.total:,.2f}", sale.payment_status]
                for c, value in enumerate(values):
                    self.history.setItem(r, c, QTableWidgetItem(str(value)))
            self.history.resizeColumnsToContents()
            self.product_changed()
        finally:
            session.close()

    def product_changed(self):
        session = get_session()
        try:
            product = session.get(Product, self.product.currentData()) if self.product.currentData() else None
            if product is None:
                self.price.setValue(0)
                self.stock_label.setText("لا يوجد")
                self.recalculate()
                return
            self.price.setValue(float(product.sale_price))
            if self.location_id is not None:
                from backend.app.modules.inventory.service import InventoryService
                balance = InventoryService(session).get_balance(product.id, self.location_id)
                self.stock_label.setText(f"{balance:,.3f}")
            else:
                self.stock_label.setText("لم يتم إعداد مخزن")
            self.recalculate()
        finally:
            session.close()

    def _payments_total(self):
        return sum((line["amount"] for line in self.payment_lines), Decimal("0"))

    def recalculate(self):
        total = sum((line["total"] for line in self.lines), Decimal("0"))
        paid = self._payments_total()
        if not self.payment_lines and self.lines and self.payment.value() == 0:
            self.payment.setValue(float(total))
        current = Decimal(str(self.payment.value()))
        display_paid = paid + current
        self.total_label.setText(f"{total:,.2f}")
        self.paid_label.setText(f"{display_paid:,.2f}")
        self.remaining_label.setText(f"{max(total - display_paid, Decimal('0')):,.2f}")

    def add_line(self):
        product_id = self.product.currentData()
        if product_id is None:
            QMessageBox.warning(self, "بيانات ناقصة", "أضف صنفًا أولًا من شاشة المخزون.")
            return
        if self.location_id is None:
            QMessageBox.warning(self, "المخزون غير مهيأ", "لا يوجد موقع مخزون نشط.")
            return
        quantity = Decimal(str(self.quantity.value()))
        price = Decimal(str(self.price.value()))
        if quantity <= 0:
            QMessageBox.warning(self, "كمية غير صحيحة", "الكمية يجب أن تكون أكبر من صفر.")
            return
        if price < 0:
            QMessageBox.warning(self, "سعر غير صحيح", "السعر لا يمكن أن يكون سالبًا.")
            return
        session = get_session()
        try:
            product = session.get(Product, product_id)
            from backend.app.modules.inventory.service import InventoryService
            stock = InventoryService(session).get_balance(product_id, self.location_id)
        finally:
            session.close()
        if quantity > Decimal(str(stock)):
            QMessageBox.warning(self, "المخزون غير كافٍ", f"المتاح: {stock:,.3f}")
            return
        existing = next((line for line in self.lines if line["product_id"] == product_id), None)
        if existing:
            new_qty = existing["quantity"] + quantity
            if new_qty > Decimal(str(stock)):
                QMessageBox.warning(self, "المخزون غير كافٍ", f"المتاح: {stock:,.3f}")
                return
            existing["quantity"] = new_qty
            existing["unit_price"] = price
            existing["total"] = new_qty * price
        else:
            self.lines.append({"product_id": product_id, "name": product.name, "quantity": quantity, "unit_price": price, "discount": Decimal("0"), "total": quantity * price, "stock": Decimal(str(stock))})
        self.refresh_lines_table()
        self.quantity.setValue(1)

    def refresh_lines_table(self):
        self.lines_table.setRowCount(len(self.lines))
        for row, line in enumerate(self.lines):
            values = [row + 1, line["name"], "", f"{line['quantity']:,.3f}", f"{line['unit_price']:,.2f}", f"{line['total']:,.2f}"]
            for col, value in enumerate(values):
                self.lines_table.setItem(row, col, QTableWidgetItem(str(value)))
        self.lines_table.resizeColumnsToContents()
        self.recalculate()

    def remove_selected_line(self):
        row = self.lines_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "اختيار السطر", "حدد صنفًا من الفاتورة أولًا.")
            return
        self.lines.pop(row)
        self.refresh_lines_table()

    def clear_lines(self):
        self.lines.clear()
        self.refresh_lines_table()
        self.clear_payments()

    def add_payment(self):
        method = self.payment_method.currentData()
        amount = Decimal(str(self.payment.value())).quantize(Decimal("0.01"))
        total = sum((line["total"] for line in self.lines), Decimal("0"))
        if not self.lines:
            QMessageBox.warning(self, "الفاتورة فارغة", "أضف أصناف الفاتورة أولًا.")
            return
        if not method or amount <= 0:
            QMessageBox.warning(self, "دفعة غير صحيحة", "اختر وسيلة دفع وأدخل مبلغًا أكبر من صفر.")
            return
        if self._payments_total() + amount > total:
            QMessageBox.warning(self, "مبلغ زائد", "مجموع الدفعات لا يمكن أن يتجاوز إجمالي الفاتورة.")
            return
        self.payment_lines.append({"payment_method": method, "amount": amount})
        self.refresh_payments_table()
        self.payment.setValue(0)

    def refresh_payments_table(self):
        self.payments_table.setRowCount(len(self.payment_lines))
        session = get_session()
        try:
            names = {m.code: m.name for m in session.scalars(select(PaymentMethod)).all()}
        finally:
            session.close()
        for row, line in enumerate(self.payment_lines):
            self.payments_table.setItem(row, 0, QTableWidgetItem(names.get(line["payment_method"], line["payment_method"])))
            self.payments_table.setItem(row, 1, QTableWidgetItem(f"{line['amount']:,.2f}"))
        self.payments_table.resizeColumnsToContents()
        self.recalculate()

    def remove_payment(self):
        row = self.payments_table.currentRow()
        if row >= 0:
            self.payment_lines.pop(row)
            self.refresh_payments_table()

    def clear_payments(self):
        self.payment_lines.clear()
        self.payments_table.setRowCount(0)
        self.payment.setValue(0)
        self.recalculate()

    def create_sale(self):
        if not self.lines:
            QMessageBox.warning(self, "الفاتورة فارغة", "أضف صنفًا واحدًا على الأقل إلى الفاتورة.")
            return
        if self.location_id is None:
            QMessageBox.warning(self, "المخزون غير مهيأ", "لا يوجد موقع مخزون نشط.")
            return
        total = sum((line["total"] for line in self.lines), Decimal("0"))
        payments = list(self.payment_lines)
        current_amount = Decimal(str(self.payment.value())).quantize(Decimal("0.01"))
        if current_amount > 0:
            method = self.payment_method.currentData() or "CASH"
            if self._payments_total() + current_amount > total:
                QMessageBox.warning(self, "مبلغ غير صحيح", "مجموع الدفعات لا يمكن أن يتجاوز إجمالي الفاتورة.")
                return
            payments.append({"payment_method": method, "amount": current_amount})
        paid = sum((p["amount"] for p in payments), Decimal("0"))
        if paid > total:
            QMessageBox.warning(self, "مبلغ غير صحيح", "المبلغ المدفوع لا يمكن أن يتجاوز إجمالي الفاتورة.")
            return
        if paid < total and self.customer.currentData() is None:
            QMessageBox.warning(self, "العميل مطلوب", "البيع الآجل أو الجزئي يتطلب اختيار عميل.")
            return
        session = get_session()
        try:
            sale = SaleService(session).create_sale(
                document_no=f"S-{date.today().strftime('%Y%m%d')}-{uuid4().hex[:8].upper()}",
                business_date=date.today().isoformat(),
                customer_id=self.customer.currentData(),
                items=[{"product_id": line["product_id"], "stock_location_id": self.location_id, "quantity": str(line["quantity"]), "unit_price": str(line["unit_price"]), "discount": str(line["discount"])} for line in self.lines],
                payments=[{"payment_method": p["payment_method"], "amount": str(p["amount"]), "currency": "BASE"} for p in payments],
                idempotency_key=str(uuid4()),
            )
            session.commit()
            QMessageBox.information(self, "تم الحفظ", f"تم تأكيد فاتورة البيع رقم {sale.document_no} بإجمالي {sale.total:,.2f}.")
            self.clear_lines()
            self.refresh_data()
        except Exception as exc:
            session.rollback()
            QMessageBox.critical(self, "تعذر حفظ الفاتورة", str(exc))
        finally:
            session.close()

    def preview_selected(self):
        row = self.history.currentRow()
        if row < 0:
            QMessageBox.information(self, "اختيار الفاتورة", "حدد فاتورة من سجل المبيعات أولًا.")
            return
        document_no = self.history.item(row, 1).text()
        session = get_session()
        try:
            sale = session.scalar(select(Sale).where(Sale.document_no == document_no))
            if sale is None:
                QMessageBox.warning(self, "الفاتورة غير موجودة", "تعذر العثور على الفاتورة المحددة.")
                return
            customer = session.get(Customer, sale.customer_id) if sale.customer_id else None
            lines = session.execute(select(Product.name, SaleItem.quantity, SaleItem.unit_price, SaleItem.line_total).join(Product, Product.id == SaleItem.product_id).where(SaleItem.sale_id == sale.id)).all()
            rows = [(name, f"{quantity:,.3f}", unit_price, line_total) for name, quantity, unit_price, line_total in lines]
            printer = QPrinter(QPrinter.HighResolution)
            printer.setPageSize(QPageSize(QPageSize.A4))
            preview = QPrintPreviewDialog(printer, self)
            preview.setWindowTitle(f"معاينة فاتورة البيع {sale.document_no}")
            def render(target):
                document = QTextDocument()
                html = f"<html><head><meta charset='utf-8'><style>body{{font-family:Arial;direction:rtl}}h1{{text-align:center}}table{{width:100%;border-collapse:collapse}}th,td{{border:1px solid #777;padding:7px;text-align:right}}.brand{{text-align:center;margin-top:30px;font-size:11px}}</style></head><body><h1>فاتورة بيع</h1><p><b>رقم الفاتورة:</b> {sale.document_no}<br><b>التاريخ:</b> {sale.business_date}<br><b>العميل:</b> {customer.name if customer else 'نقدي'}</p><table><tr><th>الصنف</th><th>الكمية</th><th>السعر</th><th>الإجمالي</th></tr>{''.join(f'<tr><td>{n}</td><td>{q}</td><td>{p:,.2f}</td><td>{t:,.2f}</td></tr>' for n,q,p,t in rows)}</table><p><b>الإجمالي:</b> {sale.total:,.2f}<br><b>المدفوع:</b> {sale.paid_amount:,.2f}<br><b>المتبقي:</b> {sale.credit_amount:,.2f}</p><div class='brand'>نظام إدارة البقالات<br>تصميم وتنفيذ المهندس / زكريا الحاج<br>لطلب البرنامج او تقديم المساعدة او طلب برامج اخرى التواصل على الرقم 772233564</div></body></html>"
                document.setHtml(html)
                document.print_(target)
            preview.paintRequested.connect(render)
            preview.resize(900, 700)
            preview.exec()
        finally:
            session.close()
