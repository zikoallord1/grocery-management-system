from datetime import date
from decimal import Decimal

from sqlalchemy import case, func, select

from backend.app.core.database import get_session
from backend.app.core.models import Supplier, SupplierAccountMovement, SupplierPayment
from backend.app.application.business_engine import BusinessEngine
from backend.app.domain.business_events import BusinessEvent
from backend.app.modules.finance.models import PaymentMethod
from backend.app.modules.finance.service import CashboxService
from backend.app.core.operation_guard import authorize_operation


class SupplierError(Exception):
    pass


class SupplierCreditError(SupplierError):
    pass


class DuplicateSupplierOperationError(SupplierError):
    pass


class SupplierService:
    def __init__(self, session=None, business_engine=None):
        self._session = session or get_session()
        self._owns_session = session is None
        self._business_engine = business_engine or BusinessEngine()

    def get_balance(self, supplier_id: int) -> Decimal:
        signed = case(
            (SupplierAccountMovement.direction == "CREDIT", SupplierAccountMovement.amount),
            (SupplierAccountMovement.direction == "DEBIT", -SupplierAccountMovement.amount),
            else_=0,
        )
        value = self._session.execute(
            select(func.coalesce(func.sum(signed), 0)).where(
                SupplierAccountMovement.supplier_id == supplier_id
            )
        ).scalar_one()
        return Decimal(str(value))

    def register_purchase_credit(
        self,
        *,
        supplier_id: int,
        amount: Decimal,
        business_date: str,
        reference_id: str,
        idempotency_key: str,
        created_by: int | None = None,
    ):
        created_by = authorize_operation(
            self._session, operation_id=idempotency_key, module="الموردون",
            permission="إضافة", entity_type="SUPPLIER_PAYMENT",
            entity_id=str(supplier_id), created_by=created_by,
        )
        supplier = self._session.get(Supplier, supplier_id)
        if supplier is None or not supplier.is_active:
            raise SupplierError("Supplier does not exist or is inactive.")
        if amount <= 0:
            raise SupplierCreditError("Credit amount must be greater than zero.")
        if self._session.execute(
            select(SupplierAccountMovement.id).where(
                SupplierAccountMovement.idempotency_key == idempotency_key
            )
        ).scalar_one_or_none() is not None:
            raise DuplicateSupplierOperationError("Duplicate supplier account operation.")
        movement = SupplierAccountMovement(
            supplier_id=supplier_id,
            movement_type="PURCHASE_CREDIT",
            amount=amount,
            direction="CREDIT",
            currency="BASE",
            reference_type="PURCHASE",
            reference_id=reference_id,
            business_date=business_date,
            idempotency_key=idempotency_key,
            created_by=created_by,
        )
        self._session.add(movement)
        self._session.flush()
        self._business_engine.process(
            self._session,
            BusinessEvent(
                event_type="SUPPLIER_PURCHASE_CREDIT_REGISTERED",
                operation_id=idempotency_key,
                business_date=date.fromisoformat(business_date),
                payload={
                    "entity_type": "SUPPLIER",
                    "entity_id": supplier_id,
                    "created_by": created_by,
                    "reference_id": reference_id,
                    "amount": str(amount),
                    "business_date": business_date,
                },
            ),
        )
        return movement

    def make_payment(
        self,
        *,
        supplier_id: int,
        amount: Decimal,
        business_date: str,
        payment_method: str,
        idempotency_key: str,
        reference_no: str | None = None,
        created_by: int | None = None,
    ):
        supplier = self._session.get(Supplier, supplier_id)
        if supplier is None or not supplier.is_active:
            raise SupplierError("Supplier does not exist or is inactive.")
        if amount <= 0:
            raise SupplierError("Payment amount must be greater than zero.")
        if self._session.execute(
            select(SupplierPayment.id).where(
                SupplierPayment.idempotency_key == idempotency_key
            )
        ).scalar_one_or_none() is not None:
            raise DuplicateSupplierOperationError("Duplicate supplier payment.")
        current = self.get_balance(supplier_id)
        if amount > current:
            raise SupplierError(f"Payment exceeds supplier balance: balance={current}")

        method = self._session.execute(
            select(PaymentMethod).where(
                PaymentMethod.code == payment_method,
                PaymentMethod.is_active.is_(True),
            )
        ).scalar_one_or_none()
        if method is None:
            raise SupplierError("Payment method does not exist or is inactive.")
        if method.cashbox_id is None:
            raise SupplierError("Selected payment method is not linked to a cashbox.")

        payment = SupplierPayment(
            supplier_id=supplier_id,
            amount=amount,
            currency="BASE",
            payment_method=payment_method,
            business_date=business_date,
            reference_no=reference_no,
            idempotency_key=idempotency_key,
            created_by=created_by,
        )
        movement = SupplierAccountMovement(
            supplier_id=supplier_id,
            movement_type="SUPPLIER_PAYMENT",
            amount=amount,
            direction="DEBIT",
            currency="BASE",
            reference_type="SUPPLIER_PAYMENT",
            reference_id=reference_no,
            business_date=business_date,
            idempotency_key=f"{idempotency_key}:movement",
            created_by=created_by,
        )
        self._session.add_all([payment, movement])
        self._session.flush()
        CashboxService(self._session).move_money(
            cashbox_id=method.cashbox_id,
            amount=amount,
            direction="OUT",
            movement_type="SUPPLIER_PAYMENT",
            business_date=business_date,
            idempotency_key=f"{idempotency_key}:cashbox",
            reference_type="SUPPLIER_PAYMENT",
            reference_id=reference_no or str(payment.id),
            created_by=created_by,
        )
        self._business_engine.process(
            self._session,
            BusinessEvent(
                event_type="SUPPLIER_PAYMENT_MADE",
                operation_id=idempotency_key,
                business_date=date.fromisoformat(business_date),
                payload={
                    "entity_type": "SUPPLIER_PAYMENT",
                    "entity_id": payment.id,
                    "supplier_id": supplier_id,
                    "created_by": created_by,
                    "amount": str(amount),
                    "payment_method": payment_method,
                    "business_date": business_date,
                    "reference_no": reference_no,
                },
            ),
        )
        return payment
