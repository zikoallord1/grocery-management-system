from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from backend.app.application.business_engine import BusinessEngine
from backend.app.domain.business_events import BusinessEvent

from backend.app.core.database import get_session
from backend.app.core.models import Product, Sale, SaleItem, SalePayment
from backend.app.core.product_units import ProductUnit, SaleItemUnit
from backend.app.modules.customers.service import CustomerService
from backend.app.modules.finance.models import PaymentMethod
from backend.app.modules.finance.service import CashboxService
from backend.app.modules.inventory.service import InventoryError, InventoryService


class SaleError(Exception):
    pass


class InvalidSaleError(SaleError):
    pass


class DuplicateSaleError(SaleError):
    pass


def _resolve_product_unit(session, product, item):
    unit_id = item.get("unit_id")
    if unit_id is None:
        return None, Decimal("1"), None
    config = session.execute(
        select(ProductUnit).where(
            ProductUnit.product_id == product.id,
            ProductUnit.unit_id == int(unit_id),
            ProductUnit.is_active.is_(True),
        )
    ).scalar_one_or_none()
    if config is None:
        raise InvalidSaleError("الوحدة غير معرفة لهذا الصنف.")
    factor = Decimal(str(config.conversion_factor))
    if factor <= 0:
        raise InvalidSaleError("معامل تحويل الوحدة يجب أن يكون أكبر من صفر.")
    return config, factor, config.unit_id


class SaleService:
    def __init__(self, session=None, business_engine: BusinessEngine | None = None):
        self._session = session or get_session()
        self._owns_session = session is None
        self._business_engine = business_engine or BusinessEngine()

    def create_sale(self, *, document_no: str, business_date: str, items: list[dict], payments: list[dict] | None = None, idempotency_key: str, customer_id: int | None = None, created_by: int | None = None):
        session = self._session
        payments = payments or []
        if not document_no.strip():
            raise InvalidSaleError("Document number is required.")
        if not items:
            raise InvalidSaleError("Sale must contain at least one item.")
        if session.execute(select(Sale.id).where(Sale.idempotency_key == idempotency_key)).scalar_one_or_none() is not None:
            raise DuplicateSaleError("Sale already exists.")
        if session.execute(select(Sale.id).where(Sale.document_no == document_no)).scalar_one_or_none() is not None:
            raise DuplicateSaleError("Document number already exists.")

        subtotal = Decimal("0")
        normalized_items = []
        for item in items:
            product_id = int(item["product_id"])
            entered_quantity = Decimal(str(item["quantity"]))
            unit_price = Decimal(str(item["unit_price"]))
            discount = Decimal(str(item.get("discount", "0")))
            if entered_quantity <= 0:
                raise InvalidSaleError("Quantity must be greater than zero.")
            if unit_price < 0 or discount < 0:
                raise InvalidSaleError("Invalid sale values.")
            product = session.get(Product, product_id)
            if product is None:
                raise InvalidSaleError(f"Product does not exist: {product_id}")
            config, factor, unit_id = _resolve_product_unit(session, product, item)
            base_quantity = entered_quantity * factor
            line_total = (entered_quantity * unit_price) - discount
            if line_total < 0:
                raise InvalidSaleError("Line total cannot be negative.")
            subtotal += line_total
            normalized_items.append({"product": product, "entered_quantity": entered_quantity, "base_quantity": base_quantity, "factor": factor, "unit_id": unit_id, "unit_config": config, "unit_price": unit_price, "discount": discount, "total": line_total, "cost_price_snapshot": Decimal(str(product.purchase_price)), "stock_location_id": int(item["stock_location_id"])})

        total = subtotal
        paid_amount = Decimal("0")
        normalized_payments = []
        for payment in payments:
            method_code = str(payment["payment_method"]).strip()
            amount = Decimal(str(payment["amount"]))
            if method_code == "CREDIT":
                raise InvalidSaleError("CREDIT is represented by customer credit, not a cash payment entry.")
            if amount <= 0:
                raise InvalidSaleError("Payment amount must be greater than zero.")
            method = session.execute(select(PaymentMethod).where(PaymentMethod.code == method_code, PaymentMethod.is_active.is_(True))).scalar_one_or_none()
            if method is None:
                raise InvalidSaleError(f"Payment method does not exist: {method_code}")
            if method.cashbox_id is None:
                raise InvalidSaleError(f"Payment method is not linked to a financial account: {method_code}")
            paid_amount += amount
            normalized_payments.append({"method": method, "amount": amount, "currency": str(payment.get("currency", "BASE")), "reference_no": payment.get("reference_no")})
        if paid_amount > total:
            raise InvalidSaleError(f"Payment exceeds sale total: total={total}, paid={paid_amount}")
        credit_amount = total - paid_amount
        if credit_amount > 0 and customer_id is None:
            raise InvalidSaleError("Customer is required for credit sales.")
        if customer_id is not None:
            from backend.app.core.models import Customer
            customer = session.get(Customer, customer_id)
            if customer is None or not customer.is_active:
                raise InvalidSaleError("Customer does not exist or is inactive.")
        payment_status = "PAID" if credit_amount == 0 else "PARTIAL" if paid_amount > 0 else "CREDIT"
        sale = Sale(document_no=document_no, customer_id=customer_id, business_date=business_date, subtotal=subtotal, discount=Decimal("0"), tax=Decimal("0"), total=total, paid_amount=paid_amount, credit_amount=credit_amount, status="CONFIRMED", payment_status=payment_status, idempotency_key=idempotency_key, created_by=created_by)
        session.add(sale)
        session.flush()
        inventory = InventoryService(session)
        try:
            for item in normalized_items:
                sale_item = SaleItem(sale_id=sale.id, product_id=item["product"].id, quantity=item["entered_quantity"], unit_price=item["unit_price"], discount=item["discount"], total=item["total"], cost_price_snapshot=item["cost_price_snapshot"])
                session.add(sale_item)
                session.flush()
                inventory.remove_stock(product_id=item["product"].id, stock_location_id=item["stock_location_id"], quantity=item["base_quantity"], unit_cost=item["cost_price_snapshot"], business_date=business_date, idempotency_key=f"{idempotency_key}:stock:{item['product'].id}", reference_type="SALE", reference_id=str(sale.id), created_by=created_by)
                if item["unit_id"] is not None:
                    config = item["unit_config"]
                    session.add(SaleItemUnit(sale_item_id=sale_item.id, unit_id=item["unit_id"], entered_quantity=item["entered_quantity"], conversion_factor=item["factor"], base_quantity=item["base_quantity"], unit_name_snapshot=(session.get(__import__('backend.app.core.models', fromlist=['Unit']).Unit, item['unit_id']).name), unit_symbol_snapshot=(session.get(__import__('backend.app.core.models', fromlist=['Unit']).Unit, item['unit_id']).symbol)))

            cashbox = CashboxService(session)
            for index, payment in enumerate(normalized_payments):
                session.add(SalePayment(sale_id=sale.id, payment_method=payment["method"].code, amount=payment["amount"], currency=payment["currency"], reference_no=payment["reference_no"]))
                cashbox.move_money(cashbox_id=payment["method"].cashbox_id, amount=payment["amount"], direction="IN", movement_type="SALE_RECEIPT", business_date=business_date, idempotency_key=f"{idempotency_key}:cashbox:{index}", reference_type="SALE", reference_id=str(sale.id), created_by=created_by)
            if credit_amount > 0:
                CustomerService(session).register_sale_credit(customer_id=customer_id, amount=credit_amount, business_date=business_date, reference_id=str(sale.id), idempotency_key=f"{idempotency_key}:customer-credit", created_by=created_by)
            session.flush()
            if self._business_engine is not None:
                self._business_engine.process(session, BusinessEvent(event_type="SALE_CONFIRMED", operation_id=idempotency_key, business_date=(__import__("datetime").date.fromisoformat(business_date) if isinstance(business_date, str) else business_date), payload={"entity_type":"SALE","entity_id":sale.id,"created_by":created_by,"sale_id":sale.id,"document_no":sale.document_no,"customer_id":sale.customer_id,"subtotal":str(sale.subtotal),"total":str(sale.total),"paid_amount":str(sale.paid_amount),"credit_amount":str(sale.credit_amount),"payment_status":sale.payment_status}))
            if self._owns_session:
                session.commit()
            return sale
        except (InventoryError, InvalidSaleError):
            if self._owns_session:
                session.rollback()
            raise
        except IntegrityError as exc:
            if self._owns_session:
                session.rollback()
            raise SaleError("Sale transaction failed.") from exc
