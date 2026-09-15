from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import inspect

from backend.app.core.database import engine, get_session, initialize_database
from backend.app.core.models import Category, Product, StockLocation, Unit
from backend.app.modules.inventory.service import InventoryService
from backend.app.modules.purchases.service import (
    DuplicatePurchaseError,
    PurchaseError,
    PurchaseService,
)
from backend.app.modules.suppliers.service import (
    SupplierService,
    SupplierError,
    DuplicateSupplierOperationError,
)


@pytest.fixture(autouse=True)
def clean_database():
    initialize_database()
    from backend.app.modules.finance.models import Cashbox, CashboxMovement
    from backend.app.core.database import SessionLocal
    _setup_session = SessionLocal()
    try:
        cash_box = _setup_session.query(Cashbox).filter_by(code='CASH').first()
        if cash_box is None:
            raise RuntimeError('Default CASH cashbox was not created')
        existing_opening = _setup_session.query(CashboxMovement).filter_by(idempotency_key='TEST-OPENING-CASH').first()
        if existing_opening is None:
            _setup_session.add(CashboxMovement(
                cashbox_id=cash_box.id,
                movement_type='OPENING_BALANCE',
                amount=100000,
                direction='IN',
                currency='BASE',
                business_date=date.today(),
                idempotency_key='TEST-OPENING-CASH'
            ))
            _setup_session.commit()
    finally:
        _setup_session.close()

    with engine.begin() as connection:
        tables = set(inspect(engine).get_table_names())

        for table in [
            "purchase_payments",
            "purchase_items",
            "purchases",
            "supplier_payments",
            "supplier_account_movements",
            "suppliers",
            "stock_movements",
            "product_barcodes",
            "products",
            "stock_locations",
            "units",
            "categories",
        ]:
            if table in tables:
                connection.exec_driver_sql(f'DELETE FROM "{table}"')


def setup_supplier_and_product(session):
    from backend.app.core.models import Supplier

    supplier = Supplier(
        code="SUP-001",
        name="مورد تجريبي",
        credit_limit=Decimal("5000"),
    )

    category = Category(name="مشتريات")
    unit = Unit(name="كرتون", symbol="كرتون")
    location = StockLocation(
        code="PUR-MAIN",
        name="المخزن الرئيسي",
        location_type="STORE",
    )

    session.add_all([supplier, category, unit, location])
    session.flush()

    product = Product(
        sku="PUR-001",
        name="صنف شراء",
        category_id=category.id,
        default_unit_id=unit.id,
        purchase_price=Decimal("100"),
        sale_price=Decimal("130"),
    )
    session.add(product)
    session.flush()

    return supplier, product, location


def test_cash_purchase_increases_stock():
    session = get_session()

    try:
        supplier, product, location = setup_supplier_and_product(session)

        purchase = PurchaseService(session).create_purchase(
            document_no="P-0001",
            supplier_id=supplier.id,
            business_date="2026-09-14",
            items=[
                {
                    "product_id": product.id,
                    "stock_location_id": location.id,
                    "quantity": "10",
                    "unit_cost": "100",
                }
            ],
            payments=[
                {
                    "payment_method": "CASH",
                    "amount": "1000",
                }
            ],
            idempotency_key=str(uuid4()),
        )

        assert purchase.total == Decimal("1000.00")
        assert purchase.paid_amount == Decimal("1000.00")
        assert purchase.credit_amount == Decimal("0.00")

        assert InventoryService(session).get_balance(
            product.id,
            location.id,
        ) == Decimal("10.000")
    finally:
        session.close()


def test_credit_purchase_creates_supplier_balance():
    session = get_session()

    try:
        supplier, product, location = setup_supplier_and_product(session)

        PurchaseService(session).create_purchase(
            document_no="P-0002",
            supplier_id=supplier.id,
            business_date="2026-09-14",
            items=[
                {
                    "product_id": product.id,
                    "stock_location_id": location.id,
                    "quantity": "10",
                    "unit_cost": "100",
                }
            ],
            payments=[],
            idempotency_key=str(uuid4()),
        )

        assert SupplierService(session).get_balance(
            supplier.id
        ) == Decimal("1000.00")
    finally:
        session.close()


def test_mixed_purchase_creates_partial_supplier_balance():
    session = get_session()

    try:
        supplier, product, location = setup_supplier_and_product(session)

        PurchaseService(session).create_purchase(
            document_no="P-0003",
            supplier_id=supplier.id,
            business_date="2026-09-14",
            items=[
                {
                    "product_id": product.id,
                    "stock_location_id": location.id,
                    "quantity": "10",
                    "unit_cost": "100",
                }
            ],
            payments=[
                {
                    "payment_method": "CASH",
                    "amount": "600",
                }
            ],
            idempotency_key=str(uuid4()),
        )

        assert SupplierService(session).get_balance(
            supplier.id
        ) == Decimal("400.00")
    finally:
        session.close()


def test_supplier_payment_reduces_balance():
    session = get_session()

    try:
        supplier, product, location = setup_supplier_and_product(session)

        service = SupplierService(session)

        service.register_purchase_credit(
            supplier_id=supplier.id,
            amount=Decimal("500"),
            business_date="2026-09-14",
            reference_id="PUR-001",
            idempotency_key=str(uuid4()),
        )

        service.make_payment(
            supplier_id=supplier.id,
            amount=Decimal("200"),
            business_date="2026-09-14",
            payment_method="CASH",
            idempotency_key=str(uuid4()),
        )

        assert service.get_balance(supplier.id) == Decimal("300.00")
    finally:
        session.close()


def test_supplier_payment_cannot_exceed_balance():
    session = get_session()

    try:
        supplier, _, _ = setup_supplier_and_product(session)

        service = SupplierService(session)

        service.register_purchase_credit(
            supplier_id=supplier.id,
            amount=Decimal("100"),
            business_date="2026-09-14",
            reference_id="PUR-002",
            idempotency_key=str(uuid4()),
        )

        with pytest.raises(SupplierError):
            service.make_payment(
                supplier_id=supplier.id,
                amount=Decimal("150"),
                business_date="2026-09-14",
                payment_method="CASH",
                idempotency_key=str(uuid4()),
            )
    finally:
        session.close()


def test_duplicate_purchase_is_rejected():
    session = get_session()

    try:
        supplier, product, location = setup_supplier_and_product(session)

        key = str(uuid4())

        payload = dict(
            document_no="P-0004",
            supplier_id=supplier.id,
            business_date="2026-09-14",
            items=[
                {
                    "product_id": product.id,
                    "stock_location_id": location.id,
                    "quantity": "1",
                    "unit_cost": "100",
                }
            ],
            payments=[
                {
                    "payment_method": "CASH",
                    "amount": "100",
                }
            ],
            idempotency_key=key,
        )

        PurchaseService(session).create_purchase(**payload)

        with pytest.raises(DuplicatePurchaseError):
            PurchaseService(session).create_purchase(**payload)
    finally:
        session.close()
