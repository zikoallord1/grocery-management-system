from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from backend.app.core.database import SessionLocal, initialize_database
from backend.app.core.models import Product, StockLocation, StockMovement, Unit
from backend.app.core.product_units import ProductUnit, SaleItemUnit, PurchaseItemUnit
from backend.app.modules.finance.models import Cashbox, CashboxMovement
from backend.app.modules.inventory.service import InventoryService
from backend.app.modules.purchases.service import PurchaseService
from backend.app.modules.sales.service import SaleService


def _setup_product(session, suffix):
    piece = session.execute(select(Unit).where(Unit.name == "حبة")).scalar_one_or_none()
    carton = session.execute(select(Unit).where(Unit.name == "كرتون")).scalar_one_or_none()
    if piece is None:
        piece = Unit(name="حبة", symbol="حبة")
        session.add(piece)
        session.flush()
    if carton is None:
        carton = Unit(name="كرتون", symbol="كرتون")
        session.add(carton)
        session.flush()
    product = Product(
        sku=f"UNIT-{suffix}-{uuid4().hex[:8]}",
        name=f"اختبار الوحدات {suffix}",
        default_unit_id=piece.id,
        purchase_price=Decimal("10.00"),
        sale_price=Decimal("15.00"),
        minimum_stock=0,
        reorder_level=0,
    )
    session.add(product)
    session.flush()
    return product, piece, carton


def _location(session):
    location = session.execute(
        select(StockLocation)
        .where(StockLocation.is_active.is_(True))
        .order_by(StockLocation.id)
    ).scalars().first()
    if location is None:
        location = StockLocation(
            code=f"TEST-UNIT-{uuid4().hex[:8]}",
            name="مخزن اختبار الوحدات",
        )
        session.add(location)
        session.flush()
    return location


def _seed_cash(session, amount="1000"):
    cashbox = session.execute(
        select(Cashbox).where(Cashbox.code == "CASH")
    ).scalar_one()
    session.add(
        CashboxMovement(
            cashbox_id=cashbox.id,
            movement_type="TEST_OPENING_BALANCE",
            amount=Decimal(str(amount)),
            direction="IN",
            currency="BASE",
            reference_type="TEST",
            reference_id=uuid4().hex,
            business_date=date.today().isoformat(),
            idempotency_key="unit-test-cash-" + uuid4().hex,
        )
    )
    session.flush()


def test_same_unit_name_has_different_factor_per_product():
    initialize_database()
    session = SessionLocal()
    try:
        product_a, _, carton = _setup_product(session, "A")
        product_b, _, carton_b = _setup_product(session, "B")
        session.add_all(
            [
                ProductUnit(product_id=product_a.id, unit_id=carton.id, conversion_factor=20, sale_price=300, purchase_price=200),
                ProductUnit(product_id=product_b.id, unit_id=carton_b.id, conversion_factor=24, sale_price=360, purchase_price=240),
            ]
        )
        session.flush()
        a = session.execute(select(ProductUnit).where(ProductUnit.product_id == product_a.id)).scalar_one()
        b = session.execute(select(ProductUnit).where(ProductUnit.product_id == product_b.id)).scalar_one()
        assert Decimal(str(a.conversion_factor)) == Decimal("20")
        assert Decimal(str(b.conversion_factor)) == Decimal("24")
    finally:
        session.rollback()
        session.close()


def test_sale_uses_product_unit_factor_and_preserves_snapshot():
    initialize_database()
    session = SessionLocal()
    try:
        product, _, carton = _setup_product(session, "SALE")
        location = _location(session)
        session.add(ProductUnit(product_id=product.id, unit_id=carton.id, conversion_factor=20, sale_price=300, purchase_price=200))
        session.flush()
        InventoryService(session).add_stock(
            product_id=product.id,
            stock_location_id=location.id,
            quantity=100,
            unit_cost=Decimal("10"),
            business_date=date.today().isoformat(),
            idempotency_key="unit-test-in-" + uuid4().hex,
            reference_type="TEST",
        )
        _seed_cash(session, "1000")
        sale = SaleService(session).create_sale(
            document_no="SU-" + uuid4().hex[:10],
            business_date=date.today().isoformat(),
            items=[
                {
                    "product_id": product.id,
                    "quantity": "2",
                    "unit_id": carton.id,
                    "unit_price": "300",
                    "discount": "0",
                    "stock_location_id": location.id,
                }
            ],
            payments=[{"payment_method": "CASH", "amount": "600", "currency": "BASE"}],
            idempotency_key="unit-sale-" + uuid4().hex,
        )
        snapshot = session.execute(select(SaleItemUnit).where(SaleItemUnit.sale_item_id == sale.id)).scalar_one()
        assert Decimal(str(snapshot.entered_quantity)) == Decimal("2")
        assert Decimal(str(snapshot.conversion_factor)) == Decimal("20")
        assert Decimal(str(snapshot.base_quantity)) == Decimal("40")
        assert snapshot.unit_name_snapshot == "كرتون"
        movement = session.execute(
            select(StockMovement).where(
                StockMovement.reference_id == str(sale.id),
                StockMovement.direction == "OUT",
            )
        ).scalar_one()
        assert Decimal(str(movement.quantity)) == Decimal("40")
    finally:
        session.rollback()
        session.close()


def test_purchase_normalizes_cost_to_base_unit_and_preserves_snapshot():
    initialize_database()
    session = SessionLocal()
    try:
        product, _, carton = _setup_product(session, "PURCHASE")
        location = _location(session)
        session.add(ProductUnit(product_id=product.id, unit_id=carton.id, conversion_factor=24, sale_price=360, purchase_price=240))
        session.flush()
        _seed_cash(session, "1000")
        purchase = PurchaseService(session).create_purchase(
            document_no="PU-" + uuid4().hex[:10],
            business_date=date.today().isoformat(),
            items=[
                {
                    "product_id": product.id,
                    "quantity": "3",
                    "unit_id": carton.id,
                    "unit_cost": "240",
                    "discount": "0",
                    "stock_location_id": location.id,
                }
            ],
            payments=[{"payment_method": "CASH", "amount": "720", "currency": "BASE"}],
            idempotency_key="unit-purchase-" + uuid4().hex,
        )
        snapshot = session.execute(select(PurchaseItemUnit).where(PurchaseItemUnit.purchase_item_id == purchase.id)).scalar_one()
        assert Decimal(str(snapshot.entered_quantity)) == Decimal("3")
        assert Decimal(str(snapshot.conversion_factor)) == Decimal("24")
        assert Decimal(str(snapshot.base_quantity)) == Decimal("72")
        movement = session.execute(
            select(StockMovement).where(
                StockMovement.reference_id == str(purchase.id),
                StockMovement.direction == "IN",
            )
        ).scalar_one()
        assert Decimal(str(movement.quantity)) == Decimal("72")
        assert Decimal(str(movement.unit_cost)) == Decimal("10")
    finally:
        session.rollback()
        session.close()


def test_product_unit_rejects_non_positive_factor():
    initialize_database()
    session = SessionLocal()
    try:
        product, _, carton = _setup_product(session, "INVALID")
        session.add(ProductUnit(product_id=product.id, unit_id=carton.id, conversion_factor=0))
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()
    finally:
        session.rollback()
        session.close()
