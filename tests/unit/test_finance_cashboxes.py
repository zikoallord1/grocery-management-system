from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import inspect

from backend.app.core.database import engine, get_session, initialize_database
from backend.app.modules.finance.models import Cashbox, CashboxMovement, ExpenseCategory, PaymentMethod
from backend.app.modules.finance.service import CashboxService, FinanceError
from backend.app.modules.expenses.service import ExpenseService
from backend.app.modules.suppliers.service import SupplierService


@pytest.fixture(autouse=True)
def clean_transactions():
    initialize_database()
    with engine.begin() as connection:
        tables = set(inspect(engine).get_table_names())
        for table in [
            "expense_payments",
            "expenses",
            "supplier_payments",
            "supplier_account_movements",
            "suppliers",
            "cashbox_movements",
        ]:
            if table in tables:
                connection.exec_driver_sql(f'DELETE FROM "{table}"')


def test_cashbox_transfer_moves_same_amount_between_accounts():
    session = get_session()
    try:
        cash = session.query(Cashbox).filter_by(code="CASH").one()
        wallet = session.query(Cashbox).filter_by(code="WALLET").one()
        session.add(
            CashboxMovement(
                cashbox_id=cash.id,
                movement_type="OPENING_BALANCE",
                amount=Decimal("1000"),
                direction="IN",
                currency="BASE",
                business_date=date.today().isoformat(),
                idempotency_key="TEST-FINANCE-OPENING",
            )
        )
        session.flush()

        CashboxService(session).transfer(
            source_cashbox_id=cash.id,
            target_cashbox_id=wallet.id,
            amount=Decimal("250"),
            business_date=date.today().isoformat(),
            idempotency_key=str(uuid4()),
        )
        session.commit()

        service = CashboxService(session)
        assert service.get_balance(cash.id) == Decimal("750.00")
        assert service.get_balance(wallet.id) == Decimal("250.00")
    finally:
        session.close()


def test_cashbox_transfer_rejects_insufficient_balance_without_partial_transfer():
    session = get_session()
    try:
        cash = session.query(Cashbox).filter_by(code="CASH").one()
        wallet = session.query(Cashbox).filter_by(code="WALLET").one()
        before = CashboxService(session).get_balance(wallet.id)

        with pytest.raises(FinanceError):
            CashboxService(session).transfer(
                source_cashbox_id=cash.id,
                target_cashbox_id=wallet.id,
                amount=Decimal("999999999"),
                business_date=date.today().isoformat(),
                idempotency_key=str(uuid4()),
            )

        assert CashboxService(session).get_balance(wallet.id) == before
        assert session.query(CashboxMovement).filter_by(reference_type="CASH_TRANSFER").count() == 0
    finally:
        session.close()


def test_expense_payment_reduces_linked_cashbox():
    session = get_session()
    try:
        cash = session.query(Cashbox).filter_by(code="CASH").one()
        method = session.query(PaymentMethod).filter_by(code="CASH").one()
        category = session.query(ExpenseCategory).filter_by(name="أخرى").one()
        session.add(
            CashboxMovement(
                cashbox_id=cash.id,
                movement_type="OPENING_BALANCE",
                amount=Decimal("500"),
                direction="IN",
                currency="BASE",
                business_date=date.today().isoformat(),
                idempotency_key="TEST-EXPENSE-OPENING",
            )
        )
        session.flush()
        ExpenseService(session).create_expense(
            expense_no=f"E-TEST-{uuid4().hex[:8]}",
            category_id=category.id,
            description="مصروف اختبار",
            amount=Decimal("125"),
            business_date=date.today().isoformat(),
            payment_method_id=method.id,
            idempotency_key=str(uuid4()),
        )
        session.commit()
        assert CashboxService(session).get_balance(cash.id) == Decimal("375.00")
    finally:
        session.close()


def test_supplier_payment_reduces_linked_cashbox():
    session = get_session()
    try:
        cash = session.query(Cashbox).filter_by(code="CASH").one()
        session.add(
            CashboxMovement(
                cashbox_id=cash.id,
                movement_type="OPENING_BALANCE",
                amount=Decimal("1000"),
                direction="IN",
                currency="BASE",
                business_date=date.today().isoformat(),
                idempotency_key="TEST-SUPPLIER-OPENING",
            )
        )
        from backend.app.core.models import Supplier
        supplier = Supplier(code=f"FIN-{uuid4().hex[:6]}", name="مورد اختبار")
        session.add(supplier)
        session.flush()
        service = SupplierService(session)
        service.register_purchase_credit(
            supplier_id=supplier.id,
            amount=Decimal("400"),
            business_date=date.today().isoformat(),
            reference_id="FIN-PUR-001",
            idempotency_key=str(uuid4()),
        )
        service.make_payment(
            supplier_id=supplier.id,
            amount=Decimal("150"),
            business_date=date.today().isoformat(),
            payment_method="CASH",
            idempotency_key=str(uuid4()),
        )
        session.commit()
        assert service.get_balance(supplier.id) == Decimal("250.00")
        assert CashboxService(session).get_balance(cash.id) == Decimal("850.00")
    finally:
        session.close()
