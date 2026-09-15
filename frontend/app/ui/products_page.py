from decimal import Decimal
from uuid import uuid4

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QDoubleSpinBox, QFormLayout, QHBoxLayout, QLabel,
    QLineEdit, QMessageBox, QPushButton, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)
from sqlalchemy import select

from backend.app.core.database import get_session
from backend.app.core.models import Category, Product, ProductBarcode, Unit
from frontend.app.ui.product_units_dialog import ProductUnitsDialog


class ProductsPage(QWidget):
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
        self.status = QLabel()
        self.status.setWordWrap(True)
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(["الرمز", "اسم الصنف", "التصنيف", "الشراء", "البيع", "الحد الأدنى", "الحالة"])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.itemSelectionChanged.connect(self.load_selected)
        self._build()
        self.refresh()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(14)
        title = QLabel("الأصناف")
        title.setObjectName("pageTitle")
        root.addWidget(title)
        desc = QLabel("إضافة وتعديل الأصناف والباركود والأسعار والحد الأدنى للمخزون. الرمز يولد تلقائيًا إذا تركته فارغًا.")
        desc.setWordWrap(True)
        desc.setObjectName("pageDescription")
        root.addWidget(desc)
        form = QFormLayout()
        form.setSpacing(12)
        self.sku.setPlaceholderText("اختياري — يولد تلقائيًا")
        self.name.setPlaceholderText("اسم الصنف")
        self.barcode.setPlaceholderText("اختياري")
        form.addRow("الرمز / SKU", self.sku)
        form.addRow("اسم الصنف *", self.name)
        form.addRow("الباركود", self.barcode)
        form.addRow("التصنيف", self.category)
        form.addRow("سعر الشراء", self.purchase)
        form.addRow("سعر البيع", self.sale)
        form.addRow("الحد الأدنى للمخزون", self.minimum)
        root.addLayout(form)
        buttons = QHBoxLayout()
        for text, slot in [
            ("حفظ الصنف", self.save_product),
            ("وحدات وعبوات الصنف", self.open_units),
            ("تفعيل / إيقاف", self.toggle_product),
            ("جديد", self.clear_form),
            ("تحديث", self.refresh),
        ]:
            button = QPushButton(text)
            button.clicked.connect(slot)
            buttons.addWidget(button)
        buttons.addWidget(self.search, 1)
        self.search.textChanged.connect(self.refresh)
        root.addLayout(buttons)
        root.addWidget(self.status)
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
        self.category.blockSignals(True)
        self.category.clear()
        self.category.addItem("بدون تصنيف", None)
        for item in session.scalars(select(Category).where(Category.is_active.is_(True)).order_by(Category.name)).all():
            self.category.addItem(item.name, item.id)
        if current is not None:
            index = self.category.findData(current)
            if index >= 0:
                self.category.setCurrentIndex(index)
        self.category.blockSignals(False)

    def save_product(self):
        name = self.name.text().strip()
        sku = self.sku.text().strip() or f"ITM-{uuid4().hex[:10].upper()}"
        barcode = self.barcode.text().strip()
        if not name:
            QMessageBox.warning(self, "بيانات ناقصة", "أدخل اسم الصنف.")
            self.name.setFocus()
            return
        session = get_session()
        try:
            current_id = self.selected_product_id or -1
            duplicate = session.scalar(select(Product).where(Product.sku == sku, Product.id != current_id))
            if duplicate:
                QMessageBox.warning(self, "رمز مكرر", "رمز الصنف مستخدم بالفعل.")
                return
            if barcode:
                duplicate_barcode = session.scalar(
                    select(ProductBarcode).where(ProductBarcode.barcode == barcode, ProductBarcode.product_id != current_id)
                )
                if duplicate_barcode:
                    QMessageBox.warning(self, "باركود مكرر", "الباركود مستخدم لصنف آخر.")
                    return
            product = session.get(Product, self.selected_product_id) if self.selected_product_id else None
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
                if existing is None:
                    session.add(ProductBarcode(product_id=product.id, barcode=barcode, barcode_type="EAN", is_primary=True, is_active=True))
                else:
                    existing.is_active = True
                    existing.is_primary = True
            session.commit()
            self.status.setText(f"تم حفظ الصنف بنجاح: {name}")
            self.clear_form()
            self.refresh()
        except Exception as exc:
            session.rollback()
            QMessageBox.critical(self, "تعذر الحفظ", f"لم يتم حفظ الصنف.\n\nالسبب: {exc}")
        finally:
            session.close()

    def open_units(self):
        if self.selected_product_id is None:
            QMessageBox.warning(self, "اختيار مطلوب", "حدد الصنف أولًا ثم افتح وحداته وعبواته.")
            return
        ProductUnitsDialog(self.selected_product_id, self).exec()

    def load_selected(self):
        row = self.table.currentRow()
        if row < 0:
            return
        item = self.table.item(row, 0)
        product_id = item.data(Qt.UserRole) if item else None
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
            barcode = session.scalar(
                select(ProductBarcode).where(ProductBarcode.product_id == product.id, ProductBarcode.is_active.is_(True)).order_by(ProductBarcode.is_primary.desc(), ProductBarcode.id).limit(1)
            )
            self.barcode.setText(barcode.barcode if barcode else "")
        finally:
            session.close()

    def toggle_product(self):
        if self.selected_product_id is None:
            QMessageBox.warning(self, "اختيار مطلوب", "حدد صنفًا من القائمة أولًا.")
            return
        session = get_session()
        try:
            product = session.get(Product, self.selected_product_id)
            if product:
                product.is_active = not product.is_active
                session.commit()
                self.status.setText("تم تحديث حالة الصنف.")
        except Exception as exc:
            session.rollback()
            QMessageBox.critical(self, "تعذر التحديث", str(exc))
        finally:
            session.close()
        self.clear_form()
        self.refresh()

    def clear_form(self):
        self.selected_product_id = None
        self.sku.clear()
        self.name.clear()
        self.barcode.clear()
        self.purchase.setValue(0)
        self.sale.setValue(0)
        self.minimum.setValue(0)
        self.table.clearSelection()

    def refresh(self):
        session = get_session()
        try:
            self._load_categories(session)
            text = self.search.text().strip()
            query = select(Product).order_by(Product.id.desc())
            if text:
                pattern = f"%{text}%"
                query = query.outerjoin(ProductBarcode, ProductBarcode.product_id == Product.id).where(
                    (Product.name.ilike(pattern)) | (Product.sku.ilike(pattern)) | (ProductBarcode.barcode.ilike(pattern))
                ).distinct()
            rows = session.scalars(query).all()
            self.table.setRowCount(len(rows))
            categories = {item.id: item.name for item in session.scalars(select(Category)).all()}
            for row, product in enumerate(rows):
                values = [
                    product.sku,
                    product.name,
                    categories.get(product.category_id, "بدون تصنيف"),
                    f"{product.purchase_price or 0:,.2f}",
                    f"{product.sale_price or 0:,.2f}",
                    f"{product.minimum_stock or 0:,.3f}",
                    "نشط" if product.is_active else "غير نشط",
                ]
                for column, value in enumerate(values):
                    item = QTableWidgetItem(str(value))
                    if column == 0:
                        item.setData(Qt.UserRole, product.id)
                    self.table.setItem(row, column, item)
            self.table.resizeColumnsToContents()
        finally:
            session.close()
