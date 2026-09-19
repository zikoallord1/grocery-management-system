from datetime import date
from decimal import Decimal

from sqlalchemy import case, func, select

from backend.app.core.database import get_session
from backend.app.core.models import Customer, CustomerAccountMovement, CustomerPayment
from backend.app.application.business_engine import BusinessEngine
from backend.app.domain.business_events import BusinessEvent
from backend.app.modules.finance.models import PaymentMethod
from backend.app.modules.finance.service import CashboxService
from backend.app.core.operation_guard import authorize_operation


class CustomerError(Exception):
    """Base customer error."""


class CustomerCreditError(CustomerError):
    """Raised when customer credit rules are violated."""


class DuplicateCustomerOperationError(CustomerError):
    """Raised for duplicate customer operations."""


class CustomerService:
    def __init__(self, session=None, business_engine=None):
        self._session = session
        self._owns_session = session is None
        self._business_engine = business_engine or BusinessEngine()

    def _get_session(self):
        if self._session is None:
            self._session = get_session()
        return self._session

    def get_balance(self, customer_id: int) -> Decimal:
        session = self._get_session()
        signed = case(
            (CustomerAccountMovement.direction == "DEBIT", CustomerAccountMovement.amount),
            (CustomerAccountMovement.direction == "CREDIT", -CustomerAccountMovement.amount),
            else_=0,
        )
        value = session.execute(
            select(func.coalesce(func.sum(signed), 0)).where(
                CustomerAccountMovement.customer_id == customer_id
            )
        ).scalar_one()
        return Decimal(str(value))

    def register_sale_credit(
        self,
        *,
        customer_id: int,
        amount: Decimal,
        business_date: str,
        reference_id: str,
        idempotency_key: str,
        created_by: int | None = None,
    ):
        session = self._get_session()
        created_by = authorize_operation(
            session, operation_id=idempotency_key, module="العملاء",
            permission="إضافة", entity_type="CUSTOMER_PAYMENT",
            entity_id=str(customer_id), created_by=created_by,
        )
        customer = session.get(Customer, customer_id)
        if customer is None or not customer.is_active:
            raise CustomerError("Customer does not exist or is inactive.")
        if amount <= 0:
            raise CustomerCreditError("Credit amount must be greater than zero.")
        existing = session.execute(
            select(CustomerAccountMovement.id).where(
                CustomerAccountMovement.idempotency_key == idempotency_key
            )
        ).scalar_one_or_none()
        if existing is not None:
            raise DuplicateCustomerOperationError("Duplicate customer account operation.")
        current = self.get_balance(customer_id)
        new_balance = current + amount
        if customer.credit_limit is not None and new_balance > Decimal(str(customer.credit_limit)):
            raise CustomerCreditError("Customer credit limit would be exceeded.")
        movement = CustomerAccountMovement(
            customer_id=customer_id,
            movement_type="SALE_CREDIT",
            amount=amount,
            direction="DEBIT",
            currency="BASE",
            reference_type="SALE",
            reference_id=reference_id,
            business_date=business_date,
            idempotency_key=idempotency_key,
            created_by=created_by,
        )
        session.add(movement)
        session.flush()
        self._business_engine.process(
            session,
            BusinessEvent(
                event_type="CUSTOMER_SALE_CREDIT_REGISTERED",
                operation_id=idempotency_key,
                business_date=date.fromisoformat(business_date),
                payload={
                    "entity_type": "CUSTOMER",
                    "entity_id": customer_id,
                    "created_by": created_by,
                    "reference_id": reference_id,
                    "amount": str(amount),
                    "business_date": business_date,
                },
            ),
        )
        return movement

    def receive_payment(
        self,
        *,
        customer_id: int,
        amount: Decimal,
        business_date: str,
        payment_method: str,
        idempotency_key: str,
        reference_no: str | None = None,
        created_by: int | None = None,
    ):
        session = self._get_session()
        customer = session.get(Customer, customer_id)
        if customer is None or not customer.is_active:
            raise CustomerError("Customer does not exist or is inactive.")
        if amount <= 0:
            raise CustomerError("Payment amount must be greater than zero.")
        existing = session.execute(
            select(CustomerPayment.id).where(
                CustomerPayment.idempotency_key == idempotency_key
            )
        ).scalar_one_or_none()
        if existing is not None:
            raise DuplicateCustomerOperationError("Duplicate customer payment.")
        current = self.get_balance(customer_id)
        if amount > current:
            raise CustomerError(f"Payment exceeds outstanding balance: balance={current}")

        method = session.execute(
            select(PaymentMethod).where(
                PaymentMethod.code == payment_method,
                PaymentMethod.is_active.is_(True),
            )
        ).scalar_one_or_none()
        if method is None:
            raise CustomerError("Payment method does not exist or is inactive.")
        if method.cashbox_id is None:
            raise CustomerError("Selected payment method is not linked to a cashbox.")

        payment = CustomerPayment(
            customer_id=customer_id,
            amount=amount,
            currency="BASE",
            payment_method=payment_method,
            business_date=business_date,
            reference_no=reference_no,
            idempotency_key=idempotency_key,
            created_by=created_by,
        )
        movement = CustomerAccountMovement(
            customer_id=customer_id,
            movement_type="CUSTOMER_PAYMENT",
            amount=amount,
            direction="CREDIT",
            currency="BASE",
            reference_type="CUSTOMER_PAYMENT",
            reference_id=reference_no,
            business_date=business_date,
            idempotency_key=f"{idempotency_key}:movement",
            created_by=created_by,
        )
        session.add_all([payment, movement])
        session.flush()
        CashboxService(session).move_money(
            cashbox_id=method.cashbox_id,
            amount=amount,
            direction="IN",
            movement_type="CUSTOMER_PAYMENT",
            business_date=business_date,
            idempotency_key=f"{idempotency_key}:cashbox",
            reference_type="CUSTOMER_PAYMENT",
            reference_id=reference_no or str(payment.id),
            created_by=created_by,
        )
        self._business_engine.process(
            session,
            BusinessEvent(
                event_type="CUSTOMER_PAYMENT_RECEIVED",
                operation_id=idempotency_key,
                business_date=date.fromisoformat(business_date),
                payload={
                    "entity_type": "CUSTOMER_PAYMENT",
                    "entity_id": payment.id,
                    "customer_id": customer_id,
                    "created_by": created_by,
                    "amount": str(amount),
                    "payment_method": payment_method,
                    "business_date": business_date,
                    "reference_no": reference_no,
                },
            ),
        )
        return payment
