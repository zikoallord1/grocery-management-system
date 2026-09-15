from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import inspect

from backend.app.core.database import get_session, initialize_database, engine
from backend.app.core.models import (
    Category,
    Product,
    ProductBarcode,
    StockLocation,
    StockMovement,
    Unit,
)

TABLE_DELETE_ORDER = [
    "stock_movements",
    "product_barcodes",
    "products",
    "stock_locations",
    "units",
    "categories",
]


@pytest.fixture(autouse=True)
def setup_database():
    initialize_database()

    with engine.begin() as connection:
        existing_tables = set(inspect(engine).get_table_names())

        for table in TABLE_DELETE_ORDER:
            if table in existing_tables:
                connection.exec_driver_sql(
                    f'DELETE FROM "{table}"'
                )


def create_product(session):
    category = Category(name="مواد غذائية")
    unit = Unit(name="حبة", symbol="حبة")
    session.add_all([category, unit])
    session.flush()

    product = Product(
        sku="TEST-001",
        name="صنف تجريبي",
        category_id=category.id,
        default_unit_id=unit.id,
        purchase_price=Decimal("100.00"),
        sale_price=Decimal("120.00"),
    )
    session.add(product)
    session.flush()
    return product


def create_location(session):
    location = StockLocation(
        code="MAIN",
        name="المخزن الرئيسي",
        location_type="STORE",
    )
    session.add(location)
    session.flush()
    return location


def test_core_tables_exist():
    initialize_database()

    inspector = inspect(engine)
    tables = set(inspector.get_table_names())

    expected = {
        "categories",
        "units",
        "products",
        "product_barcodes",
        "stock_locations",
        "stock_movements",
    }

    assert expected.issubset(tables)


def test_product_and_barcode():
    session = get_session()
    try:
        product = create_product(session)

        barcode = ProductBarcode(
            product_id=product.id,
            barcode="628000000001",
            barcode_type="EAN",
            is_primary=True,
        )
        session.add(barcode)
        session.commit()

        saved = session.query(ProductBarcode).filter_by(
            barcode="628000000001"
        ).one()

        assert saved.product_id == product.id
    finally:
        session.close()


def test_duplicate_barcode_is_rejected():
    session = get_session()
    try:
        product = create_product(session)

        session.add(
            ProductBarcode(
                product_id=product.id,
                barcode="628000000002",
                is_primary=True,
            )
        )
        session.commit()

        session.add(
            ProductBarcode(
                product_id=product.id,
                barcode="628000000002",
                is_primary=False,
            )
        )

        from sqlalchemy.exc import IntegrityError

        with pytest.raises(IntegrityError):
            session.commit()

        session.rollback()
    finally:
        session.close()


def test_stock_movement_accepts_positive_quantity():
    session = get_session()
    try:
        product = create_product(session)
        location = create_location(session)

        movement = StockMovement(
            product_id=product.id,
            stock_location_id=location.id,
            movement_type="OPENING_BALANCE",
            quantity=Decimal("10"),
            direction="IN",
            unit_cost=Decimal("100"),
            reference_type="OPENING",
            reference_id="OPEN-001",
            business_date="2026-09-14",
            idempotency_key=str(uuid4()),
        )

        session.add(movement)
        session.commit()

        saved = session.query(StockMovement).one()

        assert saved.quantity == Decimal("10.000")
        assert saved.direction == "IN"
    finally:
        session.close()


def test_stock_movement_rejects_zero_quantity():
    session = get_session()
    try:
        product = create_product(session)
        location = create_location(session)

        movement = StockMovement(
            product_id=product.id,
            stock_location_id=location.id,
            movement_type="OPENING_BALANCE",
            quantity=Decimal("0"),
            direction="IN",
            unit_cost=Decimal("100"),
            business_date="2026-09-14",
            idempotency_key=str(uuid4()),
        )

        session.add(movement)

        from sqlalchemy.exc import IntegrityError

        with pytest.raises(IntegrityError):
            session.commit()

        session.rollback()
    finally:
        session.close()


def test_idempotency_key_is_unique():
    session = get_session()
    try:
        product = create_product(session)
        location = create_location(session)
        key = str(uuid4())

        first = StockMovement(
            product_id=product.id,
            stock_location_id=location.id,
            movement_type="OPENING_BALANCE",
            quantity=Decimal("5"),
            direction="IN",
            unit_cost=Decimal("100"),
            business_date="2026-09-14",
            idempotency_key=key,
        )

        second = StockMovement(
            product_id=product.id,
            stock_location_id=location.id,
            movement_type="OPENING_BALANCE",
            quantity=Decimal("5"),
            direction="IN",
            unit_cost=Decimal("100"),
            business_date="2026-09-14",
            idempotency_key=key,
        )

        session.add(first)
        session.commit()

        session.add(second)

        from sqlalchemy.exc import IntegrityError

        with pytest.raises(IntegrityError):
            session.commit()

        session.rollback()
    finally:
        session.close()
