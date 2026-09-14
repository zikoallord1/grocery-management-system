from datetime import date
from decimal import Decimal
from uuid import uuid4

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPageSize, QTextDocument
from PySide6.QtPrintSupport import QPrintPreviewDialog, QPrinter
from PySide6.QtWidgets import QComboBox, QDoubleSpinBox, QFormLayout, QHBoxLayout, QLabel, QMessageBox, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget
from sqlalchemy import select

from backend.app.core.database import get_session
from backend.app.core.models import Product, Purchase, PurchaseItem, StockLocation, Supplier
from backend.app.modules.finance.models import PaymentMethod
from backend.app.modules.purchases.service import PurchaseService


class PurchasesPage(QWidget):
    back_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent); self.setLayoutDirection(Qt.RightToLeft)
        self.product=QComboBox(); self.supplier=QComboBox(); self.location=QComboBox(); self.payment_method=QComboBox()
        self.quantity=QDoubleSpinBox(); self.quantity.setDecimals(3); self.quantity.setMinimum(0.001); self.quantity.setMaximum(999999999)
        self.unit_cost=QDoubleSpinBox(); self.unit_cost.setDecimals(2); self.unit_cost.setMaximum(999999999)
        self.payment=QDoubleSpinBox(); self.payment.setDecimals(2); self.payment.setMaximum(999999999)
        self.document_no=QLabel(); self.total=QLabel("0.00")
        self.history=QTableWidget(0,7); self.history.setHorizontalHeaderLabels(["التاريخ","رقم الفاتورة","المورد","الصنف","الكمية","الإجمالي","الحالة"]); self.history.setEditTriggers(QTableWidget.NoEditTriggers)
        self._build(); self.refresh()

    def _build(self):
        root=QVBoxLayout(self); title=QLabel("المشتريات"); title.setObjectName("pageTitle"); root.addWidget(title); root.addWidget(QLabel("إدخال فاتورة شراء وربطها تلقائيًا بالمخزون والمورد والصندوق."))
        form=QFormLayout(); form.addRow("رقم الفاتورة",self.document_no); form.addRow("المورد",self.supplier); form.addRow("الصنف",self.product); form.addRow("المخزن",self.location); form.addRow("الكمية",self.quantity); form.addRow("تكلفة الوحدة",self.unit_cost); form.addRow("وسيلة الدفع",self.payment_method); form.addRow("المدفوع الآن",self.payment); form.addRow("إجمالي الفاتورة",self.total); root.addLayout(form)
        buttons=QHBoxLayout(); save=QPushButton("حفظ وتأكيد فاتورة الشراء"); save.setObjectName("primaryButton"); save.clicked.connect(self.save_purchase); preview=QPushButton("معاينة/طباعة الفاتورة المحددة"); preview.clicked.connect(self.preview_selected); refresh=QPushButton("تحديث"); refresh.clicked.connect(self.refresh); back=QPushButton("العودة إلى الرئيسية"); back.setObjectName("secondaryButton"); back.clicked.connect(self.back_requested.emit); buttons.addWidget(save); buttons.addWidget(preview); buttons.addWidget(refresh); buttons.addStretch(); buttons.addWidget(back); root.addLayout(buttons)
        root.addWidget(QLabel("آخر فواتير الشراء")); root.addWidget(self.history,1); self.product.currentIndexChanged.connect(self._product_changed); self.quantity.valueChanged.connect(self._update_total); self.unit_cost.valueChanged.connect(self._update_total)

    def _product_changed(self):
        session=get_session()
        try:
            product=session.get(Product,self.product.currentData()) if self.product.currentData() else None
            if product: self.unit_cost.setValue(float(product.purchase_price or 0))
        finally: session.close()
        self._update_total()

    def _update_total(self): self.total.setText(f"{self.quantity.value()*self.unit_cost.value():,.2f}")

    def _load_selectors(self,session):
        self.product.clear()
        for p in session.scalars(select(Product).where(Product.is_active.is_(True)).order_by(Product.name)).all(): self.product.addItem(f"{p.sku} — {p.name}",p.id)
        self.supplier.clear(); self.supplier.addItem("بدون مورد محدد / شراء نقدي",None)
        for s in session.scalars(select(Supplier).where(Supplier.is_active.is_(True)).order_by(Supplier.name)).all(): self.supplier.addItem(f"{s.code} — {s.name}",s.id)
        self.location.clear()
        for location in session.scalars(select(StockLocation).where(StockLocation.is_active.is_(True)).order_by(StockLocation.name)).all(): self.location.addItem(f"{location.code} — {location.name}",location.id)
        self.payment_method.clear(); self.payment_method.addItem("بدون دفع / آجل",None)
        for method in session.scalars(select(PaymentMethod).where(PaymentMethod.is_active.is_(True)).order_by(PaymentMethod.code)).all(): self.payment_method.addItem(f"{method.code} — {method.name}",method.code)

    def save_purchase(self):
        product_id=self.product.currentData(); location_id=self.location.currentData(); supplier_id=self.supplier.currentData()
        if product_id is None or location_id is None: QMessageBox.warning(self,"بيانات ناقصة","اختر الصنف والمخزن أولاً."); return
        total=Decimal(str(self.quantity.value()*self.unit_cost.value())).quantize(Decimal("0.01")); paid=Decimal(str(self.payment.value())).quantize(Decimal("0.01"))
        if total<=0: QMessageBox.warning(self,"قيمة غير صحيحة","يجب أن تكون قيمة الفاتورة أكبر من صفر."); return
        if paid>total: QMessageBox.warning(self,"مبلغ غير صحيح","المدفوع لا يمكن أن يتجاوز إجمالي الفاتورة."); return
        if paid<total and supplier_id is None: QMessageBox.warning(self,"المورد مطلوب","الفاتورة الآجلة أو الجزئية تحتاج إلى مورد."); return
        method=self.payment_method.currentData()
        if paid>0 and method is None: QMessageBox.warning(self,"وسيلة الدفع مطلوبة","اختر وسيلة الدفع للمبلغ المدفوع."); return
        session=get_session()
        try:
            document_no=f"P-{date.today().strftime('%Y%m%d')}-{uuid4().hex[:8].upper()}"
            PurchaseService(session).create_purchase(document_no=document_no,business_date=date.today().isoformat(),supplier_id=supplier_id,items=[{"product_id":product_id,"quantity":Decimal(str(self.quantity.value())),"unit_cost":Decimal(str(self.unit_cost.value())),"discount":Decimal("0"),"stock_location_id":location_id}],payments=([{"payment_method":method,"amount":paid,"currency":"BASE"}] if paid>0 else []),idempotency_key=str(uuid4()))
            session.commit(); QMessageBox.information(self,"تم الحفظ",f"تم تأكيد فاتورة الشراء {document_no} وربطها بالمخزون."); self.quantity.setValue(0); self.payment.setValue(0); self.refresh()
        except Exception as exc: session.rollback(); QMessageBox.critical(self,"تعذر الحفظ",str(exc))
        finally: session.close()

    def refresh(self):
        session=get_session()
        try:
            self._load_selectors(session); rows=session.execute(select(Purchase,Supplier,Product,PurchaseItem.quantity).outerjoin(Supplier,Supplier.id==Purchase.supplier_id).join(PurchaseItem,PurchaseItem.purchase_id==Purchase.id).join(Product,Product.id==PurchaseItem.product_id).order_by(Purchase.id.desc()).limit(100)).all(); self.history.setRowCount(len(rows))
            for r,(purchase,supplier,product,quantity) in enumerate(rows):
                for c,value in enumerate([purchase.business_date,purchase.document_no,supplier.name if supplier else "نقدي",product.name,f"{quantity:,.3f}",f"{purchase.total:,.2f}",purchase.payment_status]): self.history.setItem(r,c,QTableWidgetItem(str(value)))
            self.history.resizeColumnsToContents()
        finally: session.close()
        self.document_no.setText("سيُولد تلقائيًا عند الحفظ")

    def preview_selected(self):
        row=self.history.currentRow()
        if row<0: QMessageBox.information(self,"اختيار الفاتورة","حدد فاتورة من سجل المشتريات أولًا."); return
        document_no=self.history.item(row,1).text(); session=get_session()
        try:
            purchase=session.scalar(select(Purchase).where(Purchase.document_no==document_no))
            if purchase is None: QMessageBox.warning(self,"الفاتورة غير موجودة","تعذر العثور على الفاتورة المحددة."); return
            supplier=session.get(Supplier,purchase.supplier_id) if purchase.supplier_id else None
            lines=session.execute(select(Product.name,PurchaseItem.quantity,PurchaseItem.unit_cost,PurchaseItem.line_total).join(Product,Product.id==PurchaseItem.product_id).where(PurchaseItem.purchase_id==purchase.id)).all()
            printer=QPrinter(QPrinter.HighResolution); printer.setPageSize(QPageSize(QPageSize.A4)); preview=QPrintPreviewDialog(printer,self); preview.setWindowTitle(f"معاينة فاتورة الشراء {purchase.document_no}")
            def render(target):
                document=QTextDocument(); html=f"<html><head><meta charset='utf-8'><style>body{{font-family:Arial;direction:rtl}}h1{{text-align:center}}table{{width:100%;border-collapse:collapse}}th,td{{border:1px solid #777;padding:7px;text-align:right}}.brand{{text-align:center;margin-top:30px;font-size:11px}}</style></head><body><h1>فاتورة شراء</h1><p><b>رقم الفاتورة:</b> {purchase.document_no}<br><b>التاريخ:</b> {purchase.business_date}<br><b>المورد:</b> {supplier.name if supplier else 'نقدي'}</p><table><tr><th>الصنف</th><th>الكمية</th><th>التكلفة</th><th>الإجمالي</th></tr>{''.join(f'<tr><td>{n}</td><td>{q}</td><td>{c:,.2f}</td><td>{t:,.2f}</td></tr>' for n,q,c,t in lines)}</table><p><b>الإجمالي:</b> {purchase.total:,.2f}<br><b>المدفوع:</b> {purchase.paid_amount:,.2f}<br><b>المتبقي:</b> {purchase.credit_amount:,.2f}</p><div class='brand'>نظام إدارة البقالات<br>تصميم وتنفيذ المهندس / زكريا الحاج<br>لطلب البرنامج او تقديم المساعدة او طلب برامج اخرى التواصل على الرقم 772233564</div></body></html>"; document.setHtml(html); document.print_(target)
            preview.paintRequested.connect(render); preview.resize(900,700); preview.exec()
        finally: session.close()
