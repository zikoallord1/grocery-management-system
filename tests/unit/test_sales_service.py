import uuid
from decimal import Decimal

import pytest
from sqlalchemy import inspect

from backend.app.core.models import Customer
from backend.app.core.database import engine, get_session, initialize_database
from backend.app.core.models import Category, Product, StockLocation, Unit
from backend.app.modules.inventory.service import InventoryService
from backend.app.modules.sales.service import (
    DuplicateSaleError,
    InvalidSaleError,
    SaleService,
)


@pytest.fixture(autouse=True)
def clean_database():
    initialize_database()
    from backend.app.modules.finance.models import Cashbox, PaymentMethod
    from backend.app.core.database import SessionLocal
    _setup_session = SessionLocal()
    try:
        wallet_box = _setup_session.query(Cashbox).filter_by(code='WALLET').first()
        if wallet_box is None:
            wallet_box = Cashbox(code='WALLET', name='??????? ?????????', account_type='WALLET', currency='BASE')
            _setup_session.add(wallet_box)
            _setup_session.flush()
        wallet_method = _setup_session.query(PaymentMethod).filter_by(code='WALLET').first()
        if wallet_method is None:
            _setup_session.add(PaymentMethod(code='WALLET', name='?????', method_type='WALLET', cashbox_id=wallet_box.id, is_active=True))
        _setup_session.commit()
    finally:
        _setup_session.close()

    with engine.begin() as connection:
        tables = set(inspect(engine).get_table_names())

        for table in [
            "sale_payments",
            "sale_items",
            "sales",
            "stock_movements",
            "product_barcodes",
            "products",
            "stock_locations",
            "units",
            "categories",
        ]:
            if table in tables:
                connection.exec_driver_sql(f'DELETE FROM "{table}"')


def setup_product_and_stock(session):
    category = Category(name="مبيعات")
    unit = Unit(name="حبة مبيع", symbol="حبة")
    location = StockLocation(
        code="SALE-MAIN",
        name="مخزن البيع",
        location_type="STORE",
    )

    session.add_all([category, unit, location])
    session.flush()

    product = Product(
        sku="SALE-001",
        name="صنف بيع",
        category_id=category.id,
        default_unit_id=unit.id,
        purchase_price=Decimal("80"),
        sale_price=Decimal("120"),
    )
    session.add(product)
    session.flush()

    inventory = InventoryService(session)

    inventory.add_stock(
        product_id=product.id,
        stock_location_id=location.id,
        quantity=Decimal("10"),
        unit_cost=Decimal("80"),
        business_date="2026-09-14",
        idempotency_key=str(uuid.uuid4()),
    )

    return product, location


def test_create_cash_sale_reduces_stock():
    session = get_session()

    try:
        product, location = setup_product_and_stock(session)
        service = SaleService(session)

        sale = service.create_sale(
            document_no="S-0001",
            business_date="2026-09-14",
            items=[
                {
                    "product_id": product.id,
                    "stock_location_id": location.id,
                    "quantity": "2",
                    "unit_price": "120",
                    "discount": "0",
                }
            ],
            payments=[
                {
                    "payment_method": "CASH",
                    "amount": "240",
                }
            ],
            idempotency_key=str(uuid.uuid4()),
        )

        assert sale.total == Decimal("240.00")
        assert sale.paid_amount == Decimal("240.00")
        assert sale.credit_amount == Decimal("0.00")

        inventory = InventoryService(session)

        assert inventory.get_balance(
            product.id,
            location.id,
        ) == Decimal("8.000")

        session.commit()

    finally:
        session.close()


def test_mixed_payment_is_supported():
    session = get_session()

    try:
        product, location = setup_product_and_stock(session)
        service = SaleService(session)
        customer = Customer(
            code="CUST-TEST-MIXED-001",
            name="test-customer-mixed-payment",
            phone="0000000000",
        )
        session.add(customer)
        session.flush()

        sale = service.create_sale(
            document_no="S-0002",
            business_date="2026-09-14",
            customer_id=customer.id,
            items=[
                {
                    "product_id": product.id,
                    "stock_location_id": location.id,
                    "quantity": "2",
                    "unit_price": "100",
                    "discount": "0",
                }
            ],
            payments=[
                {
                    "payment_method": "CASH",
                    "amount": "100",
                },
                {
                    "payment_method": "WALLET",
                    "amount": "50",
                },
            ],
            idempotency_key=str(uuid.uuid4()),
        )

        assert sale.total == Decimal("200.00")
        assert sale.paid_amount == Decimal("150.00")
        assert sale.credit_amount == Decimal("50.00")
        assert sale.payment_status == "PARTIAL"

        session.commit()

    finally:
        session.close()


def test_duplicate_sale_is_rejected():
    session = get_session()

    try:
        product, location = setup_product_and_stock(session)
        service = SaleService(session)

        key = str(uuid.uuid4())

        payload = dict(
            document_no="S-0003",
            business_date="2026-09-14",
            items=[
                {
                    "product_id": product.id,
                    "stock_location_id": location.id,
                    "quantity": "1",
                    "unit_price": "100",
                    "discount": "0",
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

        service.create_sale(**payload)
        session.commit()

        with pytest.raises(DuplicateSaleError):
            service.create_sale(**payload)

    finally:
        session.close()


def test_payment_cannot_exceed_total():
    session = get_session()

    try:
        product, location = setup_product_and_stock(session)
        service = SaleService(session)

        with pytest.raises(InvalidSaleError):
            service.create_sale(
                document_no="S-0004",
                business_date="2026-09-14",
                items=[
                    {
                        "product_id": product.id,
                        "stock_location_id": location.id,
                        "quantity": "1",
                        "unit_price": "100",
                    }
                ],
                payments=[
                    {
                        "payment_method": "CASH",
                        "amount": "101",
                    }
                ],
                idempotency_key=str(uuid.uuid4()),
            )

    finally:
        session.close()


def test_sale_fails_when_stock_is_insufficient():
    session = get_session()

    try:
        product, location = setup_product_and_stock(session)
        service = SaleService(session)

        with pytest.raises(Exception):
            service.create_sale(
                document_no="S-0005",
                business_date="2026-09-14",
                items=[
                    {
                        "product_id": product.id,
                        "stock_location_id": location.id,
                        "quantity": "11",
                        "unit_price": "100",
                    }
                ],
                payments=[
                    {
                        "payment_method": "CASH",
                        "amount": "1100",
                    }
                ],
                idempotency_key=str(uuid.uuid4()),
            )

        inventory = InventoryService(session)

        assert inventory.get_balance(
            product.id,
            location.id,
        ) == Decimal("10.000")

    finally:
        session.close()
