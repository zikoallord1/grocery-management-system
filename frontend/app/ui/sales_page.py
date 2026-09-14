from datetime import date
from decimal import Decimal
from uuid import uuid4

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPageSize, QTextDocument
from PySide6.QtPrintSupport import QPrintPreviewDialog, QPrinter
from PySide6.QtWidgets import QComboBox, QDoubleSpinBox, QFormLayout, QHBoxLayout, QLabel, QMessageBox, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget
from sqlalchemy import select

from backend.app.core.database import get_session
from backend.app.core.models import Customer, Product, Sale, SaleItem, StockLocation
from backend.app.modules.sales.service import SaleService


class SalesPage(QWidget):
    back_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self.product = QComboBox()
        self.quantity = QDoubleSpinBox(); self.quantity.setRange(0.001, 999999999); self.quantity.setDecimals(3); self.quantity.setValue(1)
        self.price = QDoubleSpinBox(); self.price.setRange(0, 999999999); self.price.setDecimals(2)
        self.payment = QDoubleSpinBox(); self.payment.setRange(0, 999999999); self.payment.setDecimals(2)
        self.customer = QComboBox(); self.customer.addItem("بدون عميل / بيع نقدي", None)
        self.total_label = QLabel("0.00"); self.stock_label = QLabel("-"); self.location_id = None
        self.history = QTableWidget(0, 7)
        self.history.setHorizontalHeaderLabels(["التاريخ", "رقم الفاتورة", "العميل", "الصنف", "الكمية", "الإجمالي", "الحالة"])
        self.history.setEditTriggers(QTableWidget.NoEditTriggers)
        self._build(); self.refresh_data()

    def _build(self):
        root=QVBoxLayout(self); title=QLabel("فاتورة بيع جديدة"); title.setObjectName("pageTitle"); root.addWidget(title)
        description=QLabel("اختر الصنف والكمية، وسيقوم النظام بربط الفاتورة بالمخزون والصندوق وذمم العميل عند الحاجة."); description.setWordWrap(True); description.setObjectName("pageDescription"); root.addWidget(description)
        form=QFormLayout(); form.addRow("الصنف",self.product); form.addRow("الكمية",self.quantity); form.addRow("سعر البيع",self.price); form.addRow("العميل",self.customer); form.addRow("المبلغ المدفوع",self.payment); form.addRow("الإجمالي",self.total_label); form.addRow("الرصيد المتاح",self.stock_label); root.addLayout(form)
        buttons=QHBoxLayout(); save=QPushButton("حفظ وتأكيد الفاتورة"); save.setObjectName("primaryButton"); save.clicked.connect(self.create_sale); preview=QPushButton("معاينة/طباعة الفاتورة المحددة"); preview.clicked.connect(self.preview_selected); refresh=QPushButton("تحديث الأصناف"); refresh.clicked.connect(self.refresh_data); back=QPushButton("العودة إلى الرئيسية"); back.setObjectName("secondaryButton"); back.clicked.connect(self.back_requested.emit); buttons.addWidget(save); buttons.addWidget(preview); buttons.addWidget(refresh); buttons.addWidget(back); root.addLayout(buttons)
        root.addWidget(QLabel("آخر فواتير البيع")); root.addWidget(self.history,1)
        self.product.currentIndexChanged.connect(self.product_changed); self.quantity.valueChanged.connect(self.recalculate); self.price.valueChanged.connect(self.recalculate); self.payment.valueChanged.connect(self.recalculate)

    def refresh_data(self):
        session=get_session()
        try:
            self.product.blockSignals(True); self.product.clear()
            for product in session.scalars(select(Product).where(Product.is_active.is_(True)).order_by(Product.name)).all(): self.product.addItem(f"{product.name} — {product.sku}",product.id)
            self.product.blockSignals(False)
            current=self.customer.currentData(); self.customer.blockSignals(True); self.customer.clear(); self.customer.addItem("بدون عميل / بيع نقدي",None)
            for customer in session.scalars(select(Customer).where(Customer.is_active.is_(True)).order_by(Customer.name)).all(): self.customer.addItem(f"{customer.name} — {customer.code}",customer.id)
            if current is not None:
                idx=self.customer.findData(current)
                if idx>=0: self.customer.setCurrentIndex(idx)
            self.customer.blockSignals(False)
            location=session.scalar(select(StockLocation).where(StockLocation.is_active.is_(True)).order_by(StockLocation.id).limit(1)); self.location_id=location.id if location else None
            rows=session.execute(select(Sale,Customer,Product,SaleItem.quantity).outerjoin(Customer,Customer.id==Sale.customer_id).join(SaleItem,SaleItem.sale_id==Sale.id).join(Product,Product.id==SaleItem.product_id).order_by(Sale.id.desc()).limit(100)).all()
            self.history.setRowCount(len(rows))
            for r,(sale,customer,product,quantity) in enumerate(rows):
                values=[sale.business_date,sale.document_no,customer.name if customer else "نقدي",product.name,f"{quantity:,.3f}",f"{sale.total:,.2f}",sale.payment_status]
                for c,value in enumerate(values): self.history.setItem(r,c,QTableWidgetItem(str(value)))
            self.history.resizeColumnsToContents(); self.product_changed()
        finally: session.close()

    def product_changed(self):
        session=get_session()
        try:
            product=session.get(Product,self.product.currentData()) if self.product.currentData() else None
            if product is None: self.price.setValue(0); self.stock_label.setText("لا يوجد"); self.recalculate(); return
            self.price.setValue(float(product.sale_price))
            if self.location_id is not None:
                from backend.app.modules.inventory.service import InventoryService
                self.stock_label.setText(f"{InventoryService(session).get_balance(product.id,self.location_id):,.3f}")
            else: self.stock_label.setText("لم يتم إعداد مخزن")
            self.recalculate()
        finally: session.close()

    def recalculate(self):
        total=Decimal(str(self.quantity.value()))*Decimal(str(self.price.value())); self.total_label.setText(f"{total:,.2f}")
        if self.payment.value()==0 and total>0: self.payment.setValue(float(total))

    def create_sale(self):
        if self.product.currentData() is None: QMessageBox.warning(self,"بيانات ناقصة","أضف صنفًا أولًا من شاشة المخزون."); return
        if self.location_id is None: QMessageBox.warning(self,"المخزون غير مهيأ","لا يوجد موقع مخزون نشط."); return
        total=Decimal(str(self.quantity.value()))*Decimal(str(self.price.value())); paid=Decimal(str(self.payment.value()))
        if paid>total: QMessageBox.warning(self,"مبلغ غير صحيح","المبلغ المدفوع لا يمكن أن يتجاوز إجمالي الفاتورة."); return
        if paid<total and self.customer.currentData() is None: QMessageBox.warning(self,"العميل مطلوب","البيع الآجل أو الجزئي يتطلب اختيار عميل."); return
        session=get_session()
        try:
            sale=SaleService(session).create_sale(document_no=f"S-{date.today().strftime('%Y%m%d')}-{uuid4().hex[:8].upper()}",business_date=date.today().isoformat(),customer_id=self.customer.currentData(),items=[{"product_id":self.product.currentData(),"stock_location_id":self.location_id,"quantity":str(self.quantity.value()),"unit_price":str(self.price.value()),"discount":"0"}],payments=[{"payment_method":"CASH","amount":str(paid)}] if paid>0 else [],idempotency_key=str(uuid4()))
            session.commit(); QMessageBox.information(self,"تم الحفظ",f"تم تأكيد فاتورة البيع رقم {sale.document_no} بإجمالي {sale.total:,.2f}."); self.payment.setValue(float(total)); self.refresh_data()
        except Exception as exc: session.rollback(); QMessageBox.critical(self,"تعذر حفظ الفاتورة",str(exc))
        finally: session.close()

    def preview_selected(self):
        row = self.history.currentRow()
        if row < 0:
            QMessageBox.information(self, "اختيار الفاتورة", "حدد فاتورة من سجل المبيعات أولًا.")
            return
        document_no = self.history.item(row, 1).text()
        session = get_session()
        try:
            sale = session.scalar(select(Sale).where(Sale.document_no == document_no))
            if sale is None:
                QMessageBox.warning(self, "الفاتورة غير موجودة", "تعذر العثور على الفاتورة المحددة.")
                return
            customer = session.get(Customer, sale.customer_id) if sale.customer_id else None
            lines = session.execute(select(Product.name, SaleItem.quantity, SaleItem.unit_price, SaleItem.line_total).join(Product, Product.id == SaleItem.product_id).where(SaleItem.sale_id == sale.id)).all()
            rows = [(name, f"{quantity:,.3f}", unit_price, line_total) for name, quantity, unit_price, line_total in lines]
            printer = QPrinter(QPrinter.HighResolution); printer.setPageSize(QPageSize(QPageSize.A4))
            preview = QPrintPreviewDialog(printer, self); preview.setWindowTitle(f"معاينة فاتورة البيع {sale.document_no}")
            def render(target):
                document = QTextDocument()
                html = f"<html><head><meta charset='utf-8'><style>body{{font-family:Arial;direction:rtl}}h1{{text-align:center}}table{{width:100%;border-collapse:collapse}}th,td{{border:1px solid #777;padding:7px;text-align:right}}.brand{{text-align:center;margin-top:30px;font-size:11px}}</style></head><body><h1>فاتورة بيع</h1><p><b>رقم الفاتورة:</b> {sale.document_no}<br><b>التاريخ:</b> {sale.business_date}<br><b>العميل:</b> {customer.name if customer else 'نقدي'}</p><table><tr><th>الصنف</th><th>الكمية</th><th>السعر</th><th>الإجمالي</th></tr>{''.join(f'<tr><td>{n}</td><td>{q}</td><td>{p:,.2f}</td><td>{t:,.2f}</td></tr>' for n,q,p,t in rows)}</table><p><b>الإجمالي:</b> {sale.total:,.2f}<br><b>المدفوع:</b> {sale.paid_amount:,.2f}<br><b>المتبقي:</b> {sale.credit_amount:,.2f}</p><div class='brand'>نظام إدارة البقالات<br>تصميم وتنفيذ المهندس / زكريا الحاج<br>لطلب البرنامج او تقديم المساعدة او طلب برامج اخرى التواصل على الرقم 772233564</div></body></html>"
                document.setHtml(html); document.print_(target)
            preview.paintRequested.connect(render); preview.resize(900, 700); preview.exec()
        finally:
            session.close()
