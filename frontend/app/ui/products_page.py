from decimal import Decimal
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox,QDoubleSpinBox,QFormLayout,QHBoxLayout,QLineEdit,QMessageBox,QPushButton,QTableWidget,QTableWidgetItem,QVBoxLayout,QWidget
from sqlalchemy import select
from backend.app.core.database import get_session
from backend.app.core.models import Category,Product,ProductBarcode,Unit
from frontend.app.ui.product_units_dialog import ProductUnitsDialog
class ProductsPage(QWidget):
 def __init__(self,parent=None):
  super().__init__(parent); self.setLayoutDirection(Qt.RightToLeft); self.selected_product_id=None
  self.sku=QLineEdit(); self.name=QLineEdit(); self.barcode=QLineEdit(); self.category=QComboBox(); self.purchase=QDoubleSpinBox(); self.purchase.setMaximum(999999999); self.sale=QDoubleSpinBox(); self.sale.setMaximum(999999999); self.minimum=QDoubleSpinBox(); self.minimum.setMaximum(999999999); self.minimum.setDecimals(3); self.search=QLineEdit(); self.search.setPlaceholderText("بحث بالاسم أو الرمز أو الباركود..."); self.table=QTableWidget(0,7); self.table.setHorizontalHeaderLabels(["الرمز","اسم الصنف","التصنيف","الشراء","البيع","الحد الأدنى","الحالة"]); self.table.setEditTriggers(QTableWidget.NoEditTriggers); self.table.setSelectionBehavior(QTableWidget.SelectRows); self.table.itemSelectionChanged.connect(self.load_selected); self._build(); self.refresh()
 def _build(self):
  root=QVBoxLayout(self); form=QFormLayout(); form.addRow("الرمز / SKU",self.sku); form.addRow("اسم الصنف",self.name); form.addRow("الباركود",self.barcode); form.addRow("التصنيف",self.category); form.addRow("سعر الشراء",self.purchase); form.addRow("سعر البيع",self.sale); form.addRow("الحد الأدنى للمخزون",self.minimum); root.addLayout(form); buttons=QHBoxLayout()
  for text,slot in [("حفظ الصنف",self.save_product),("وحدات وعبوات الصنف",self.open_units),("تفعيل / إيقاف",self.toggle_product),("جديد",self.clear_form),("تحديث",self.refresh)]: b=QPushButton(text); b.clicked.connect(slot); buttons.addWidget(b)
  buttons.addWidget(self.search,1); self.search.textChanged.connect(self.refresh); root.addLayout(buttons); root.addWidget(self.table,1)
 def _default_unit_id(self,s):
  u=s.scalar(select(Unit).where(Unit.is_active.is_(True)).order_by(Unit.id).limit(1));
  if u:return u.id
  u=Unit(name="قطعة",symbol="قطعة",is_active=True); s.add(u); s.flush(); return u.id
 def _load_categories(self,s):
  cur=self.category.currentData(); self.category.clear(); self.category.addItem("بدون تصنيف",None)
  for x in s.scalars(select(Category).where(Category.is_active.is_(True)).order_by(Category.name)).all(): self.category.addItem(x.name,x.id)
  if cur is not None:
   i=self.category.findData(cur)
   if i>=0:self.category.setCurrentIndex(i)
 def save_product(self):
  sku,name=self.sku.text().strip(),self.name.text().strip(); barcode=self.barcode.text().strip()
  if not sku or not name: QMessageBox.warning(self,"بيانات ناقصة","أدخل رمز الصنف واسم الصنف."); return
  s=get_session()
  try:
   p=s.get(Product,self.selected_product_id) if self.selected_product_id else None; dup=s.scalar(select(Product).where(Product.sku==sku,Product.id!=(p.id if p else -1)))
   if dup: QMessageBox.warning(self,"رمز مكرر","رمز الصنف مستخدم بالفعل."); return
   if barcode and s.scalar(select(ProductBarcode).where(ProductBarcode.barcode==barcode,ProductBarcode.product_id!=(p.id if p else -1))): QMessageBox.warning(self,"باركود مكرر","الباركود مستخدم لصنف آخر."); return
   if p is None: p=Product(sku=sku,name=name,default_unit_id=self._default_unit_id(s),category_id=self.category.currentData(),purchase_price=Decimal(str(self.purchase.value())),sale_price=Decimal(str(self.sale.value())),minimum_stock=Decimal(str(self.minimum.value())),reorder_level=Decimal(str(self.minimum.value())),is_active=True); s.add(p); s.flush()
   else: p.sku=sku; p.name=name; p.category_id=self.category.currentData(); p.purchase_price=Decimal(str(self.purchase.value())); p.sale_price=Decimal(str(self.sale.value())); p.minimum_stock=Decimal(str(self.minimum.value())); p.reorder_level=Decimal(str(self.minimum.value()))
   if barcode:
    e=s.scalar(select(ProductBarcode).where(ProductBarcode.product_id==p.id,ProductBarcode.barcode==barcode)); e= e or ProductBarcode(product_id=p.id,barcode=barcode,barcode_type="EAN",is_primary=True,is_active=True); e.is_active=True; e.is_primary=True; s.add(e) if e.id is None else None
   s.commit(); self.clear_form(); self.refresh()
  except Exception as e: s.rollback(); QMessageBox.critical(self,"تعذر الحفظ",str(e))
  finally:s.close()
 def open_units(self):
  if self.selected_product_id is None: QMessageBox.warning(self,"اختيار مطلوب","حدد الصنف أولًا ثم افتح وحداته وعبواته."); return
  ProductUnitsDialog(self.selected_product_id,self).exec()
 def load_selected(self):
  r=self.table.currentRow()
  if r<0:return
  pid=self.table.item(r,0).data(Qt.UserRole); s=get_session()
  try:
   p=s.get(Product,pid)
   if not p:return
   self.selected_product_id=p.id; self.sku.setText(p.sku); self.name.setText(p.name); self.category.setCurrentIndex(max(0,self.category.findData(p.category_id))); self.purchase.setValue(float(p.purchase_price or 0)); self.sale.setValue(float(p.sale_price or 0)); self.minimum.setValue(float(p.minimum_stock or 0)); c=s.scalar(select(ProductBarcode).where(ProductBarcode.product_id==p.id,ProductBarcode.is_active.is_(True)).order_by(ProductBarcode.is_primary.desc(),ProductBarcode.id).limit(1)); self.barcode.setText(c.barcode if c else "")
  finally:s.close()
 def toggle_product(self):
  if self.selected_product_id is None:return
  s=get_session();
  try:
   p=s.get(Product,self.selected_product_id)
   if p:p.is_active=not p.is_active;s.commit();self.clear_form();self.refresh()
  finally:s.close()
 def clear_form(self): self.selected_product_id=None; self.sku.clear(); self.name.clear(); self.barcode.clear(); self.purchase.setValue(0); self.sale.setValue(0); self.minimum.setValue(0); self.table.clearSelection()
 def refresh(self):
  s=get_session()
  try:
   self._load_categories(s); t=self.search.text().strip(); q=select(Product).order_by(Product.id.desc())
   if t:
    p=f"%{t}%"; q=q.outerjoin(ProductBarcode,ProductBarcode.product_id==Product.id).where((Product.name.ilike(p))|(Product.sku.ilike(p))|(ProductBarcode.barcode.ilike(p))).distinct()
   rows=s.scalars(q).all(); self.table.setRowCount(len(rows))
   for r,p in enumerate(rows):
    c=s.get(Category,p.category_id) if p.category_id else None; vals=[p.sku,p.name,c.name if c else "بدون تصنيف",f"{p.purchase_price:,.2f}",f"{p.sale_price:,.2f}",f"{p.minimum_stock:,.3f}","نشط" if p.is_active else "غير نشط"]
    for col,v in enumerate(vals): it=QTableWidgetItem(str(v)); it.setData(Qt.UserRole,p.id) if col==0 else None; self.table.setItem(r,col,it)
   self.table.resizeColumnsToContents()
  finally:s.close()
