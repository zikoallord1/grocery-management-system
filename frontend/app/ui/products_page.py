from decimal import Decimal

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy import select

from backend.app.core.database import get_session
from backend.app.core.models import Category, Product, ProductBarcode, Unit


class ProductsPage(QWidget):
    """Operational product master: create, edit, activate/deactivate and search products."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self.selected_product_id = None
        self.sku = QLineEdit()
        self.name = QLineEdit()
        self.barcode = QLineEdit()
        self.category = QComboBox()
        self.purchase = QDoubleSpinBox()
        self.purchase.setMaximum(999999999)
        self.sale = QDoubleSpinBox()
        self.sale.setMaximum(999999999)
        self.minimum = QDoubleSpinBox()
        self.minimum.setMaximum(999999999)
        self.minimum.setDecimals(3)
        self.search = QLineEdit()
        self.search.setPlaceholderText("بحث بالاسم أو الرمز أو الباركود...")
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(["الرمز", "اسم الصنف", "التصنيف", "الشراء", "البيع", "الحد الأدنى", "الحالة"])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.itemSelectionChanged.connect(self.load_selected)
        self._build()
        self.refresh()

    def _build(self):
        root = QVBoxLayout(self)
        form = QFormLayout()
        form.addRow("الرمز / SKU", self.sku)
        form.addRow("اسم الصنف", self.name)
        form.addRow("الباركود", self.barcode)
        form.addRow("التصنيف", self.category)
        form.addRow("سعر الشراء", self.purchase)
        form.addRow("سعر البيع", self.sale)
        form.addRow("الحد الأدنى للمخزون", self.minimum)
        root.addLayout(form)

        buttons = QHBoxLayout()
        save = QPushButton("حفظ الصنف")
        save.setObjectName("primaryButton")
        save.clicked.connect(self.save_product)
        toggle = QPushButton("تفعيل / إيقاف")
        toggle.clicked.connect(self.toggle_product)
        clear = QPushButton("جديد")
        clear.clicked.connect(self.clear_form)
        refresh = QPushButton("تحديث")
        refresh.clicked.connect(self.refresh)
        buttons.addWidget(save)
        buttons.addWidget(toggle)
        buttons.addWidget(clear)
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

    def _load_categories(self, session):
        current = self.category.currentData()
        self.category.clear()
        self.category.addItem("بدون تصنيف", None)
        for item in session.scalars(select(Category).where(Category.is_active.is_(True)).order_by(Category.name)).all():
            self.category.addItem(item.name, item.id)
        if current is not None:
            idx = self.category.findData(current)
            if idx >= 0:
                self.category.setCurrentIndex(idx)

    def save_product(self):
        sku, name = self.sku.text().strip(), self.name.text().strip()
        barcode = self.barcode.text().strip()
        if not sku or not name:
            QMessageBox.warning(self, "بيانات ناقصة", "أدخل رمز الصنف واسم الصنف.")
            return
        session = get_session()
        try:
            product = session.get(Product, self.selected_product_id) if self.selected_product_id else None
            duplicate = session.scalar(select(Product).where(Product.sku == sku, Product.id != (product.id if product else -1)))
            if duplicate:
                QMessageBox.warning(self, "رمز مكرر", "رمز الصنف مستخدم بالفعل.")
                return
            if barcode:
                duplicate_barcode = session.scalar(select(ProductBarcode).where(ProductBarcode.barcode == barcode, ProductBarcode.product_id != (product.id if product else -1)))
                if duplicate_barcode:
                    QMessageBox.warning(self, "باركود مكرر", "الباركود مستخدم لصنف آخر.")
                    return
            if product is None:
                product = Product(
                    sku=sku,
                    name=name,
                    default_unit_id=self._default_unit_id(session),
                    category_id=self.category.currentData(),
                    purchase_price=Decimal(str(self.purchase.value())),
                    sale_price=Decimal(str(self.sale.value())),
                    minimum_stock=Decimal(str(self.minimum.value())),
                    reorder_level=Decimal(str(self.minimum.value())),
                    is_active=True,
                )
                session.add(product)
                session.flush()
            else:
                product.sku = sku
                product.name = name
                product.category_id = self.category.currentData()
                product.purchase_price = Decimal(str(self.purchase.value()))
                product.sale_price = Decimal(str(self.sale.value()))
                product.minimum_stock = Decimal(str(self.minimum.value()))
                product.reorder_level = Decimal(str(self.minimum.value()))
            if barcode:
                existing = session.scalar(select(ProductBarcode).where(ProductBarcode.product_id == product.id, ProductBarcode.barcode == barcode))
                if not existing:
                    session.add(ProductBarcode(product_id=product.id, barcode=barcode, barcode_type="EAN", is_primary=True, is_active=True))
                else:
                    existing.is_active = True
                    existing.is_primary = True
            session.commit()
            self.clear_form()
            self.refresh()
        except Exception as exc:
            session.rollback()
            QMessageBox.critical(self, "تعذر الحفظ", str(exc))
        finally:
            session.close()

    def load_selected(self):
        row = self.table.currentRow()
        if row < 0:
            return
        product_id = self.table.item(row, 0).data(Qt.UserRole)
        if product_id is None:
            return
        session = get_session()
        try:
            product = session.get(Product, product_id)
            if not product:
                return
            self.selected_product_id = product.id
            self.sku.setText(product.sku)
            self.name.setText(product.name)
            self.category.setCurrentIndex(max(0, self.category.findData(product.category_id)))
            self.purchase.setValue(float(product.purchase_price or 0))
            self.sale.setValue(float(product.sale_price or 0))
            self.minimum.setValue(float(product.minimum_stock or 0))
            code = session.scalar(select(ProductBarcode).where(ProductBarcode.product_id == product.id, ProductBarcode.is_active.is_(True)).order_by(ProductBarcode.is_primary.desc(), ProductBarcode.id).limit(1))
            self.barcode.setText(code.barcode if code else "")
        finally:
            session.close()

    def toggle_product(self):
        if self.selected_product_id is None:
            QMessageBox.warning(self, "اختيار مطلوب", "حدد الصنف من الجدول أولاً.")
            return
        session = get_session()
        try:
            product = session.get(Product, self.selected_product_id)
            if product:
                product.is_active = not product.is_active
                session.commit()
                self.clear_form()
                self.refresh()
        except Exception as exc:
            session.rollback()
            QMessageBox.critical(self, "تعذر التحديث", str(exc))
        finally:
            session.close()

    def clear_form(self):
        self.selected_product_id = None
        self.sku.clear()
        self.name.clear()
        self.barcode.clear()
        self.category.setCurrentIndex(0)
        self.purchase.setValue(0)
        self.sale.setValue(0)
        self.minimum.setValue(0)
        self.table.clearSelection()

    def refresh(self):
        session = get_session()
        try:
            self._load_categories(session)
            term = self.search.text().strip()
            query = select(Product).order_by(Product.id.desc())
            if term:
                pattern = f"%{term}%"
                query = query.outerjoin(ProductBarcode, ProductBarcode.product_id == Product.id).where(
                    (Product.name.ilike(pattern)) | (Product.sku.ilike(pattern)) | (ProductBarcode.barcode.ilike(pattern))
                ).distinct()
            rows = session.scalars(query).all()
            self.table.setRowCount(len(rows))
            for r, p in enumerate(rows):
                category = session.get(Category, p.category_id) if p.category_id else None
                values = [p.sku, p.name, category.name if category else "بدون تصنيف", f"{p.purchase_price:,.2f}", f"{p.sale_price:,.2f}", f"{p.minimum_stock:,.3f}", "نشط" if p.is_active else "غير نشط"]
                for c, value in enumerate(values):
                    item = QTableWidgetItem(str(value))
                    if c == 0:
                        item.setData(Qt.UserRole, p.id)
                    self.table.setItem(r, c, item)
            self.table.resizeColumnsToContents()
        finally:
            session.close()
