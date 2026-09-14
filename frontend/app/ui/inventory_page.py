from datetime import date
from decimal import Decimal
from uuid import uuid4

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox, QDoubleSpinBox, QFormLayout, QHBoxLayout, QLabel,
    QMessageBox, QPushButton, QTableWidget, QTableWidgetItem, QTabWidget,
    QVBoxLayout, QWidget,
)
from sqlalchemy import case, func, select

from backend.app.core.database import get_session
from backend.app.core.models import Product, StockLocation, StockMovement
from backend.app.modules.inventory.service import InventoryService


class InventoryPage(QWidget):
    """واجهة تشغيلية للمخزون: أرصدة، إدخال، تحويل، جرد وتسوية، وحركة قابلة للبحث."""

    back_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self.product = QComboBox()
        self.quantity = QDoubleSpinBox()
        self.quantity.setDecimals(3)
        self.quantity.setMinimum(0.001)
        self.quantity.setMaximum(999999999)
        self.unit_cost = QDoubleSpinBox()
        self.unit_cost.setDecimals(2)
        self.unit_cost.setMaximum(999999999)
        self.location = QComboBox()
        self.transfer_product = QComboBox()
        self.transfer_source = QComboBox()
        self.transfer_target = QComboBox()
        self.transfer_quantity = QDoubleSpinBox()
        self.transfer_quantity.setDecimals(3)
        self.transfer_quantity.setMinimum(0.001)
        self.transfer_quantity.setMaximum(999999999)
        self.adjustment_product = QComboBox()
        self.adjustment_location = QComboBox()
        self.actual_quantity = QDoubleSpinBox()
        self.actual_quantity.setDecimals(3)
        self.actual_quantity.setMinimum(0)
        self.actual_quantity.setMaximum(999999999)
        self.adjustment_reason = QComboBox()
        self.adjustment_reason.setEditable(True)
        self.adjustment_reason.lineEdit().setPlaceholderText("سبب الجرد/التسوية (اختياري)")
        self.search = QComboBox()
        self.search.setEditable(True)
        self.search.lineEdit().setPlaceholderText("بحث في حركة المخزون...")
        self.balance_table = QTableWidget(0, 6)
        self.balance_table.setHorizontalHeaderLabels(["الرمز", "الصنف", "المخزن", "الكمية", "سعر التكلفة", "قيمة المخزون"])
        self.balance_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.movement_table = QTableWidget(0, 7)
        self.movement_table.setHorizontalHeaderLabels(["التاريخ", "الرمز", "الصنف", "المخزن", "الحركة", "الكمية", "التكلفة"])
        self.movement_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._build()
        self.refresh()

    def _build(self):
        root = QVBoxLayout(self)
        heading = QLabel("المخزون")
        heading.setObjectName("pageTitle")
        root.addWidget(heading)
        text = QLabel("الأرصدة والرصيد الافتتاحي والتحويل والجرد والتسوية وحركة الأصناف.")
        text.setObjectName("pageDescription")
        root.addWidget(text)
        form = QFormLayout()
        form.addRow("الصنف", self.product)
        form.addRow("المخزن", self.location)
        form.addRow("الكمية", self.quantity)
        form.addRow("تكلفة الوحدة", self.unit_cost)
        root.addLayout(form)
        buttons = QHBoxLayout()
        opening = QPushButton("إضافة رصيد افتتاحي")
        opening.setObjectName("primaryButton")
        opening.clicked.connect(self.add_opening_stock)
        refresh = QPushButton("تحديث البيانات")
        refresh.clicked.connect(self.refresh)
        back = QPushButton("العودة إلى الرئيسية")
        back.setObjectName("secondaryButton")
        back.clicked.connect(self.back_requested.emit)
        buttons.addWidget(opening)
        buttons.addWidget(refresh)
        buttons.addStretch()
        buttons.addWidget(back)
        root.addLayout(buttons)
        operations = QTabWidget()
        transfer_tab = QWidget()
        transfer_form = QFormLayout(transfer_tab)
        transfer_form.addRow("الصنف", self.transfer_product)
        self.transfer_product.currentIndexChanged.connect(self._sync_transfer_product)
        transfer_form.addRow("من مخزن", self.transfer_source)
        transfer_form.addRow("إلى مخزن", self.transfer_target)
        transfer_form.addRow("الكمية", self.transfer_quantity)
        transfer_button = QPushButton("تنفيذ تحويل المخزون")
        transfer_button.setObjectName("primaryButton")
        transfer_button.clicked.connect(self.transfer_stock)
        transfer_form.addRow(transfer_button)
        adjustment_tab = QWidget()
        adjustment_form = QFormLayout(adjustment_tab)
        adjustment_form.addRow("الصنف", self.adjustment_product)
        self.adjustment_product.currentIndexChanged.connect(self._sync_adjustment_product)
        adjustment_form.addRow("المخزن", self.adjustment_location)
        adjustment_form.addRow("الكمية الفعلية", self.actual_quantity)
        adjustment_form.addRow("السبب", self.adjustment_reason)
        adjustment_button = QPushButton("حفظ نتيجة الجرد والتسوية")
        adjustment_button.setObjectName("primaryButton")
        adjustment_button.clicked.connect(self.adjust_stock)
        adjustment_form.addRow(adjustment_button)
        operations.addTab(transfer_tab, "تحويل بين المخازن")
        operations.addTab(adjustment_tab, "الجرد والتسوية")
        root.addWidget(operations)
        tabs = QTabWidget()
        balances = QWidget()
        QVBoxLayout(balances).addWidget(self.balance_table)
        movements = QWidget()
        movement_layout = QVBoxLayout(movements)
        movement_layout.addWidget(self.search)
        movement_layout.addWidget(self.movement_table)
        tabs.addTab(balances, "أرصدة المخزون")
        tabs.addTab(movements, "حركة المخزون")
        root.addWidget(tabs, 1)
        self.search.currentTextChanged.connect(self.refresh_movements)

    def _load_selectors(self, session):
        current_product = self.product.currentData()
        current_location = self.location.currentData()
        products = session.scalars(select(Product).where(Product.is_active.is_(True)).order_by(Product.name)).all()
        locations = session.scalars(select(StockLocation).where(StockLocation.is_active.is_(True)).order_by(StockLocation.name)).all()
        for selector in [self.product, self.transfer_product, self.adjustment_product]:
            selector.blockSignals(True)
            selector.clear()
            for item in products:
                selector.addItem(f"{item.sku} — {item.name}", item.id)
            selector.blockSignals(False)
        for selector in [self.location, self.transfer_source, self.transfer_target, self.adjustment_location]:
            selector.clear()
            for item in locations:
                selector.addItem(f"{item.code} — {item.name}", item.id)
        for selector in [self.product, self.transfer_product, self.adjustment_product]:
            if current_product is not None:
                idx = selector.findData(current_product)
                if idx >= 0:
                    selector.setCurrentIndex(idx)
        if current_location is not None:
            idx = self.location.findData(current_location)
            if idx >= 0:
                self.location.setCurrentIndex(idx)
        if self.product.currentData() is not None:
            product = session.get(Product, self.product.currentData())
            if product:
                self.unit_cost.setValue(float(product.purchase_price or 0))

    def _sync_transfer_product(self):
        if self.transfer_product.currentData() is not None:
            self.product.setCurrentIndex(max(0, self.product.findData(self.transfer_product.currentData())))

    def _sync_adjustment_product(self):
        if self.adjustment_product.currentData() is not None:
            self.product.setCurrentIndex(max(0, self.product.findData(self.adjustment_product.currentData())))

    def add_opening_stock(self):
        product_id = self.product.currentData(); location_id = self.location.currentData()
        quantity = Decimal(str(self.quantity.value())); unit_cost = Decimal(str(self.unit_cost.value()))
        if product_id is None or location_id is None:
            QMessageBox.warning(self, "بيانات ناقصة", "اختر الصنف والمخزن أولاً."); return
        session = get_session()
        try:
            InventoryService(session).add_stock(product_id=product_id, stock_location_id=location_id, quantity=quantity, unit_cost=unit_cost, business_date=date.today().isoformat(), idempotency_key=str(uuid4()), reference_type="OPENING_STOCK")
            session.commit(); self.quantity.setValue(0)
            QMessageBox.information(self, "تم الحفظ", "تمت إضافة الرصيد الافتتاحي وتسجيل الحركة."); self.refresh()
        except Exception as exc:
            session.rollback(); QMessageBox.critical(self, "تعذر الحفظ", str(exc))
        finally: session.close()

    def transfer_stock(self):
        product_id = self.transfer_product.currentData(); source_id = self.transfer_source.currentData(); target_id = self.transfer_target.currentData(); quantity = Decimal(str(self.transfer_quantity.value()))
        if product_id is None or source_id is None or target_id is None:
            QMessageBox.warning(self, "بيانات ناقصة", "اختر الصنف ومخزني المصدر والاستلام."); return
        if source_id == target_id:
            QMessageBox.warning(self, "مخزن غير صحيح", "يجب أن يكون مخزن الاستلام مختلفًا عن مخزن المصدر."); return
        session = get_session()
        try:
            InventoryService(session).transfer_stock(product_id=product_id, source_location_id=source_id, target_location_id=target_id, quantity=quantity, unit_cost=Decimal(str(self.unit_cost.value())), business_date=date.today().isoformat(), idempotency_key=str(uuid4()))
            session.commit(); self.transfer_quantity.setValue(0)
            QMessageBox.information(self, "تم التحويل", "تم تحويل الكمية وتسجيل حركتي الخروج والدخول."); self.refresh()
        except Exception as exc:
            session.rollback(); QMessageBox.critical(self, "تعذر التحويل", str(exc))
        finally: session.close()

    def adjust_stock(self):
        product_id = self.adjustment_product.currentData(); location_id = self.adjustment_location.currentData(); actual = Decimal(str(self.actual_quantity.value()))
        if product_id is None or location_id is None:
            QMessageBox.warning(self, "بيانات ناقصة", "اختر الصنف والمخزن أولاً."); return
        session = get_session()
        try:
            InventoryService(session).adjust_stock(product_id=product_id, stock_location_id=location_id, actual_quantity=actual, unit_cost=Decimal(str(self.unit_cost.value())), business_date=date.today().isoformat(), idempotency_key=str(uuid4()), reason=self.adjustment_reason.currentText().strip() or None)
            session.commit(); QMessageBox.information(self, "تمت التسوية", "تم تسجيل فرق الجرد كتسوية مخزنية دون حذف الحركات السابقة."); self.refresh()
        except Exception as exc:
            session.rollback(); QMessageBox.critical(self, "تعذر الحفظ", str(exc))
        finally: session.close()

    def refresh(self):
        session = get_session()
        try:
            self._load_selectors(session); self.refresh_balances(session); self.refresh_movements(session)
        finally: session.close()

    def refresh_balances(self, session=None):
        owns = session is None; session = session or get_session()
        try:
            movement_balance = select(StockMovement.product_id.label("product_id"), StockMovement.stock_location_id.label("location_id"), func.coalesce(func.sum(case((StockMovement.direction == "IN", StockMovement.quantity), (StockMovement.direction == "OUT", -StockMovement.quantity), else_=0)), 0).label("quantity"), func.coalesce(func.sum(case((StockMovement.direction == "IN", StockMovement.quantity * StockMovement.unit_cost), (StockMovement.direction == "OUT", -(StockMovement.quantity * StockMovement.unit_cost)), else_=0)), 0).label("value")).group_by(StockMovement.product_id, StockMovement.stock_location_id).subquery()
            rows = session.execute(select(Product, StockLocation, func.coalesce(movement_balance.c.quantity, 0), func.coalesce(movement_balance.c.value, 0)).select_from(Product).join(StockLocation, StockLocation.is_active.is_(True)).outerjoin(movement_balance, (movement_balance.c.product_id == Product.id) & (movement_balance.c.location_id == StockLocation.id)).where(Product.is_active.is_(True)).order_by(Product.name, StockLocation.name)).all()
            self.balance_table.setRowCount(len(rows))
            for r, (product, location, quantity, value) in enumerate(rows):
                qty = Decimal(str(quantity)); total_value = Decimal(str(value)); avg_cost = total_value / qty if qty else Decimal("0")
                for c, item in enumerate([product.sku, product.name, location.name, f"{qty:,.3f}", f"{avg_cost:,.2f}", f"{total_value:,.2f}"]): self.balance_table.setItem(r, c, QTableWidgetItem(str(item)))
            self.balance_table.resizeColumnsToContents()
        finally:
            if owns: session.close()

    def refresh_movements(self, session=None):
        owns = session is None; session = session or get_session()
        try:
            term = self.search.currentText().strip()
            query = select(StockMovement, Product, StockLocation).join(Product, Product.id == StockMovement.product_id).join(StockLocation, StockLocation.id == StockMovement.stock_location_id).order_by(StockMovement.id.desc()).limit(500)
            if term:
                pattern = f"%{term}%"; query = query.where((Product.name.ilike(pattern)) | (Product.sku.ilike(pattern)) | (StockMovement.movement_type.ilike(pattern)))
            rows = session.execute(query).all(); self.movement_table.setRowCount(len(rows))
            movement_names = {"TRANSFER_OUT": "تحويل - خروج", "TRANSFER_IN": "تحويل - دخول", "ADJUSTMENT_IN": "تسوية - زيادة", "ADJUSTMENT_OUT": "تسوية - نقص"}
            for r, (movement, product, location) in enumerate(rows):
                direction = "دخول" if movement.direction == "IN" else "خروج"; action = movement_names.get(movement.movement_type, direction)
                values = [movement.business_date, product.sku, product.name, location.name, action, f"{Decimal(str(movement.quantity)):,.3f}", f"{Decimal(str(movement.unit_cost)):,.2f}"]
                for c, item in enumerate(values): self.movement_table.setItem(r, c, QTableWidgetItem(str(item)))
            self.movement_table.resizeColumnsToContents()
        finally:
            if owns: session.close()
