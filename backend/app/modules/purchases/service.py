from decimal import Decimal

from sqlalchemy import select

from backend.app.application.business_engine import BusinessEngine
from backend.app.domain.business_events import BusinessEvent

from backend.app.core.database import get_session
from backend.app.core.models import (
    Product,
    Purchase,
    PurchaseItem,
    PurchasePayment,
    Supplier,
)
from backend.app.modules.finance.models import PaymentMethod
from backend.app.modules.finance.service import CashboxService
from backend.app.modules.inventory.service import InventoryService
from backend.app.modules.suppliers.service import SupplierService


class PurchaseError(Exception):
    pass


class DuplicatePurchaseError(PurchaseError):
    pass


class PurchaseService:
    def __init__(
        self,
        session=None,
        business_engine: BusinessEngine | None = None,
    ):
        self._session = session or get_session()
        self._owns_session = session is None
        self._business_engine = business_engine or BusinessEngine()

    def create_purchase(
        self,
        *,
        document_no: str,
        business_date: str,
        items: list[dict],
        payments: list[dict] | None = None,
        idempotency_key: str,
        supplier_id: int | None = None,
        created_by: int | None = None,
    ):
        session = self._session
        payments = payments or []

        if not document_no.strip():
            raise PurchaseError("Document number is required.")

        if not items:
            raise PurchaseError("Purchase must contain at least one item.")

        if session.execute(
            select(Purchase.id).where(
                Purchase.idempotency_key == idempotency_key
            )
        ).scalar_one_or_none() is not None:
            raise DuplicatePurchaseError("Purchase already exists.")

        if session.execute(
            select(Purchase.id).where(
                Purchase.document_no == document_no
            )
        ).scalar_one_or_none() is not None:
            raise DuplicatePurchaseError("Document number already exists.")

        if supplier_id is not None:
            supplier = session.get(Supplier, supplier_id)
            if supplier is None or not supplier.is_active:
                raise PurchaseError(
                    "Supplier does not exist or is inactive."
                )

        normalized = []
        subtotal = Decimal("0")

        for item in items:
            product = session.get(Product, int(item["product_id"]))

            if product is None:
                raise PurchaseError("Product does not exist.")

            quantity = Decimal(str(item["quantity"]))
            unit_cost = Decimal(str(item["unit_cost"]))
            discount = Decimal(str(item.get("discount", "0")))

            if quantity <= 0:
                raise PurchaseError(
                    "Quantity must be greater than zero."
                )

            if unit_cost < 0 or discount < 0:
                raise PurchaseError("Invalid purchase values.")

            line_total = (quantity * unit_cost) - discount

            if line_total < 0:
                raise PurchaseError(
                    "Line total cannot be negative."
                )

            subtotal += line_total

            normalized.append(
                {
                    "product": product,
                    "quantity": quantity,
                    "unit_cost": unit_cost,
                    "discount": discount,
                    "total": line_total,
                    "stock_location_id": int(
                        item["stock_location_id"]
                    ),
                }
            )

        total = subtotal
        paid_amount = Decimal("0")
        normalized_payments = []

        for payment in payments:
            method_code = str(payment["payment_method"]).strip()

            if method_code == "CREDIT":
                raise PurchaseError(
                    "CREDIT is represented by supplier credit."
                )

            amount = Decimal(str(payment["amount"]))

            if amount <= 0:
                raise PurchaseError(
                    "Payment amount must be greater than zero."
                )

            method = session.execute(
                select(PaymentMethod).where(
                    PaymentMethod.code == method_code,
                    PaymentMethod.is_active.is_(True),
                )
            ).scalar_one_or_none()

            if method is None:
                raise PurchaseError(
                    f"Payment method does not exist: {method_code}"
                )

            if method.cashbox_id is None:
                raise PurchaseError(
                    f"Payment method is not linked to a financial account: {method_code}"
                )

            paid_amount += amount

            normalized_payments.append(
                {
                    "method": method,
                    "amount": amount,
                    "currency": str(
                        payment.get("currency", "BASE")
                    ),
                    "reference_no": payment.get("reference_no"),
                }
            )

        if paid_amount > total:
            raise PurchaseError(
                "Payment exceeds purchase total."
            )

        credit_amount = total - paid_amount

        if credit_amount > 0 and supplier_id is None:
            raise PurchaseError(
                "Supplier is required for credit purchases."
            )

        payment_status = (
            "PAID"
            if credit_amount == 0
            else "PARTIAL"
            if paid_amount > 0
            else "CREDIT"
        )

        purchase = Purchase(
            document_no=document_no,
            supplier_id=supplier_id,
            business_date=business_date,
            subtotal=subtotal,
            discount=Decimal("0"),
            tax=Decimal("0"),
            total=total,
            paid_amount=paid_amount,
            credit_amount=credit_amount,
            status="CONFIRMED",
            payment_status=payment_status,
            idempotency_key=idempotency_key,
            created_by=created_by,
        )

        session.add(purchase)
        session.flush()

        inventory = InventoryService(session)

        try:
            for item in normalized:
                session.add(
                    PurchaseItem(
                        purchase_id=purchase.id,
                        product_id=item["product"].id,
                        quantity=item["quantity"],
                        unit_cost=item["unit_cost"],
                        discount=item["discount"],
                        total=item["total"],
                    )
                )

                inventory.add_stock(
                    product_id=item["product"].id,
                    stock_location_id=item["stock_location_id"],
                    quantity=item["quantity"],
                    unit_cost=item["unit_cost"],
                    business_date=business_date,
                    idempotency_key=(
                        f"{idempotency_key}:stock:{item['product'].id}"
                    ),
                    reference_type="PURCHASE",
                    reference_id=str(purchase.id),
                    created_by=created_by,
                )

            cashbox = CashboxService(session)

            for index, payment in enumerate(normalized_payments):
                session.add(
                    PurchasePayment(
                        purchase_id=purchase.id,
                        payment_method=payment["method"].code,
                        amount=payment["amount"],
                        currency=payment["currency"],
                        reference_no=payment["reference_no"],
                    )
                )

                cashbox.move_money(
                    cashbox_id=payment["method"].cashbox_id,
                    amount=payment["amount"],
                    direction="OUT",
                    movement_type="PURCHASE_PAYMENT",
                    business_date=business_date,
                    idempotency_key=(
                        f"{idempotency_key}:cashbox:{index}"
                    ),
                    reference_type="PURCHASE",
                    reference_id=str(purchase.id),
                    created_by=created_by,
                )

            if credit_amount > 0:
                SupplierService(session).register_purchase_credit(
                    supplier_id=supplier_id,
                    amount=credit_amount,
                    business_date=business_date,
                    reference_id=str(purchase.id),
                    idempotency_key=(
                        f"{idempotency_key}:supplier-credit"
                    ),
                    created_by=created_by,
                )

            session.flush()

            if self._business_engine is not None:
                self._business_engine.process(
                    session,
                    BusinessEvent(
                        event_type="PURCHASE_CONFIRMED",
                        operation_id=idempotency_key,
                        business_date=(
                            __import__("datetime").date.fromisoformat(
                                business_date
                            )
                            if isinstance(business_date, str)
                            else business_date
                        ),
                        payload={
                            "entity_type": "PURCHASE",
                            "entity_id": purchase.id,
                            "created_by": created_by,
                            "purchase_id": purchase.id,
                            "document_no": purchase.document_no,
                            "supplier_id": purchase.supplier_id,
                            "subtotal": str(purchase.subtotal),
                            "total": str(purchase.total),
                            "paid_amount": str(purchase.paid_amount),
                            "credit_amount": str(purchase.credit_amount),
                            "payment_status": purchase.payment_status,
                        },
                    ),
                )

            if self._owns_session:
                session.commit()

            return purchase

        except Exception:
            if self._owns_session:
                session.rollback()
            raise
