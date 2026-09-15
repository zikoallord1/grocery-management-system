from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from backend.app.core.database import get_session
from backend.app.core.models import (
    Product,
    Purchase,
    PurchaseItem,
    PurchasePayment,
    Supplier,
)
from backend.app.modules.inventory.service import InventoryService
from backend.app.modules.suppliers.service import SupplierService


class PurchaseError(Exception):
    pass


class DuplicatePurchaseError(PurchaseError):
    pass


class PurchaseService:
    def __init__(self, session=None):
        self._session = session or get_session()
        self._owns_session = session is None

    def create_purchase(
        self,
        *,
        document_no: str,
        business_date: str,
        items: list[dict],
        payments: list[dict],
        idempotency_key: str,
        supplier_id: int | None = None,
        created_by: int | None = None,
    ):
        session = self._session

        if not document_no.strip():
            raise PurchaseError("Document number is required.")

        if not items:
            raise PurchaseError("Purchase must contain at least one item.")

        existing = session.execute(
            select(Purchase.id).where(
                Purchase.idempotency_key == idempotency_key
            )
        ).scalar_one_or_none()

        if existing is not None:
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
                raise PurchaseError("Supplier does not exist or is inactive.")

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
                raise PurchaseError("Quantity must be greater than zero.")

            if unit_cost < 0 or discount < 0:
                raise PurchaseError("Invalid purchase values.")

            line_total = (quantity * unit_cost) - discount

            if line_total < 0:
                raise PurchaseError("Line total cannot be negative.")

            subtotal += line_total

            normalized.append({
                "product": product,
                "quantity": quantity,
                "unit_cost": unit_cost,
                "discount": discount,
                "total": line_total,
                "stock_location_id": int(item["stock_location_id"]),
            })

        total = subtotal

        paid = Decimal("0")
        for payment in payments:
            amount = Decimal(str(payment["amount"]))
            if amount <= 0:
                raise PurchaseError("Payment amount must be greater than zero.")
            paid += amount

        if paid > total:
            raise PurchaseError("Payment exceeds purchase total.")

        credit = total - paid

        purchase = Purchase(
            document_no=document_no,
            supplier_id=supplier_id,
            business_date=business_date,
            subtotal=subtotal,
            discount=Decimal("0"),
            tax=Decimal("0"),
            total=total,
            paid_amount=paid,
            credit_amount=credit,
            status="CONFIRMED",
            payment_status=(
                "PAID" if credit == 0
                else "PARTIAL" if paid > 0
                else "CREDIT"
            ),
            idempotency_key=idempotency_key,
            created_by=created_by,
        )

        session.add(purchase)
        session.flush()

        inventory = InventoryService(session)

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

        for payment in payments:
            session.add(
                PurchasePayment(
                    purchase_id=purchase.id,
                    payment_method=str(payment["payment_method"]),
                    amount=Decimal(str(payment["amount"])),
                    currency=str(payment.get("currency", "BASE")),
                    reference_no=payment.get("reference_no"),
                )
            )

        if supplier_id is not None and credit > 0:
            SupplierService(session).register_purchase_credit(
                supplier_id=supplier_id,
                amount=credit,
                business_date=business_date,
                reference_id=str(purchase.id),
                idempotency_key=f"{idempotency_key}:supplier-credit",
                created_by=created_by,
            )

        session.flush()

        if self._owns_session:
            session.commit()

        return purchase
