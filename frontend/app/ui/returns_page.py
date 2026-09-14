from datetime import date
from decimal import Decimal
from uuid import uuid4

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QComboBox, QDoubleSpinBox, QFormLayout, QHBoxLayout,
    QLabel, QLineEdit, QMessageBox, QPushButton, QTableWidget, QTableWidgetItem,
    QTabWidget, QVBoxLayout, QWidget)
from sqlalchemy import select

from backend.app.core.database import get_session
from backend.app.core.models import Product, Purchase, PurchaseItem, Sale, SaleItem
from backend.app.modules.finance.models import PaymentMethod
from backend.app.modules.returns.models import PurchaseReturn, SaleReturn
from backend.app.modules.returns.service import ReturnService


class ReturnsPage(QWidget):
    back_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self.sale = QComboBox(); self.sale_item = QComboBox(); self.sale_qty = QDoubleSpinBox(); self.sale_qty.setRange(0.001, 999999999); self.sale_qty.setDecimals(3)
        self.sale_refund = QComboBox(); self.sale_reason = QLineEdit(); self.sale_doc = QLabel()
        self.purchase = QComboBox(); self.purchase_item = QComboBox(); self.purchase_qty = QDoubleSpinBox(); self.purchase_qty.setRange(0.001, 999999999); self.purchase_qty.setDecimals(3)
        self.purchase_refund = QComboBox(); self.purchase_reason = QLineEdit(); self.purchase_doc = QLabel()
        self.history = QTableWidget(0, 7)
        self.history.setHorizontalHeaderLabels(["التاريخ", "رقم المرتجع", "نوع المرتجع", "الفاتورة الأصلية", "الإجمالي", "المبلغ النقدي", "الحالة"])
        self.history.setEditTriggers(QTableWidget.NoEditTriggers)
        self._build(); self.refresh()

    def _build(self):
        root=QVBoxLayout(self); title=QLabel("المرتجعات والإلغاءات"); title.setObjectName("pageTitle"); root.addWidget(title)
        desc=QLabel("إرجاع البيع أو الشراء يعكس المخزون والحركة المالية دون حذف الفاتورة الأصلية."); desc.setWordWrap(True); desc.setObjectName("pageDescription"); root.addWidget(desc)
        tabs=QTabWidget(); tabs.addTab(self._sale_tab(), "مرتجع مبيعات"); tabs.addTab(self._purchase_tab(), "مرتجع مشتريات"); root.addWidget(tabs,1)
        root.addWidget(QLabel("سجل المرتجعات")); root.addWidget(self.history,1)
        refresh=QPushButton("تحديث البيانات"); refresh.clicked.connect(self.refresh); back=QPushButton("العودة إلى الرئيسية"); back.setObjectName("secondaryButton"); back.clicked.connect(self.back_requested.emit)
        row=QHBoxLayout(); row.addWidget(refresh); row.addStretch(); row.addWidget(back); root.addLayout(row)
        self.sale.currentIndexChanged.connect(self._load_sale_items); self.purchase.currentIndexChanged.connect(self._load_purchase_items)

    def _sale_tab(self):
        w=QWidget(); f=QFormLayout(w); f.addRow("الفاتورة الأصلية",self.sale); f.addRow("الصنف",self.sale_item); f.addRow("كمية المرتجع",self.sale_qty); f.addRow("طريقة رد المبلغ",self.sale_refund); f.addRow("سبب المرتجع",self.sale_reason); f.addRow("رقم المرتجع",self.sale_doc)
        b=QPushButton("حفظ وتأكيد مرتجع المبيعات"); b.setObjectName("primaryButton"); b.clicked.connect(self.save_sale_return); f.addRow(b); return w

    def _purchase_tab(self):
        w=QWidget(); f=QFormLayout(w); f.addRow("الفاتورة الأصلية",self.purchase); f.addRow("الصنف",self.purchase_item); f.addRow("كمية المرتجع",self.purchase_qty); f.addRow("طريقة استلام المبلغ",self.purchase_refund); f.addRow("سبب المرتجع",self.purchase_reason); f.addRow("رقم المرتجع",self.purchase_doc)
        b=QPushButton("حفظ وتأكيد مرتجع المشتريات"); b.setObjectName("primaryButton"); b.clicked.connect(self.save_purchase_return); f.addRow(b); return w

    def _payment_methods(self, combo, session):
        combo.clear(); combo.addItem("بدون رد/استلام نقدي", None)
        for m in session.scalars(select(PaymentMethod).where(PaymentMethod.is_active.is_(True)).order_by(PaymentMethod.code)).all(): combo.addItem(f"{m.code} — {m.name}", m.code)

    def refresh(self):
        session=get_session()
        try:
            self.sale.clear()
            for s in session.scalars(select(Sale).where(Sale.status=="CONFIRMED").order_by(Sale.id.desc()).limit(200)).all(): self.sale.addItem(f"{s.document_no} — {s.total:,.2f}",s.id)
            self.purchase.clear()
            for p in session.scalars(select(Purchase).where(Purchase.status=="CONFIRMED").order_by(Purchase.id.desc()).limit(200)).all(): self.purchase.addItem(f"{p.document_no} — {p.total:,.2f}",p.id)
            self._payment_methods(self.sale_refund, session); self._payment_methods(self.purchase_refund, session)
            self._load_sale_items(); self._load_purchase_items()
            sale_rows=session.execute(select(SaleReturn,Sale).join(Sale,Sale.id==SaleReturn.sale_id).order_by(SaleReturn.id.desc()).limit(100)).all()
            purchase_rows=session.execute(select(PurchaseReturn,Purchase).join(Purchase,Purchase.id==PurchaseReturn.purchase_id).order_by(PurchaseReturn.id.desc()).limit(100)).all()
            history=[]
            for ret, sale in sale_rows: history.append((ret.business_date,ret.document_no,"مرتجع مبيعات",sale.document_no,ret.total,ret.refunded_amount,ret.status,ret.id))
            for ret, purchase in purchase_rows: history.append((ret.business_date,ret.document_no,"مرتجع مشتريات",purchase.document_no,ret.total,ret.refunded_amount,ret.status,ret.id))
            history.sort(key=lambda row: row[7], reverse=True); history=history[:100]
            self.history.setRowCount(len(history))
            for r,row in enumerate(history):
                values=[row[0],row[1],row[2],row[3],f"{row[4]:,.2f}",f"{row[5]:,.2f}",row[6]]
                for c,value in enumerate(values): self.history.setItem(r,c,QTableWidgetItem(str(value)))
            self.history.resizeColumnsToContents()
        finally:
            session.close()
        self.sale_doc.setText("سيُولد تلقائيًا عند الحفظ"); self.purchase_doc.setText("سيُولد تلقائيًا عند الحفظ")

    def _load_sale_items(self):
        session=get_session()
        try:
            self.sale_item.clear(); sale_id=self.sale.currentData()
            if sale_id:
                for item in session.scalars(select(SaleItem).where(SaleItem.sale_id==sale_id).order_by(SaleItem.id)).all():
                    product=session.get(Product,item.product_id); self.sale_item.addItem(f"{product.name} — الكمية الأصلية {item.quantity}",item.id)
        finally: session.close()

    def _load_purchase_items(self):
        session=get_session()
        try:
            self.purchase_item.clear(); purchase_id=self.purchase.currentData()
            if purchase_id:
                for item in session.scalars(select(PurchaseItem).where(PurchaseItem.purchase_id==purchase_id).order_by(PurchaseItem.id)).all():
                    product=session.get(Product,item.product_id); self.purchase_item.addItem(f"{product.name} — الكمية الأصلية {item.quantity}",item.id)
        finally: session.close()

    def save_sale_return(self):
        sale_id=self.sale.currentData(); item_id=self.sale_item.currentData(); qty=Decimal(str(self.sale_qty.value()))
        if sale_id is None or item_id is None: QMessageBox.warning(self,"بيانات ناقصة","اختر الفاتورة والصنف."); return
        session=get_session()
        try:
            doc=f"SR-{date.today().strftime('%Y%m%d')}-{uuid4().hex[:8].upper()}"
            ReturnService(session).return_sale(sale_id=int(sale_id),items=[{"sale_item_id":int(item_id),"quantity":qty}],business_date=date.today().isoformat(),document_no=doc,refund_payment_method=self.sale_refund.currentData(),reason=self.sale_reason.text().strip() or None,idempotency_key=str(uuid4()))
            session.commit(); self.sale_qty.setValue(0); self.sale_reason.clear(); QMessageBox.information(self,"تم الحفظ",f"تم تأكيد مرتجع المبيعات {doc}."); self.refresh()
        except Exception as exc: session.rollback(); QMessageBox.critical(self,"تعذر الحفظ",str(exc))
        finally: session.close()

    def save_purchase_return(self):
        purchase_id=self.purchase.currentData(); item_id=self.purchase_item.currentData(); qty=Decimal(str(self.purchase_qty.value()))
        if purchase_id is None or item_id is None: QMessageBox.warning(self,"بيانات ناقصة","اختر الفاتورة والصنف."); return
        session=get_session()
        try:
            doc=f"PR-{date.today().strftime('%Y%m%d')}-{uuid4().hex[:8].upper()}"
            ReturnService(session).return_purchase(purchase_id=int(purchase_id),items=[{"purchase_item_id":int(item_id),"quantity":qty}],business_date=date.today().isoformat(),document_no=doc,refund_payment_method=self.purchase_refund.currentData(),reason=self.purchase_reason.text().strip() or None,idempotency_key=str(uuid4()))
            session.commit(); self.purchase_qty.setValue(0); self.purchase_reason.clear(); QMessageBox.information(self,"تم الحفظ",f"تم تأكيد مرتجع المشتريات {doc}."); self.refresh()
        except Exception as exc: session.rollback(); QMessageBox.critical(self,"تعذر الحفظ",str(exc))
        finally: session.close()
