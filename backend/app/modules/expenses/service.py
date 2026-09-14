from datetime import date
from decimal import Decimal

from sqlalchemy import select

from backend.app.core.database import get_session
from backend.app.modules.finance.models import Expense, ExpenseCategory, ExpensePayment, PaymentMethod
from backend.app.modules.finance.service import CashboxService
from backend.app.application.business_engine import BusinessEngine
from backend.app.domain.business_events import BusinessEvent


class ExpenseError(Exception):
    pass


class DuplicateExpenseError(ExpenseError):
    pass


class ExpenseService:
    def __init__(self, session=None, business_engine=None):
        self._session = session or get_session()
        self._owns_session = session is None
        self._business_engine = business_engine or BusinessEngine()

    def create_expense(
        self,
        *,
        expense_no: str,
        category_id: int,
        description: str,
        amount: Decimal,
        business_date: str,
        payment_method_id: int,
        idempotency_key: str,
        created_by: int | None = None,
    ):
        if amount <= 0:
            raise ExpenseError("Expense amount must be greater than zero.")
        if self._session.execute(
            select(Expense.id).where(Expense.idempotency_key == idempotency_key)
        ).scalar_one_or_none() is not None:
            raise DuplicateExpenseError("Duplicate expense.")
        if self._session.get(ExpenseCategory, category_id) is None:
            raise ExpenseError("Expense category does not exist.")
        method = self._session.get(PaymentMethod, payment_method_id)
        if method is None or not method.is_active:
            raise ExpenseError("Payment method does not exist or is inactive.")
        if method.cashbox_id is None:
            raise ExpenseError("Payment method is not linked to a cash account.")
        expense = Expense(
            expense_no=expense_no,
            category_id=category_id,
            description=description,
            amount=amount,
            currency="BASE",
            business_date=business_date,
            status="CONFIRMED",
            payment_status="PAID",
            payment_method_id=payment_method_id,
            idempotency_key=idempotency_key,
            created_by=created_by,
        )
        self._session.add(expense)
        self._session.flush()
        self._session.add(
            ExpensePayment(
                expense_id=expense.id,
                payment_method_id=payment_method_id,
                amount=amount,
                currency="BASE",
            )
        )
        CashboxService(self._session).move_money(
            cashbox_id=method.cashbox_id,
            amount=amount,
            direction="OUT",
            movement_type="EXPENSE_PAYMENT",
            business_date=business_date,
            idempotency_key=f"{idempotency_key}:cashbox",
            reference_type="EXPENSE",
            reference_id=str(expense.id),
            created_by=created_by,
        )
        self._session.flush()
        self._business_engine.process(
            self._session,
            BusinessEvent(
                event_type="EXPENSE_CONFIRMED",
                operation_id=idempotency_key,
                business_date=date.fromisoformat(business_date),
                payload={
                    "entity_type": "EXPENSE",
                    "entity_id": expense.id,
                    "created_by": created_by,
                    "amount": str(amount),
                    "category_id": category_id,
                    "payment_method_id": payment_method_id,
                    "business_date": business_date,
                    "description": description,
                },
            ),
        )
        return expense
