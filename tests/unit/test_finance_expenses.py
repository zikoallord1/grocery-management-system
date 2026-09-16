from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import inspect

from backend.app.core.database import engine, get_session, initialize_database
from backend.app.modules.expenses.service import ExpenseService
from backend.app.modules.finance.models import (
    Cashbox,
    CashboxMovement,
    ExpenseCategory,
    PaymentMethod,
)
from backend.app.modules.finance.service import (
    CashboxService,
    FinanceError,
    DuplicateFinanceOperationError,
)


@pytest.fixture(autouse=True)
def clean_database():
    initialize_database()

    with engine.begin() as connection:
        tables = set(inspect(engine).get_table_names())
        if connection.dialect.name == "sqlite":
            connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
        try:
            for table in [
                "expense_payments",
                "expenses",
                "expense_categories",
                "cashbox_movements",
                "payment_methods",
                "cashboxes",
            ]:
                if table in tables:
                    connection.exec_driver_sql(f'DELETE FROM "{table}"')
        finally:
            if connection.dialect.name == "sqlite":
                connection.exec_driver_sql("PRAGMA foreign_keys=ON")


def test_cashbox_and_wallet_are_independent():
    session = get_session()
    try:
        service = CashboxService(session)

        cash = service.create_cashbox(
            code="CASH",
            name="النقد",
            account_type="CASH",
        )

        wallet = service.create_cashbox(
            code="WALLET-001",
            name="محفظة إلكترونية 1",
            account_type="WALLET",
            provider_name="محفظة تجريبية",
            account_reference="W001",
        )

        assert cash.account_type == "CASH"
        assert wallet.account_type == "WALLET"
        assert wallet.provider_name == "محفظة تجريبية"

        session.commit()
    finally:
        session.close()


def test_payment_method_can_point_to_wallet():
    session = get_session()
    try:
        service = CashboxService(session)

        wallet = service.create_cashbox(
            code="WALLET-002",
            name="محفظة إلكترونية 2",
            account_type="WALLET",
            provider_name="محفظة تجريبية",
        )

        method = service.create_payment_method(
            code="WALLET",
            name="محفظة إلكترونية",
            method_type="E_WALLET",
            cashbox_id=wallet.id,
        )

        assert method.method_type == "E_WALLET"
        assert method.cashbox_id == wallet.id

        session.commit()
    finally:
        session.close()


def test_cashbox_receipt_and_payment_balance():
    session = get_session()
    try:
        service = CashboxService(session)

        cash = service.create_cashbox(
            code="CASH-003",
            name="صندوق الاختبار",
            account_type="CASH",
        )

        service.move_money(
            cashbox_id=cash.id,
            amount=Decimal("1000"),
            direction="IN",
            movement_type="OPENING_BALANCE",
            business_date="2026-09-14",
            idempotency_key=str(uuid4()),
        )

        service.move_money(
            cashbox_id=cash.id,
            amount=Decimal("250"),
            direction="OUT",
            movement_type="PAYMENT",
            business_date="2026-09-14",
            idempotency_key=str(uuid4()),
        )

        assert service.get_balance(cash.id) == Decimal("750.00")

        session.commit()
    finally:
        session.close()


def test_wallet_sale_receipt():
    session = get_session()
    try:
        service = CashboxService(session)

        wallet = service.create_cashbox(
            code="WALLET-003",
            name="محفظة مبيعات",
            account_type="WALLET",
            provider_name="محفظة",
        )

        service.move_money(
            cashbox_id=wallet.id,
            amount=500,
            direction="IN",
            movement_type="SALE_RECEIPT",
            business_date="2026-09-14",
            idempotency_key=str(uuid4()),
            reference_type="SALE",
            reference_id="S-100",
        )

        assert service.get_balance(wallet.id) == Decimal("500.00")

        session.commit()
    finally:
        session.close()


def test_transfer_between_cash_and_wallet():
    session = get_session()
    try:
        service = CashboxService(session)

        cash = service.create_cashbox(
            code="CASH-004",
            name="نقد للتحويل",
            account_type="CASH",
        )

        wallet = service.create_cashbox(
            code="WALLET-004",
            name="محفظة للتحويل",
            account_type="WALLET",
            provider_name="محفظة",
        )

        service.move_money(
            cashbox_id=cash.id,
            amount=1000,
            direction="IN",
            movement_type="OPENING_BALANCE",
            business_date="2026-09-14",
            idempotency_key=str(uuid4()),
        )

        service.transfer(
            source_cashbox_id=cash.id,
            target_cashbox_id=wallet.id,
            amount=300,
            business_date="2026-09-14",
            idempotency_key=str(uuid4()),
        )

        assert service.get_balance(cash.id) == Decimal("700.00")
        assert service.get_balance(wallet.id) == Decimal("300.00")

        session.commit()
    finally:
        session.close()


def test_transfer_cannot_use_same_account():
    session = get_session()
    try:
        service = CashboxService(session)

        cash = service.create_cashbox(
            code="CASH-005",
            name="نقد",
            account_type="CASH",
        )

        with pytest.raises(FinanceError):
            service.transfer(
                source_cashbox_id=cash.id,
                target_cashbox_id=cash.id,
                amount=100,
                business_date="2026-09-14",
                idempotency_key=str(uuid4()),
            )
    finally:
        session.close()


def test_wallet_cannot_go_negative():
    session = get_session()
    try:
        service = CashboxService(session)

        wallet = service.create_cashbox(
            code="WALLET-005",
            name="محفظة بلا رصيد",
            account_type="WALLET",
            provider_name="محفظة",
        )

        with pytest.raises(FinanceError):
            service.move_money(
                cashbox_id=wallet.id,
                amount=100,
                direction="OUT",
                movement_type="PAYMENT",
                business_date="2026-09-14",
                idempotency_key=str(uuid4()),
            )
    finally:
        session.close()


def test_duplicate_cashbox_operation_rejected():
    session = get_session()
    try:
        service = CashboxService(session)

        cash = service.create_cashbox(
            code="CASH-006",
            name="صندوق",
            account_type="CASH",
        )

        key = str(uuid4())

        service.move_money(
            cashbox_id=cash.id,
            amount=100,
            direction="IN",
            movement_type="OPENING_BALANCE",
            business_date="2026-09-14",
            idempotency_key=key,
        )

        with pytest.raises(DuplicateFinanceOperationError):
            service.move_money(
                cashbox_id=cash.id,
                amount=100,
                direction="IN",
                movement_type="OPENING_BALANCE",
                business_date="2026-09-14",
                idempotency_key=key,
            )
    finally:
        session.close()


def test_expense_creates_cashbox_outflow():
    session = get_session()
    try:
        finance = CashboxService(session)

        cash = finance.create_cashbox(
            code="CASH-007",
            name="صندوق المصروف",
            account_type="CASH",
        )

        finance.move_money(
            cashbox_id=cash.id,
            amount=1000,
            direction="IN",
            movement_type="OPENING_BALANCE",
            business_date="2026-09-14",
            idempotency_key=str(uuid4()),
        )

        method = finance.create_payment_method(
            code="CASH-EXPENSE",
            name="نقد",
            method_type="CASH",
            cashbox_id=cash.id,
        )

        category = ExpenseCategory(name="تشغيل")

        session.add(category)
        session.flush()

        expense = ExpenseService(session).create_expense(
            expense_no="EXP-001",
            category_id=category.id,
            description="مصروف تجريبي",
            amount=Decimal("150"),
            business_date="2026-09-14",
            payment_method_id=method.id,
            idempotency_key=str(uuid4()),
        )

        assert expense.amount == Decimal("150.00")
        assert finance.get_balance(cash.id) == Decimal("850.00")

        session.commit()
    finally:
        session.close()


def test_expense_fails_when_cashbox_has_insufficient_balance():
    session = get_session()
    try:
        finance = CashboxService(session)

        cash = finance.create_cashbox(
            code="CASH-008",
            name="صندوق بدون رصيد",
            account_type="CASH",
        )

        method = finance.create_payment_method(
            code="CASH-EMPTY",
            name="نقد",
            method_type="CASH",
            cashbox_id=cash.id,
        )

        category = ExpenseCategory(name="مصروفات")
        session.add(category)
        session.flush()

        with pytest.raises(FinanceError):
            ExpenseService(session).create_expense(
                expense_no="EXP-002",
                category_id=category.id,
                description="مصروف يجب رفضه",
                amount=Decimal("100"),
                business_date="2026-09-14",
                payment_method_id=method.id,
                idempotency_key=str(uuid4()),
            )
    finally:
        session.close()
