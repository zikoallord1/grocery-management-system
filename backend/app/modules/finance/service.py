from decimal import Decimal

from sqlalchemy import case, func, select

from backend.app.core.database import get_session
from backend.app.modules.finance.models import (
    Cashbox,
    CashboxMovement,
    PaymentMethod,
)


class FinanceError(Exception):
    pass


class DuplicateFinanceOperationError(FinanceError):
    pass


class CashboxService:
    def __init__(self, session=None):
        self._session = session or get_session()
        self._owns_session = session is None

    def get_balance(self, cashbox_id: int) -> Decimal:
        signed = case(
            (CashboxMovement.direction == "IN", CashboxMovement.amount),
            (CashboxMovement.direction == "OUT", -CashboxMovement.amount),
            else_=0,
        )

        value = self._session.execute(
            select(func.coalesce(func.sum(signed), 0)).where(
                CashboxMovement.cashbox_id == cashbox_id
            )
        ).scalar_one()

        return Decimal(str(value))

    def create_cashbox(
        self,
        *,
        code: str,
        name: str,
        account_type: str = "CASH",
        currency: str = "BASE",
        provider_name: str | None = None,
        account_reference: str | None = None,
    ) -> Cashbox:
        cashbox = Cashbox(
            code=code,
            name=name,
            account_type=account_type,
            currency=currency,
            provider_name=provider_name,
            account_reference=account_reference,
        )

        self._session.add(cashbox)
        self._session.flush()
        return cashbox

    def create_payment_method(
        self,
        *,
        code: str,
        name: str,
        method_type: str,
        cashbox_id: int | None = None,
    ) -> PaymentMethod:
        method = PaymentMethod(
            code=code,
            name=name,
            method_type=method_type,
            cashbox_id=cashbox_id,
        )

        self._session.add(method)
        self._session.flush()
        return method

    def move_money(
        self,
        *,
        cashbox_id: int,
        amount: Decimal,
        direction: str,
        movement_type: str,
        business_date: str,
        idempotency_key: str,
        reference_type: str | None = None,
        reference_id: str | None = None,
        created_by: int | None = None,
    ) -> CashboxMovement:
        if amount <= 0:
            raise FinanceError("Amount must be greater than zero.")

        if direction not in {"IN", "OUT"}:
            raise FinanceError("Direction must be IN or OUT.")

        if self._session.execute(
            select(CashboxMovement.id).where(
                CashboxMovement.idempotency_key == idempotency_key
            )
        ).scalar_one_or_none() is not None:
            raise DuplicateFinanceOperationError(
                "Duplicate cashbox operation."
            )

        cashbox = self._session.get(Cashbox, cashbox_id)
        if cashbox is None or not cashbox.is_active:
            raise FinanceError("Cashbox does not exist or is inactive.")

        if direction == "OUT":
            balance = self.get_balance(cashbox_id)
            if balance < amount:
                raise FinanceError(
                    f"Insufficient balance: balance={balance}"
                )

        movement = CashboxMovement(
            cashbox_id=cashbox_id,
            movement_type=movement_type,
            amount=amount,
            direction=direction,
            currency=cashbox.currency,
            reference_type=reference_type,
            reference_id=reference_id,
            business_date=business_date,
            idempotency_key=idempotency_key,
            created_by=created_by,
        )

        self._session.add(movement)
        self._session.flush()
        return movement

    def transfer(
        self,
        *,
        source_cashbox_id: int,
        target_cashbox_id: int,
        amount: Decimal,
        business_date: str,
        idempotency_key: str,
        created_by: int | None = None,
    ) -> tuple[CashboxMovement, CashboxMovement]:
        if source_cashbox_id == target_cashbox_id:
            raise FinanceError("Source and target must be different.")

        source = self._session.get(Cashbox, source_cashbox_id)
        target = self._session.get(Cashbox, target_cashbox_id)

        if source is None or target is None:
            raise FinanceError("Source or target account does not exist.")

        out_movement = self.move_money(
            cashbox_id=source_cashbox_id,
            amount=amount,
            direction="OUT",
            movement_type="TRANSFER_OUT",
            business_date=business_date,
            idempotency_key=f"{idempotency_key}:OUT",
            reference_type="CASH_TRANSFER",
            reference_id=idempotency_key,
            created_by=created_by,
        )

        in_movement = self.move_money(
            cashbox_id=target_cashbox_id,
            amount=amount,
            direction="IN",
            movement_type="TRANSFER_IN",
            business_date=business_date,
            idempotency_key=f"{idempotency_key}:IN",
            reference_type="CASH_TRANSFER",
            reference_id=idempotency_key,
            created_by=created_by,
        )

        return out_movement, in_movement
