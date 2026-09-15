from decimal import Decimal

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QDialog, QDoubleSpinBox, QFormLayout, QHBoxLayout, QLabel, QMessageBox, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout
from sqlalchemy import select

from backend.app.core.database import get_session
from backend.app.core.models import Product, Unit
from backend.app.core.product_units import ProductUnit


class ProductUnitsDialog(QDialog):
    """Configure unit packaging per product, e.g. this product's carton = 20 pieces."""

    def __init__(self, product_id: int, parent=None):
        super().__init__(parent)
        self.product_id = product_id
        self.setWindowTitle("وحدات وعبوات الصنف")
        self.setMinimumSize(760, 500)
        self.setLayoutDirection(Qt.RightToLeft)
        self.unit = QComboBox()
        self.factor = QDoubleSpinBox(); self.factor.setDecimals(3); self.factor.setRange(0.001, 999999999); self.factor.setValue(1)
        self.sale_price = QDoubleSpinBox(); self.sale_price.setDecimals(2); self.sale_price.setRange(0, 999999999)
        self.purchase_price = QDoubleSpinBox(); self.purchase_price.setDecimals(2); self.purchase_price.setRange(0, 999999999)
        self.barcode = QComboBox(); self.barcode.setEditable(True); self.barcode.setInsertPolicy(QComboBox.NoInsert)
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["الوحدة", "المحتوى بالوحدة الأساسية", "سعر البيع", "سعر الشراء", "الباركود", "الحالة"])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._build()
        self.refresh()

    def _build(self):
        root = QVBoxLayout(self)
        root.addWidget(QLabel("عرّف محتوى الوحدة لهذا الصنف فقط. مثال: كرتون = 20 حبة، بينما صنف آخر يمكن أن يكون كرتونه = 24 حبة."))
        form = QFormLayout()
        form.addRow("الوحدة", self.unit)
        form.addRow("عدد الوحدات الأساسية داخلها", self.factor)
        form.addRow("سعر البيع لهذه الوحدة", self.sale_price)
        form.addRow("سعر الشراء لهذه الوحدة", self.purchase_price)
        form.addRow("باركود هذه الوحدة (اختياري)", self.barcode)
        root.addLayout(form)
        buttons = QHBoxLayout()
        save = QPushButton("حفظ الوحدة"); save.setObjectName("primaryButton"); save.clicked.connect(self.save)
        toggle = QPushButton("تفعيل / إيقاف"); toggle.clicked.connect(self.toggle)
        refresh = QPushButton("تحديث"); refresh.clicked.connect(self.refresh)
        buttons.addWidget(save); buttons.addWidget(toggle); buttons.addWidget(refresh); buttons.addStretch()
        root.addLayout(buttons)
        root.addWidget(self.table, 1)

    def refresh(self):
        session = get_session()
        try:
            product = session.get(Product, self.product_id)
            if not product: return
            self.unit.blockSignals(True); self.unit.clear()
            configs = session.scalars(select(ProductUnit).where(ProductUnit.product_id == self.product_id).order_by(ProductUnit.id)).all()
            configured_ids = {c.unit_id for c in configs}
            for u in session.scalars(select(Unit).where(Unit.is_active.is_(True)).order_by(Unit.name)).all():
                self.unit.addItem(f"{u.name} ({u.symbol})", u.id)
            self.unit.blockSignals(False)
            self.table.setRowCount(len(configs))
            for r, config in enumerate(configs):
                u = session.get(Unit, config.unit_id)
                values = [f"{u.name} ({u.symbol})" if u else str(config.unit_id), f"1 = {config.conversion_factor}", f"{config.sale_price or 0:,.2f}", f"{config.purchase_price or 0:,.2f}", config.barcode or "", "نشط" if config.is_active else "غير نشط"]
                for c, value in enumerate(values): self.table.setItem(r, c, QTableWidgetItem(str(value)))
            self.table.resizeColumnsToContents()
            self._load_selected_defaults(session)
        finally: session.close()

    def _load_selected_defaults(self, session):
        config = session.scalar(select(ProductUnit).where(ProductUnit.product_id == self.product_id, ProductUnit.unit_id == self.unit.currentData()))
        if config:
            self.factor.setValue(float(config.conversion_factor)); self.sale_price.setValue(float(config.sale_price or 0)); self.purchase_price.setValue(float(config.purchase_price or 0)); self.barcode.setEditText(config.barcode or "")
        else:
            product = session.get(Product, self.product_id)
            self.factor.setValue(1); self.sale_price.setValue(float(product.sale_price or 0) if product else 0); self.purchase_price.setValue(float(product.purchase_price or 0) if product else 0); self.barcode.setEditText("")

    def save(self):
        unit_id = self.unit.currentData()
        if unit_id is None: return
        factor = Decimal(str(self.factor.value()))
        if factor <= 0:
            QMessageBox.warning(self, "معامل غير صحيح", "عدد الوحدات الأساسية يجب أن يكون أكبر من صفر."); return
        session = get_session()
        try:
            product = session.get(Product, self.product_id); unit = session.get(Unit, unit_id)
            if not product or not unit: return
            config = session.scalar(select(ProductUnit).where(ProductUnit.product_id == self.product_id, ProductUnit.unit_id == unit_id))
            barcode = self.barcode.currentText().strip() or None
            if barcode:
                duplicate = session.scalar(select(ProductUnit).where(ProductUnit.barcode == barcode, ProductUnit.id != (config.id if config else -1)))
                if duplicate: QMessageBox.warning(self, "باركود مكرر", "باركود الوحدة مستخدم لوحدة أخرى."); return
            if config is None:
                config = ProductUnit(product_id=self.product_id, unit_id=unit_id)
                session.add(config)
            config.conversion_factor = factor; config.sale_price = Decimal(str(self.sale_price.value())); config.purchase_price = Decimal(str(self.purchase_price.value())); config.barcode = barcode; config.is_active = True
            session.commit(); self.refresh()
        except Exception as exc:
            session.rollback(); QMessageBox.critical(self, "تعذر الحفظ", str(exc))
        finally: session.close()

    def toggle(self):
        unit_id = self.unit.currentData()
        if unit_id is None: return
        session = get_session()
        try:
            config = session.scalar(select(ProductUnit).where(ProductUnit.product_id == self.product_id, ProductUnit.unit_id == unit_id))
            if config:
                config.is_active = not config.is_active; session.commit(); self.refresh()
        finally: session.close()
