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
from backend.app.core.models import Product, Purchase, StockLocation, Supplier
from backend.app.modules.finance.models import PaymentMethod
from backend.app.modules.purchases.service import PurchaseService


class PurchasesPage(QWidget):
    """Operational purchase entry connected directly to the purchase service."""

    back_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self.product = QComboBox()
        self.supplier = QComboBox()
        self.location = QComboBox()
        self.payment_method = QComboBox()
        self.quantity = QDoubleSpinBox()
        self.quantity.setDecimals(3)
        self.quantity.setMinimum(0.001)
        self.quantity.setMaximum(999999999)
        self.unit_cost = QDoubleSpinBox()
        self.unit_cost.setDecimals(2)
        self.unit_cost.setMaximum(999999999)
        self.payment = QDoubleSpinBox()
        self.payment.setDecimals(2)
        self.payment.setMaximum(999999999)
        self.document_no = QLabel()
        self.total = QLabel("0.00")
        self.history = QTableWidget(0, 7)
        self.history.setHorizontalHeaderLabels(["التاريخ", "رقم الفاتورة", "المورد", "الصنف", "الكمية", "الإجمالي", "الحالة"])
        self.history.setEditTriggers(QTableWidget.NoEditTriggers)
        self._build()
        self.refresh()

    def _build(self):
        root = QVBoxLayout(self)
        title = QLabel("المشتريات")
        title.setObjectName("pageTitle")
        root.addWidget(title)
        root.addWidget(QLabel("إدخال فاتورة شراء وربطها تلقائيًا بالمخزون والمورد والصندوق."))

        form = QFormLayout()
        form.addRow("رقم الفاتورة", self.document_no)
        form.addRow("المورد", self.supplier)
        form.addRow("الصنف", self.product)
        form.addRow("المخزن", self.location)
        form.addRow("الكمية", self.quantity)
        form.addRow("تكلفة الوحدة", self.unit_cost)
        form.addRow("وسيلة الدفع", self.payment_method)
        form.addRow("المدفوع الآن", self.payment)
        form.addRow("إجمالي الفاتورة", self.total)
        root.addLayout(form)

        buttons = QHBoxLayout()
        save = QPushButton("حفظ وتأكيد فاتورة الشراء")
        save.setObjectName("primaryButton")
        save.clicked.connect(self.save_purchase)
        refresh = QPushButton("تحديث")
        refresh.clicked.connect(self.refresh)
        back = QPushButton("العودة إلى الرئيسية")
        back.setObjectName("secondaryButton")
        back.clicked.connect(self.back_requested.emit)
        buttons.addWidget(save)
        buttons.addWidget(refresh)
        buttons.addStretch()
        buttons.addWidget(back)
        root.addLayout(buttons)
        root.addWidget(QLabel("آخر فواتير الشراء"))
        root.addWidget(self.history, 1)

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
        self.total.setText(f"{self.quantity.value() * self.unit_cost.value():,.2f}")

    def _load_selectors(self, session):
        self.product.clear()
        for p in session.scalars(select(Product).where(Product.is_active.is_(True)).order_by(Product.name)).all():
            self.product.addItem(f"{p.sku} — {p.name}", p.id)
        self.supplier.clear()
        self.supplier.addItem("بدون مورد محدد / شراء نقدي", None)
        for s in session.scalars(select(Supplier).where(Supplier.is_active.is_(True)).order_by(Supplier.name)).all():
            self.supplier.addItem(f"{s.code} — {s.name}", s.id)
        self.location.clear()
        for location in session.scalars(select(StockLocation).where(StockLocation.is_active.is_(True)).order_by(StockLocation.name)).all():
            self.location.addItem(f"{location.code} — {location.name}", location.id)
        self.payment_method.clear()
        self.payment_method.addItem("بدون دفع / آجل", None)
        for method in session.scalars(select(PaymentMethod).where(PaymentMethod.is_active.is_(True)).order_by(PaymentMethod.code)).all():
            self.payment_method.addItem(f"{method.code} — {method.name}", method.code)

    def save_purchase(self):
        product_id = self.product.currentData()
        location_id = self.location.currentData()
        supplier_id = self.supplier.currentData()
        if product_id is None or location_id is None:
            QMessageBox.warning(self, "بيانات ناقصة", "اختر الصنف والمخزن أولاً.")
            return
        total = Decimal(str(self.quantity.value() * self.unit_cost.value())).quantize(Decimal("0.01"))
        paid = Decimal(str(self.payment.value())).quantize(Decimal("0.01"))
        if total <= 0:
            QMessageBox.warning(self, "قيمة غير صحيحة", "يجب أن تكون قيمة الفاتورة أكبر من صفر.")
            return
        if paid > total:
            QMessageBox.warning(self, "مبلغ غير صحيح", "المدفوع لا يمكن أن يتجاوز إجمالي الفاتورة.")
            return
        if paid < total and supplier_id is None:
            QMessageBox.warning(self, "المورد مطلوب", "الفاتورة الآجلة أو الجزئية تحتاج إلى مورد.")
            return
        method = self.payment_method.currentData()
        if paid > 0 and method is None:
            QMessageBox.warning(self, "وسيلة الدفع مطلوبة", "اختر وسيلة الدفع للمبلغ المدفوع.")
            return

        session = get_session()
        try:
            document_no = f"P-{date.today().strftime('%Y%m%d')}-{uuid4().hex[:8].upper()}"
            PurchaseService(session).create_purchase(
                document_no=document_no,
                business_date=date.today().isoformat(),
                supplier_id=supplier_id,
                items=[{
                    "product_id": product_id,
                    "quantity": Decimal(str(self.quantity.value())),
                    "unit_cost": Decimal(str(self.unit_cost.value())),
                    "discount": Decimal("0"),
                    "stock_location_id": location_id,
                }],
                payments=([{"payment_method": method, "amount": paid, "currency": "BASE"}] if paid > 0 else []),
                idempotency_key=str(uuid4()),
            )
            session.commit()
            QMessageBox.information(self, "تم الحفظ", f"تم تأكيد فاتورة الشراء {document_no} وربطها بالمخزون.")
            self.quantity.setValue(0)
            self.payment.setValue(0)
            self.refresh()
        except Exception as exc:
            session.rollback()
            QMessageBox.critical(self, "تعذر الحفظ", str(exc))
        finally:
            session.close()

    def refresh(self):
        session = get_session()
        try:
            self._load_selectors(session)
            rows = session.execute(
                select(Purchase, Supplier, Product)
                .outerjoin(Supplier, Supplier.id == Purchase.supplier_id)
                .join(__import__('backend.app.core.models', fromlist=['PurchaseItem']).PurchaseItem, __import__('backend.app.core.models', fromlist=['PurchaseItem']).PurchaseItem.purchase_id == Purchase.id)
                .join(Product, Product.id == __import__('backend.app.core.models', fromlist=['PurchaseItem']).PurchaseItem.product_id)
                .order_by(Purchase.id.desc())
                .limit(100)
            ).all()
            self.history.setRowCount(len(rows))
            for r, (purchase, supplier, product) in enumerate(rows):
                values = [purchase.business_date, purchase.document_no, supplier.name if supplier else "نقدي", product.name, f"{purchase.total / max(Decimal('0.001'), Decimal(str(purchase.total / max(Decimal('0.001'), Decimal(str(purchase.total)))))):,.3f}" if False else "", f"{purchase.total:,.2f}", purchase.payment_status]
                # Show the actual first-line quantity without complicating the purchase list query.
                values[4] = "متعدد/واحد"
                for c, value in enumerate(values):
                    self.history.setItem(r, c, QTableWidgetItem(str(value)))
            self.history.resizeColumnsToContents()
        finally:
            session.close()
        self.document_no.setText(f"سيُولد تلقائيًا عند الحفظ")
