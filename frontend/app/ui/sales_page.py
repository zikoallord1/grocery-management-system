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
    QVBoxLayout,
    QWidget,
)
from sqlalchemy import select

from backend.app.core.database import get_session
from backend.app.core.models import Customer, Product, StockLocation
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
        self.payment = QDoubleSpinBox()
        self.payment.setRange(0, 999999999)
        self.payment.setDecimals(2)
        self.customer = QComboBox()
        self.customer.addItem("بدون عميل / بيع نقدي", None)
        self.total_label = QLabel("0.00")
        self.stock_label = QLabel("-")
        self.location_id = None
        self._build()
        self.refresh_data()

    def _build(self):
        root = QVBoxLayout(self)
        title = QLabel("فاتورة بيع جديدة")
        title.setObjectName("pageTitle")
        root.addWidget(title)
        description = QLabel("اختر الصنف والكمية، وسيقوم النظام بربط الفاتورة بالمخزون والصندوق وذمم العميل عند الحاجة.")
        description.setWordWrap(True)
        description.setObjectName("pageDescription")
        root.addWidget(description)

        form = QFormLayout()
        form.addRow("الصنف", self.product)
        form.addRow("الكمية", self.quantity)
        form.addRow("سعر البيع", self.price)
        form.addRow("العميل", self.customer)
        form.addRow("المبلغ المدفوع", self.payment)
        form.addRow("الإجمالي", self.total_label)
        form.addRow("الرصيد المتاح", self.stock_label)
        root.addLayout(form)

        buttons = QHBoxLayout()
        save = QPushButton("حفظ وتأكيد الفاتورة")
        save.setObjectName("primaryButton")
        save.clicked.connect(self.create_sale)
        refresh = QPushButton("تحديث الأصناف")
        refresh.clicked.connect(self.refresh_data)
        back = QPushButton("العودة إلى الرئيسية")
        back.setObjectName("secondaryButton")
        back.clicked.connect(self.back_requested.emit)
        buttons.addWidget(save)
        buttons.addWidget(refresh)
        buttons.addWidget(back)
        root.addLayout(buttons)
        self.product.currentIndexChanged.connect(self.product_changed)
        self.quantity.valueChanged.connect(self.recalculate)
        self.price.valueChanged.connect(self.recalculate)
        self.payment.valueChanged.connect(self.recalculate)
        root.addStretch()

    def refresh_data(self):
        session = get_session()
        try:
            self.product.blockSignals(True)
            self.product.clear()
            products = session.scalars(
                select(Product).where(Product.is_active.is_(True)).order_by(Product.name)
            ).all()
            for product in products:
                self.product.addItem(f"{product.name} — {product.sku}", product.id)
            self.product.blockSignals(False)
            self.customer.blockSignals(True)
            current = self.customer.currentData()
            self.customer.clear()
            self.customer.addItem("بدون عميل / بيع نقدي", None)
            customers = session.scalars(
                select(Customer).where(Customer.is_active.is_(True)).order_by(Customer.name)
            ).all()
            for customer in customers:
                self.customer.addItem(f"{customer.name} — {customer.code}", customer.id)
            if current is not None:
                index = self.customer.findData(current)
                if index >= 0:
                    self.customer.setCurrentIndex(index)
            self.customer.blockSignals(False)
            location = session.scalar(
                select(StockLocation).where(StockLocation.is_active.is_(True)).order_by(StockLocation.id).limit(1)
            )
            self.location_id = location.id if location else None
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

    def recalculate(self):
        total = Decimal(str(self.quantity.value())) * Decimal(str(self.price.value()))
        self.total_label.setText(f"{total:,.2f}")
        if self.payment.value() == 0 and total > 0:
            self.payment.setValue(float(total))

    def create_sale(self):
        if self.product.currentData() is None:
            QMessageBox.warning(self, "بيانات ناقصة", "أضف صنفًا أولًا من شاشة المخزون.")
            return
        if self.location_id is None:
            QMessageBox.warning(self, "المخزون غير مهيأ", "لا يوجد موقع مخزون نشط.")
            return
        total = Decimal(str(self.quantity.value())) * Decimal(str(self.price.value()))
        paid = Decimal(str(self.payment.value()))
        if paid > total:
            QMessageBox.warning(self, "مبلغ غير صحيح", "المبلغ المدفوع لا يمكن أن يتجاوز إجمالي الفاتورة.")
            return
        if paid < total and self.customer.currentData() is None:
            QMessageBox.warning(self, "العميل مطلوب", "البيع الآجل أو الجزئي يتطلب اختيار عميل.")
            return
        session = get_session()
        try:
            service = SaleService(session)
            sale = service.create_sale(
                document_no=f"S-{date.today().strftime('%Y%m%d')}-{uuid4().hex[:8].upper()}",
                business_date=date.today().isoformat(),
                customer_id=self.customer.currentData(),
                items=[{
                    "product_id": self.product.currentData(),
                    "stock_location_id": self.location_id,
                    "quantity": str(self.quantity.value()),
                    "unit_price": str(self.price.value()),
                    "discount": "0",
                }],
                payments=[{"payment_method": "CASH", "amount": str(paid)}] if paid > 0 else [],
                idempotency_key=str(uuid4()),
            )
            session.commit()
            QMessageBox.information(self, "تم الحفظ", f"تم تأكيد فاتورة البيع رقم {sale.document_no} بإجمالي {sale.total:,.2f}.")
            self.payment.setValue(float(total))
            self.product_changed()
        except Exception as exc:
            session.rollback()
            QMessageBox.critical(self, "تعذر حفظ الفاتورة", str(exc))
        finally:
            session.close()
