from datetime import date
from decimal import Decimal

from sqlalchemy import func, select

from backend.app.application.business_engine import BusinessEngine
from backend.app.domain.business_events import BusinessEvent
from backend.app.core.database import get_session
from backend.app.core.models import (
    CustomerAccountMovement,
    Purchase,
    PurchaseItem,
    Sale,
    SaleItem,
    StockMovement,
    SupplierAccountMovement,
)
from backend.app.modules.finance.models import PaymentMethod
from backend.app.modules.finance.service import CashboxService
from backend.app.modules.inventory.service import InventoryService
from backend.app.modules.returns.models import (
    PurchaseReturn,
    PurchaseReturnItem,
    SaleReturn,
    SaleReturnItem,
)
from backend.app.core.operation_guard import authorize_operation


class ReturnError(Exception):
    pass


class DuplicateReturnError(ReturnError):
    pass


class ReturnService:
    def __init__(self, session=None, business_engine=None):
        self._session = session or get_session()
        self._owns_session = session is None
        self._business_engine = business_engine or BusinessEngine()

    def _commit_or_rollback(self):
        if self._owns_session:
            self._session.commit()

    def return_sale(self, *, sale_id: int, items: list[dict], business_date: str,
                    document_no: str, refund_payment_method: str | None = None,
                    reason: str | None = None, idempotency_key: str,
                    created_by: int | None = None):
        session = self._session
        created_by = authorize_operation(
            session, operation_id=idempotency_key, module="المرتجعات",
            permission="إضافة", entity_type="SALE_RETURN",
            entity_id=str(sale_id), created_by=created_by,
        )
        if session.execute(select(SaleReturn.id).where(SaleReturn.idempotency_key == idempotency_key)).scalar_one_or_none():
            raise DuplicateReturnError("Sales return already exists.")
        if session.execute(select(SaleReturn.id).where(SaleReturn.document_no == document_no)).scalar_one_or_none():
            raise DuplicateReturnError("Return document number already exists.")
        sale = session.get(Sale, sale_id)
        if sale is None or sale.status != "CONFIRMED":
            raise ReturnError("Confirmed sale does not exist.")
        if not items:
            raise ReturnError("Return must contain at least one item.")

        normalized = []
        total = Decimal("0")
        for data in items:
            sale_item = session.get(SaleItem, int(data["sale_item_id"]))
            if sale_item is None or sale_item.sale_id != sale.id:
                raise ReturnError("Sale item does not belong to the selected sale.")
            quantity = Decimal(str(data["quantity"]))
            if quantity <= 0:
                raise ReturnError("Return quantity must be greater than zero.")
            already = session.execute(select(func.coalesce(func.sum(SaleReturnItem.quantity), 0)).where(SaleReturnItem.sale_item_id == sale_item.id)).scalar_one()
            available = Decimal(str(sale_item.quantity)) - Decimal(str(already))
            if quantity > available:
                raise ReturnError(f"Return quantity exceeds available quantity: {available}")
            line_total = (quantity * Decimal(str(sale_item.unit_price))).quantize(Decimal("0.01"))
            stock = session.execute(select(StockMovement).where(StockMovement.reference_type == "SALE", StockMovement.reference_id == str(sale.id), StockMovement.product_id == sale_item.product_id, StockMovement.direction == "OUT").order_by(StockMovement.id)).scalars().first()
            if stock is None:
                raise ReturnError("Original sale stock movement was not found.")
            normalized.append((sale_item, quantity, line_total, stock))
            total += line_total

        refunded = min(total, Decimal(str(sale.paid_amount)))
        credit_reduction = total - refunded
        if refunded > 0 and refund_payment_method is None:
            raise ReturnError("A refund payment method is required for the paid portion of the return.")
        method = None
        if refunded > 0:
            method = session.execute(select(PaymentMethod).where(PaymentMethod.code == refund_payment_method, PaymentMethod.is_active.is_(True))).scalar_one_or_none()
            if method is None or method.cashbox_id is None:
                raise ReturnError("Refund payment method does not exist or is not linked to a cashbox.")

        ret = SaleReturn(document_no=document_no, sale_id=sale.id, business_date=business_date, total=total,
                         refunded_amount=refunded, credit_reduction=credit_reduction, reason=reason,
                         idempotency_key=idempotency_key, created_by=created_by)
        session.add(ret)
        session.flush()
        inventory = InventoryService(session)
        for index, (sale_item, quantity, line_total, stock) in enumerate(normalized):
            session.add(SaleReturnItem(return_id=ret.id, sale_item_id=sale_item.id, product_id=sale_item.product_id,
                                       quantity=quantity, unit_price=sale_item.unit_price, total=line_total))
            inventory.add_stock(product_id=sale_item.product_id, stock_location_id=stock.stock_location_id,
                                quantity=quantity, unit_cost=sale_item.cost_price_snapshot, business_date=business_date,
                                idempotency_key=f"{idempotency_key}:stock:{index}", reference_type="SALE_RETURN",
                                reference_id=str(ret.id), created_by=created_by)
        if refunded > 0:
            CashboxService(session).move_money(cashbox_id=method.cashbox_id, amount=refunded, direction="OUT",
                movement_type="SALE_RETURN_REFUND", business_date=business_date, idempotency_key=f"{idempotency_key}:cashbox",
                reference_type="SALE_RETURN", reference_id=str(ret.id), created_by=created_by)
        if credit_reduction > 0:
            if sale.customer_id is None:
                raise ReturnError("Credit reduction requires a customer on the original sale.")
            session.add(CustomerAccountMovement(customer_id=sale.customer_id, movement_type="SALE_RETURN_CREDIT_REDUCTION",
                amount=credit_reduction, direction="CREDIT", currency="BASE", reference_type="SALE_RETURN",
                reference_id=str(ret.id), business_date=business_date, idempotency_key=f"{idempotency_key}:customer",
                created_by=created_by))
        self._business_engine.process(session, BusinessEvent(event_type="SALE_RETURN_CONFIRMED", operation_id=idempotency_key,
            business_date=date.fromisoformat(business_date), payload={"entity_type":"SALE_RETURN","entity_id":ret.id,"sale_id":sale.id,"total":str(total)}))
        session.flush(); self._commit_or_rollback(); return ret

    def return_purchase(self, *, purchase_id: int, items: list[dict], business_date: str,
                        document_no: str, refund_payment_method: str | None = None,
                        reason: str | None = None, idempotency_key: str,
                        created_by: int | None = None):
        session = self._session
        created_by = authorize_operation(
            session, operation_id=idempotency_key, module="المرتجعات",
            permission="إضافة", entity_type="PURCHASE_RETURN",
            entity_id=str(purchase_id), created_by=created_by,
        )
        if session.execute(select(PurchaseReturn.id).where(PurchaseReturn.idempotency_key == idempotency_key)).scalar_one_or_none():
            raise DuplicateReturnError("Purchase return already exists.")
        if session.execute(select(PurchaseReturn.id).where(PurchaseReturn.document_no == document_no)).scalar_one_or_none():
            raise DuplicateReturnError("Return document number already exists.")
        purchase = session.get(Purchase, purchase_id)
        if purchase is None or purchase.status != "CONFIRMED":
            raise ReturnError("Confirmed purchase does not exist.")
        if not items:
            raise ReturnError("Return must contain at least one item.")
        normalized=[]; total=Decimal("0")
        for data in items:
            item=session.get(PurchaseItem,int(data["purchase_item_id"]))
            if item is None or item.purchase_id != purchase.id:
                raise ReturnError("Purchase item does not belong to the selected purchase.")
            quantity=Decimal(str(data["quantity"]))
            if quantity<=0: raise ReturnError("Return quantity must be greater than zero.")
            already=session.execute(select(func.coalesce(func.sum(PurchaseReturnItem.quantity),0)).where(PurchaseReturnItem.purchase_item_id==item.id)).scalar_one()
            available=Decimal(str(item.quantity))-Decimal(str(already))
            if quantity>available: raise ReturnError(f"Return quantity exceeds available quantity: {available}")
            line_total=(quantity*Decimal(str(item.unit_cost))).quantize(Decimal("0.01"))
            stock=session.execute(select(StockMovement).where(StockMovement.reference_type=="PURCHASE",StockMovement.reference_id==str(purchase.id),StockMovement.product_id==item.product_id,StockMovement.direction=="IN").order_by(StockMovement.id)).scalars().first()
            if stock is None: raise ReturnError("Original purchase stock movement was not found.")
            normalized.append((item,quantity,line_total,stock)); total+=line_total
        refunded=min(total,Decimal(str(purchase.paid_amount))); credit_reduction=total-refunded
        if refunded>0 and refund_payment_method is None: raise ReturnError("A refund payment method is required for the paid portion of the return.")
        method=None
        if refunded>0:
            method=session.execute(select(PaymentMethod).where(PaymentMethod.code==refund_payment_method,PaymentMethod.is_active.is_(True))).scalar_one_or_none()
            if method is None or method.cashbox_id is None: raise ReturnError("Refund payment method does not exist or is not linked to a cashbox.")
        ret=PurchaseReturn(document_no=document_no,purchase_id=purchase.id,business_date=business_date,total=total,refunded_amount=refunded,credit_reduction=credit_reduction,reason=reason,idempotency_key=idempotency_key,created_by=created_by)
        session.add(ret); session.flush(); inventory=InventoryService(session)
        for index,(item,quantity,line_total,stock) in enumerate(normalized):
            session.add(PurchaseReturnItem(return_id=ret.id,purchase_item_id=item.id,product_id=item.product_id,quantity=quantity,unit_cost=item.unit_cost,total=line_total))
            inventory.remove_stock(product_id=item.product_id,stock_location_id=stock.stock_location_id,quantity=quantity,unit_cost=item.unit_cost,business_date=business_date,idempotency_key=f"{idempotency_key}:stock:{index}",reference_type="PURCHASE_RETURN",reference_id=str(ret.id),created_by=created_by)
        if refunded>0:
            CashboxService(session).move_money(cashbox_id=method.cashbox_id,amount=refunded,direction="IN",movement_type="PURCHASE_RETURN_REFUND",business_date=business_date,idempotency_key=f"{idempotency_key}:cashbox",reference_type="PURCHASE_RETURN",reference_id=str(ret.id),created_by=created_by)
        if credit_reduction>0:
            if purchase.supplier_id is None: raise ReturnError("Credit reduction requires a supplier on the original purchase.")
            session.add(SupplierAccountMovement(supplier_id=purchase.supplier_id,movement_type="PURCHASE_RETURN_CREDIT_REDUCTION",amount=credit_reduction,direction="DEBIT",currency="BASE",reference_type="PURCHASE_RETURN",reference_id=str(ret.id),business_date=business_date,idempotency_key=f"{idempotency_key}:supplier",created_by=created_by))
        self._business_engine.process(session,BusinessEvent(event_type="PURCHASE_RETURN_CONFIRMED",operation_id=idempotency_key,business_date=date.fromisoformat(business_date),payload={"entity_type":"PURCHASE_RETURN","entity_id":ret.id,"purchase_id":purchase.id,"total":str(total)}))
        session.flush(); self._commit_or_rollback(); return ret
