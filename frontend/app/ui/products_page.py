from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget
from sqlalchemy import select

from backend.app.core.database import get_session
from backend.app.core.models import Category, Product, ProductBarcode, Unit


class ProductsPage(QWidget):
    back_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self.editing_id = None
        self.sku = QLineEdit(); self.name = QLineEdit(); self.barcode = QLineEdit()
        self.category = QComboBox(); self.unit = QComboBox()
        self.purchase_price = QDoubleSpinBox(); self.sale_price = QDoubleSpinBox()
        self.minimum_stock = QDoubleSpinBox(); self.reorder_level = QDoubleSpinBox()
        self.active = QCheckBox("الصنف فعال وقابل للبيع"); self.active.setChecked(True)
        for box in (self.purchase_price, self.sale_price): box.setDecimals(2); box.setMaximum(999999999)
        for box in (self.minimum_stock, self.reorder_level): box.setDecimals(3); box.setMaximum(999999999)
        self.search = QLineEdit(); self.search.setPlaceholderText("بحث باسم الصنف أو الرمز أو الباركود...")
        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(["الرمز", "الصنف", "الباركود", "الفئة", "الوحدة", "سعر الشراء", "سعر البيع", "الحالة"])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._build(); self.refresh()

    def _build(self):
        root = QVBoxLayout(self); root.setContentsMargins(18, 18, 18, 18); root.setSpacing(12)
        title = QLabel("الأصناف"); title.setObjectName("pageTitle"); root.addWidget(title)
        desc = QLabel("إضافة الأصناف وكمياتها وأسعارها وبياناتها التابعة. بيانات الصنف تُستخدم مباشرة في المبيعات والمشتريات والمخزون.")
        desc.setWordWrap(True); desc.setObjectName("pageDescription"); root.addWidget(desc)
        form = QFormLayout(); form.setHorizontalSpacing(18); form.setVerticalSpacing(10)
        for label, field in [("رمز الصنف", self.sku), ("اسم الصنف", self.name), ("الباركود", self.barcode), ("الفئة", self.category), ("الوحدة", self.unit), ("سعر الشراء", self.purchase_price), ("سعر البيع", self.sale_price), ("الحد الأدنى للمخزون", self.minimum_stock), ("نقطة إعادة الطلب", self.reorder_level), ("الحالة", self.active)]: form.addRow(label, field)
        root.addLayout(form)
        actions = QHBoxLayout()
        save = QPushButton("حفظ الصنف"); save.setObjectName("primaryButton"); save.clicked.connect(self.save_product)
        new = QPushButton("صنف جديد"); new.clicked.connect(self.clear_form)
        disable = QPushButton("تعطيل الصنف"); disable.setObjectName("secondaryButton"); disable.clicked.connect(self.disable_product)
        back = QPushButton("العودة إلى الرئيسية"); back.setObjectName("secondaryButton"); back.clicked.connect(self.back_requested.emit)
        for button in (save, new, disable): actions.addWidget(button)
        actions.addStretch(); actions.addWidget(back); root.addLayout(actions)
        root.addWidget(self.search); root.addWidget(self.table, 1)
        self.search.textChanged.connect(self.refresh_table); self.table.cellDoubleClicked.connect(self.load_selected)

    def _load_choices(self, session):
        self.category.clear(); self.category.addItem("بدون فئة", None)
        for row in session.scalars(select(Category).where(Category.is_active.is_(True)).order_by(Category.name)).all(): self.category.addItem(row.name, row.id)
        self.unit.clear()
        for row in session.scalars(select(Unit).where(Unit.is_active.is_(True)).order_by(Unit.name)).all(): self.unit.addItem(f"{row.name} ({row.symbol})", row.id)

    def refresh(self):
        session = get_session()
        try: self._load_choices(session); self.refresh_table(session)
        finally: session.close()

    def refresh_table(self, session=None):
        owns = session is None; session = session or get_session()
        try:
            term = self.search.text().strip()
            query = select(Product, ProductBarcode, Category, Unit).join(Unit, Unit.id == Product.default_unit_id).outerjoin(Category, Category.id == Product.category_id).outerjoin(ProductBarcode, (ProductBarcode.product_id == Product.id) & ProductBarcode.is_primary.is_(True)).where(Product.is_active.is_(True)).order_by(Product.name)
            if term:
                pattern = f"%{term}%"; query = query.where((Product.name.ilike(pattern)) | (Product.sku.ilike(pattern)) | (ProductBarcode.barcode.ilike(pattern)))
            rows = session.execute(query).all(); self.table.setRowCount(len(rows))
            for r, (product, barcode, category, unit) in enumerate(rows):
                values = [product.sku, product.name, barcode.barcode if barcode else "", category.name if category else "", unit.name, f"{product.purchase_price:,.2f}", f"{product.sale_price:,.2f}", "فعال" if product.is_active else "موقوف"]
                for c, value in enumerate(values): self.table.setItem(r, c, QTableWidgetItem(str(value)))
                self.table.item(r, 0).setData(Qt.UserRole, product.id)
            self.table.resizeColumnsToContents()
        finally:
            if owns: session.close()

    def clear_form(self):
        self.editing_id = None
        for field in (self.sku, self.name, self.barcode): field.clear()
        for box in (self.purchase_price, self.sale_price, self.minimum_stock, self.reorder_level): box.setValue(0)
        self.active.setChecked(True)
        if self.category.count(): self.category.setCurrentIndex(0)
        if self.unit.count(): self.unit.setCurrentIndex(0)

    def load_selected(self, row, _column):
        item = self.table.item(row, 0)
        if not item: return
        session = get_session()
        try:
            product = session.get(Product, item.data(Qt.UserRole))
            if not product: return
            self.editing_id = product.id; self.sku.setText(product.sku); self.name.setText(product.name)
            barcode = session.scalar(select(ProductBarcode).where(ProductBarcode.product_id == product.id, ProductBarcode.is_primary.is_(True), ProductBarcode.is_active.is_(True)))
            self.barcode.setText(barcode.barcode if barcode else "")
            self.category.setCurrentIndex(max(0, self.category.findData(product.category_id))); self.unit.setCurrentIndex(max(0, self.unit.findData(product.default_unit_id)))
            self.purchase_price.setValue(float(product.purchase_price)); self.sale_price.setValue(float(product.sale_price)); self.minimum_stock.setValue(float(product.minimum_stock)); self.reorder_level.setValue(float(product.reorder_level)); self.active.setChecked(bool(product.is_active))
        finally: session.close()

    def save_product(self):
        if not self.sku.text().strip() or not self.name.text().strip() or self.unit.currentData() is None:
            QMessageBox.warning(self, "بيانات ناقصة", "أدخل رمز الصنف واسمه واختر الوحدة."); return
        session = get_session()
        try:
            product = session.get(Product, self.editing_id) if self.editing_id else None
            if product is None: product = Product(sku=self.sku.text().strip(), name=self.name.text().strip(), default_unit_id=self.unit.currentData()); session.add(product); session.flush()
            product.sku = self.sku.text().strip(); product.name = self.name.text().strip(); product.category_id = self.category.currentData(); product.default_unit_id = self.unit.currentData(); product.purchase_price = self.purchase_price.value(); product.sale_price = self.sale_price.value(); product.minimum_stock = self.minimum_stock.value(); product.reorder_level = self.reorder_level.value(); product.is_active = self.active.isChecked()
            barcode_text = self.barcode.text().strip()
            if barcode_text:
                barcode = session.scalar(select(ProductBarcode).where(ProductBarcode.product_id == product.id, ProductBarcode.is_primary.is_(True)))
                if barcode is None: session.add(ProductBarcode(product_id=product.id, barcode=barcode_text, is_primary=True, is_active=True))
                else: barcode.barcode = barcode_text; barcode.is_active = True
            session.commit(); self.editing_id = product.id; QMessageBox.information(self, "تم الحفظ", "تم حفظ بيانات الصنف بنجاح."); self.refresh_table()
        except Exception as exc:
            session.rollback(); QMessageBox.critical(self, "تعذر الحفظ", str(exc))
        finally: session.close()

    def disable_product(self):
        if not self.editing_id: return
        session = get_session()
        try:
            product = session.get(Product, self.editing_id)
            if product: product.is_active = False; session.commit(); self.clear_form(); self.refresh_table()
        except Exception as exc:
            session.rollback(); QMessageBox.critical(self, "تعذر التعطيل", str(exc))
        finally: session.close()
