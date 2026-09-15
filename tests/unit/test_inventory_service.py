from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import inspect

from backend.app.core.database import engine, get_session, initialize_database
from backend.app.core.models import Category, Product, StockLocation, Unit
from backend.app.modules.inventory.service import (
    DuplicateInventoryOperationError,
    InsufficientStockError,
    InventoryError,
    InventoryService,
)


def setup_entities(session):
    category = Category(name="مشروبات")
    unit = Unit(name="حبة خدمة", symbol="حبة")
    location = StockLocation(
        code="MAIN-SVC",
        name="المخزن الرئيسي",
        location_type="STORE",
    )

    session.add_all([category, unit, location])
    session.flush()

    product = Product(
        sku="SVC-001",
        name="صنف خدمة",
        category_id=category.id,
        default_unit_id=unit.id,
        purchase_price=Decimal("100"),
        sale_price=Decimal("130"),
    )
    session.add(product)
    session.flush()

    return product, location


@pytest.fixture(autouse=True)
def clean_database():
    initialize_database()

    with engine.begin() as connection:
        tables = set(inspect(engine).get_table_names())

        for table in [
            "cashbox_movements",
            "sale_payments",
            "sale_items",
            "sales",
            "purchase_payments",
            "purchase_items",
            "purchases",
            "customer_payments",
            "customer_account_movements",
            "supplier_payments",
            "supplier_account_movements",
            "product_barcodes",
            "stock_movements",
            "expense_payments",
            "expenses",
            "expense_categories",
            "payment_methods",
            "customers",
            "suppliers",
            "products",
            "stock_locations",
            "units",
            "categories",
        ]:
            if table in tables:
                connection.exec_driver_sql(f'DELETE FROM "{table}"')

def test_add_stock_and_read_balance():
    session = get_session()
    try:
        product, location = setup_entities(session)

        service = InventoryService(session)

        service.add_stock(
            product_id=product.id,
            stock_location_id=location.id,
            quantity=Decimal("10"),
            unit_cost=Decimal("100"),
            business_date="2026-09-14",
            idempotency_key=str(uuid4()),
        )

        assert service.get_balance(
            product.id,
            location.id,
        ) == Decimal("10.000")

        session.commit()
    finally:
        session.close()


def test_add_then_remove_stock():
    session = get_session()
    try:
        product, location = setup_entities(session)

        service = InventoryService(session)

        service.add_stock(
            product_id=product.id,
            stock_location_id=location.id,
            quantity=Decimal("10"),
            unit_cost=Decimal("100"),
            business_date="2026-09-14",
            idempotency_key=str(uuid4()),
        )

        service.remove_stock(
            product_id=product.id,
            stock_location_id=location.id,
            quantity=Decimal("4"),
            unit_cost=Decimal("100"),
            business_date="2026-09-14",
            idempotency_key=str(uuid4()),
        )

        assert service.get_balance(
            product.id,
            location.id,
        ) == Decimal("6.000")

        session.commit()
    finally:
        session.close()


def test_negative_stock_is_rejected():
    session = get_session()
    try:
        product, location = setup_entities(session)

        service = InventoryService(session)

        with pytest.raises(InsufficientStockError):
            service.remove_stock(
                product_id=product.id,
                stock_location_id=location.id,
                quantity=Decimal("1"),
                unit_cost=Decimal("100"),
                business_date="2026-09-14",
                idempotency_key=str(uuid4()),
            )
    finally:
        session.close()


def test_zero_quantity_is_rejected():
    session = get_session()
    try:
        product, location = setup_entities(session)

        service = InventoryService(session)

        with pytest.raises(InventoryError):
            service.add_stock(
                product_id=product.id,
                stock_location_id=location.id,
                quantity=Decimal("0"),
                unit_cost=Decimal("100"),
                business_date="2026-09-14",
                idempotency_key=str(uuid4()),
            )
    finally:
        session.close()


def test_duplicate_idempotency_is_rejected():
    session = get_session()
    try:
        product, location = setup_entities(session)
        service = InventoryService(session)

        key = str(uuid4())

        service.add_stock(
            product_id=product.id,
            stock_location_id=location.id,
            quantity=Decimal("3"),
            unit_cost=Decimal("100"),
            business_date="2026-09-14",
            idempotency_key=key,
        )

        with pytest.raises(DuplicateInventoryOperationError):
            service.add_stock(
                product_id=product.id,
                stock_location_id=location.id,
                quantity=Decimal("3"),
                unit_cost=Decimal("100"),
                business_date="2026-09-14",
                idempotency_key=key,
            )

        session.commit()
    finally:
        session.close()

