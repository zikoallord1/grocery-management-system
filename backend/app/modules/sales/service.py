from decimal import Decimal
from uuid import uuid4

from sqlalchemy import case, func, select
from sqlalchemy.exc import IntegrityError

from backend.app.core.database import get_session
from backend.app.core.models import Product, StockMovement
from backend.app.modules.inventory.service import (
    DuplicateInventoryOperationError,
    InsufficientStockError,
    InventoryError,
    InventoryService,
)


class SaleError(Exception):
    """Base error for sales."""


class InvalidSaleError(SaleError):
    """Raised when sale data is invalid."""


class DuplicateSaleError(SaleError):
    """Raised when a sale is submitted more than once."""


class SaleService:
    def __init__(self, session=None):
        self._session = session
        self._owns_session = session is None

    def _get_session(self):
        if self._session is None:
            self._session = get_session()
        return self._session

    def close(self):
        if self._owns_session and self._session is not None:
            self._session.close()
            self._session = None

    def create_sale(
        self,
        *,
        document_no: str,
        business_date: str,
        items: list[dict],
        payments: list[dict],
        idempotency_key: str,
        created_by: int | None = None,
    ):
        session = self._get_session()

        if not document_no.strip():
            raise InvalidSaleError("Document number is required.")

        if not items:
            raise InvalidSaleError("Sale must contain at least one item.")

        if not payments:
            raise InvalidSaleError("Sale must contain at least one payment entry.")

        existing = session.execute(
            select(Sale.id).where(
                Sale.idempotency_key == idempotency_key
            )
        ).scalar_one_or_none()

        if existing is not None:
            raise DuplicateSaleError(
                f"Sale already exists: {idempotency_key}"
            )

        existing_document = session.execute(
            select(Sale.id).where(
                Sale.document_no == document_no
            )
        ).scalar_one_or_none()

        if existing_document is not None:
            raise DuplicateSaleError(
                f"Document number already exists: {document_no}"
            )

        subtotal = Decimal("0")
        normalized_items = []

        for item in items:
            product_id = int(item["product_id"])
            quantity = Decimal(str(item["quantity"]))
            unit_price = Decimal(str(item["unit_price"]))
            discount = Decimal(str(item.get("discount", "0")))

            if quantity <= 0:
                raise InvalidSaleError("Quantity must be greater than zero.")

            if unit_price < 0:
                raise InvalidSaleError("Unit price cannot be negative.")

            if discount < 0:
                raise InvalidSaleError("Discount cannot be negative.")

            product = session.get(Product, product_id)
            if product is None:
                raise InvalidSaleError(
                    f"Product does not exist: {product_id}"
                )

            line_total = (quantity * unit_price) - discount

            if line_total < 0:
                raise InvalidSaleError(
                    "Line total cannot be negative."
                )

            subtotal += line_total

            normalized_items.append(
                {
                    "product": product,
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "discount": discount,
                    "total": line_total,
                    "cost_price_snapshot": Decimal(str(product.purchase_price)),
                }
            )

        total = subtotal

        payment_total = Decimal("0")

        for payment in payments:
            amount = Decimal(str(payment["amount"]))

            if amount <= 0:
                raise InvalidSaleError(
                    "Payment amount must be greater than zero."
                )

            payment_total += amount

        if payment_total > total:
            raise InvalidSaleError(
                f"Payment exceeds sale total: total={total}, paid={payment_total}"
            )

        credit_amount = total - payment_total
        payment_status = (
            "PAID"
            if credit_amount == 0
            else "PARTIAL"
            if payment_total > 0
            else "CREDIT"
        )

        sale = Sale(
            document_no=document_no,
            business_date=business_date,
            subtotal=subtotal,
            discount=Decimal("0"),
            tax=Decimal("0"),
            total=total,
            paid_amount=payment_total,
            credit_amount=credit_amount,
            status="CONFIRMED",
            payment_status=payment_status,
            idempotency_key=idempotency_key,
            created_by=created_by,
        )

        session.add(sale)
        session.flush()

        inventory = InventoryService(session)

        try:
            for item in normalized_items:
                sale_item = SaleItem(
                    sale_id=sale.id,
                    product_id=item["product"].id,
                    quantity=item["quantity"],
                    unit_price=item["unit_price"],
                    discount=item["discount"],
                    total=item["total"],
                    cost_price_snapshot=item["cost_price_snapshot"],
                )

                session.add(sale_item)

                inventory.remove_stock(
                    product_id=item["product"].id,
                    stock_location_id=int(items[normalized_items.index(item)].get("stock_location_id", 1)),
                    quantity=item["quantity"],
                    unit_cost=item["cost_price_snapshot"],
                    business_date=business_date,
                    idempotency_key=f"{idempotency_key}:stock:{item['product'].id}:{uuid4()}",
                    reference_type="SALE",
                    reference_id=str(sale.id),
                    created_by=created_by,
                )

            for payment in payments:
                sale_payment = SalePayment(
                    sale_id=sale.id,
                    payment_method=str(payment["payment_method"]),
                    amount=Decimal(str(payment["amount"])),
                    currency=str(payment.get("currency", "BASE")),
                    reference_no=payment.get("reference_no"),
                )
                session.add(sale_payment)

            session.flush()

            if self._owns_session:
                session.commit()

        except (InventoryError, IntegrityError) as exc:
            if self._owns_session:
                session.rollback()
            if isinstance(exc, InventoryError):
                raise
            raise SaleError("Sale transaction failed.") from exc

        return sale


from backend.app.core.models import Sale, SaleItem, SalePayment
