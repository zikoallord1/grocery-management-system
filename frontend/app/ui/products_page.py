from decimal import Decimal

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFormLayout, QHBoxLayout, QLineEdit, QMessageBox, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget, QDoubleSpinBox
from sqlalchemy import select

from backend.app.core.database import get_session
from backend.app.core.models import Product, Unit


class ProductsPage(QWidget):
    """Operational product master: create and search products."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self.sku = QLineEdit()
        self.name = QLineEdit()
        self.purchase = QDoubleSpinBox()
        self.purchase.setMaximum(999999999)
        self.sale = QDoubleSpinBox()
        self.sale.setMaximum(999999999)
        self.minimum = QDoubleSpinBox()
        self.minimum.setMaximum(999999999)
        self.minimum.setDecimals(3)
        self.search = QLineEdit()
        self.search.setPlaceholderText("بحث بالاسم أو الرمز...")
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["الرمز", "اسم الصنف", "الشراء", "البيع", "الحد الأدنى", "الحالة"])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._build()
        self.refresh()

    def _build(self):
        root = QVBoxLayout(self)
        form = QFormLayout()
        form.addRow("الرمز / SKU", self.sku)
        form.addRow("اسم الصنف", self.name)
        form.addRow("سعر الشراء", self.purchase)
        form.addRow("سعر البيع", self.sale)
        form.addRow("الحد الأدنى للمخزون", self.minimum)
        root.addLayout(form)
        buttons = QHBoxLayout()
        save = QPushButton("حفظ الصنف")
        save.setObjectName("primaryButton")
        save.clicked.connect(self.create_product)
        refresh = QPushButton("تحديث")
        refresh.clicked.connect(self.refresh)
        buttons.addWidget(save)
        buttons.addWidget(refresh)
        buttons.addWidget(self.search, 1)
        self.search.textChanged.connect(self.refresh)
        root.addLayout(buttons)
        root.addWidget(self.table, 1)

    def _default_unit_id(self, session):
        unit = session.scalar(select(Unit).where(Unit.is_active.is_(True)).order_by(Unit.id).limit(1))
        if unit:
            return unit.id
        unit = Unit(name="قطعة", symbol="قطعة", is_active=True)
        session.add(unit)
        session.flush()
        return unit.id

    def create_product(self):
        sku, name = self.sku.text().strip(), self.name.text().strip()
        if not sku or not name:
            QMessageBox.warning(self, "بيانات ناقصة", "أدخل رمز الصنف واسم الصنف.")
            return
        session = get_session()
        try:
            if session.scalar(select(Product).where(Product.sku == sku)):
                QMessageBox.warning(self, "رمز مكرر", "رمز الصنف مستخدم بالفعل.")
                return
            minimum = Decimal(str(self.minimum.value()))
            session.add(Product(sku=sku, name=name, default_unit_id=self._default_unit_id(session), purchase_price=Decimal(str(self.purchase.value())), sale_price=Decimal(str(self.sale.value())), minimum_stock=minimum, reorder_level=minimum, is_active=True))
            session.commit()
            self.sku.clear(); self.name.clear(); self.purchase.setValue(0); self.sale.setValue(0); self.minimum.setValue(0)
            self.refresh()
        except Exception as exc:
            session.rollback()
            QMessageBox.critical(self, "تعذر الحفظ", str(exc))
        finally:
            session.close()

    def refresh(self):
        session = get_session()
        try:
            term = self.search.text().strip()
            query = select(Product).order_by(Product.id.desc())
            if term:
                query = query.where((Product.name.ilike(f"%{term}%")) | (Product.sku.ilike(f"%{term}%")))
            rows = session.scalars(query).all()
            self.table.setRowCount(len(rows))
            for r, p in enumerate(rows):
                values = [p.sku, p.name, f"{p.purchase_price:,.2f}", f"{p.sale_price:,.2f}", f"{p.minimum_stock:,.3f}", "نشط" if p.is_active else "غير نشط"]
                for c, value in enumerate(values):
                    self.table.setItem(r, c, QTableWidgetItem(str(value)))
            self.table.resizeColumnsToContents()
        finally:
            session.close()
