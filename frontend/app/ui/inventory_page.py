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
from sqlalchemy import case, func, select

from backend.app.core.database import get_session
from backend.app.core.models import Product, StockLocation, StockMovement
from backend.app.modules.inventory.service import InventoryService


class InventoryPage(QWidget):
    back_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        title = QLabel("المخزون")
        title.setObjectName("pageTitle")
        layout.addWidget(title)
        layout.addWidget(QLabel("متابعة أرصدة الأصناف وحركات المخزون وإضافة الرصيد الافتتاحي."))

        form = QFormLayout()
        self.product = QComboBox()
        self.location = QComboBox()
        self.quantity = QDoubleSpinBox()
        self.quantity.setRange(0.001, 999999999)
        self.quantity.setDecimals(3)
        self.unit_cost = QDoubleSpinBox()
        self.unit_cost.setRange(0, 999999999)
        self.unit_cost.setDecimals(2)
        self.search = QComboBox()
        self.search.setEditable(True)
        self.search.addItem("")
        form.addRow("الصنف", self.product)
        form.addRow("المخزن", self.location)
        form.addRow("الكمية", self.quantity)
        form.addRow("تكلفة الوحدة", self.unit_cost)
        layout.addLayout(form)

        buttons = QHBoxLayout()
        save = QPushButton("حفظ الرصيد الافتتاحي")
        save.clicked.connect(self.save_opening_stock)
        refresh = QPushButton("تحديث")
        refresh.clicked.connect(self.refresh)
        back = QPushButton("العودة إلى الرئيسية")
        back.clicked.connect(self.back_requested.emit)
        buttons.addWidget(save)
        buttons.addWidget(refresh)
        buttons.addWidget(back)
        layout.addLayout(buttons)

        layout.addWidget(QLabel("أرصدة المخزون"))
        self.balance_table = QTableWidget(0, 6)
        self.balance_table.setHorizontalHeaderLabels(["الرمز", "الصنف", "المخزن", "الكمية", "متوسط التكلفة", "قيمة المخزون"])
        self.balance_table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.balance_table)

        layout.addWidget(QLabel("حركات المخزون"))
        self.movement_table = QTableWidget(0, 7)
        self.movement_table.setHorizontalHeaderLabels(["التاريخ", "الصنف", "المخزن", "النوع", "الاتجاه", "الكمية", "تكلفة الوحدة"])
        self.movement_table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.movement_table)

    def refresh(self):
        session = get_session()
        try:
            self.load_selectors(session)
            self.refresh_balances(session)
            self.refresh_movements(session)
        finally:
            session.close()

    def load_selectors(self, session):
        current_product = self.product.currentData()
        current_location = self.location.currentData()
        self.product.clear()
        self.location.clear()
        products = session.execute(select(Product).where(Product.is_active.is_(True)).order_by(Product.name)).scalars().all()
        locations = session.execute(select(StockLocation).where(StockLocation.is_active.is_(True)).order_by(StockLocation.name)).scalars().all()
        for item in products:
            self.product.addItem(f"{item.name} — {item.sku}", item.id)
        for item in locations:
            self.location.addItem(item.name, item.id)
        if current_product is not None:
            index = self.product.findData(current_product)
            if index >= 0:
                self.product.setCurrentIndex(index)
        if current_location is not None:
            index = self.location.findData(current_location)
            if index >= 0:
                self.location.setCurrentIndex(index)

    def refresh_balances(self, session=None):
        owns = session is None
        session = session or get_session()
        try:
            movement_balance = (
                select(
                    StockMovement.product_id.label("product_id"),
                    StockMovement.stock_location_id.label("location_id"),
                    func.coalesce(func.sum(case((StockMovement.direction == "IN", StockMovement.quantity), (StockMovement.direction == "OUT", -StockMovement.quantity), else_=0)), 0).label("quantity"),
                    func.coalesce(func.sum(case((StockMovement.direction == "IN", StockMovement.quantity * StockMovement.unit_cost), (StockMovement.direction == "OUT", -(StockMovement.quantity * StockMovement.unit_cost)), else_=0)), 0).label("value"),
                )
                .group_by(StockMovement.product_id, StockMovement.stock_location_id)
                .subquery()
            )
            rows = session.execute(
                select(
                    Product,
                    StockLocation,
                    func.coalesce(movement_balance.c.quantity, 0),
                    func.coalesce(movement_balance.c.value, 0),
                )
                .select_from(Product, StockLocation)
                .outerjoin(
                    movement_balance,
                    (movement_balance.c.product_id == Product.id)
                    & (movement_balance.c.location_id == StockLocation.id),
                )
                .where(Product.is_active.is_(True), StockLocation.is_active.is_(True))
                .order_by(Product.name, StockLocation.name)
            ).all()
            self.balance_table.setRowCount(len(rows))
            for r, (product, location, quantity, value) in enumerate(rows):
                qty = Decimal(str(quantity))
                total_value = Decimal(str(value))
                avg_cost = total_value / qty if qty else Decimal("0")
                values = [product.sku, product.name, location.name, f"{qty:,.3f}", f"{avg_cost:,.2f}", f"{total_value:,.2f}"]
                for c, item in enumerate(values):
                    self.balance_table.setItem(r, c, QTableWidgetItem(str(item)))
            self.balance_table.resizeColumnsToContents()
        finally:
            if owns:
                session.close()

    def refresh_movements(self, session=None):
        owns = session is None
        session = session or get_session()
        try:
            term = self.search.currentText().strip()
            query = (
                select(StockMovement, Product, StockLocation)
                .join(Product, Product.id == StockMovement.product_id)
                .join(StockLocation, StockLocation.id == StockMovement.stock_location_id)
                .order_by(StockMovement.id.desc())
                .limit(500)
            )
            if term:
                pattern = f"%{term}%"
                query = query.where((Product.name.ilike(pattern)) | (Product.sku.ilike(pattern)) | (StockMovement.movement_type.ilike(pattern)))
            rows = session.execute(query).all()
            self.movement_table.setRowCount(len(rows))
            for r, (movement, product, location) in enumerate(rows):
                values = [movement.business_date, product.name, location.name, movement.movement_type, movement.direction, f"{Decimal(str(movement.quantity)):,.3f}", f"{Decimal(str(movement.unit_cost)):,.2f}"]
                for c, item in enumerate(values):
                    self.movement_table.setItem(r, c, QTableWidgetItem(str(item)))
            self.movement_table.resizeColumnsToContents()
        finally:
            if owns:
                session.close()

    def save_opening_stock(self):
        product_id = self.product.currentData()
        location_id = self.location.currentData()
        quantity = Decimal(str(self.quantity.value()))
        unit_cost = Decimal(str(self.unit_cost.value()))
        if not product_id or not location_id or quantity <= 0:
            QMessageBox.warning(self, "تنبيه", "اختر الصنف والمخزن وأدخل كمية صحيحة.")
            return
        session = get_session()
        try:
            InventoryService(session).add_stock(
                product_id=product_id,
                stock_location_id=location_id,
                quantity=quantity,
                unit_cost=unit_cost,
                business_date=date.today().isoformat(),
                idempotency_key=str(uuid4()),
            )
            session.commit()
            QMessageBox.information(self, "تم الحفظ", "تمت إضافة الرصيد الافتتاحي بنجاح.")
            self.quantity.setValue(0)
            self.refresh()
        except Exception as exc:
            session.rollback()
            QMessageBox.critical(self, "تعذر الحفظ", str(exc))
        finally:
            session.close()
