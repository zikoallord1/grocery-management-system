from decimal import Decimal
from uuid import uuid4

import pytest

from backend.app.core.database import get_session, initialize_database
from backend.app.core.models import Category, Product, StockLocation, Unit
from backend.app.modules.inventory.service import InsufficientStockError, InventoryError, InventoryService


def setup_inventory(session):
    category = Category(name=f"اختبار مخزون {uuid4().hex[:8]}")
    unit = Unit(name=f"حبة {uuid4().hex[:8]}", symbol="حبة")
    source = StockLocation(code=f"SRC-{uuid4().hex[:8]}", name="مخزن المصدر", location_type="STORE")
    target = StockLocation(code=f"DST-{uuid4().hex[:8]}", name="مخزن الهدف", location_type="STORE")
    session.add_all([category, unit, source, target])
    session.flush()
    product = Product(sku=f"TR-{uuid4().hex[:8]}", name="صنف تحويل", category_id=category.id, default_unit_id=unit.id, purchase_price=Decimal("10"), sale_price=Decimal("15"))
    session.add(product)
    session.flush()
    InventoryService(session).add_stock(product_id=product.id, stock_location_id=source.id, quantity=Decimal("10"), unit_cost=Decimal("10"), business_date="2026-09-14", idempotency_key=str(uuid4()), reference_type="OPENING_STOCK")
    return product, source, target


def test_transfer_is_atomic_and_updates_both_locations():
    initialize_database()
    session = get_session()
    try:
        product, source, target = setup_inventory(session)
        key = str(uuid4())
        InventoryService(session).transfer_stock(product_id=product.id, source_location_id=source.id, target_location_id=target.id, quantity=Decimal("4"), unit_cost=Decimal("10"), business_date="2026-09-14", idempotency_key=key)
        assert InventoryService(session).get_balance(product.id, source.id) == Decimal("6.000")
        assert InventoryService(session).get_balance(product.id, target.id) == Decimal("4.000")
        session.commit()
    finally:
        session.close()


def test_transfer_rejects_insufficient_stock_without_partial_movement():
    initialize_database()
    session = get_session()
    try:
        product, source, target = setup_inventory(session)
        with pytest.raises(InsufficientStockError):
            InventoryService(session).transfer_stock(product_id=product.id, source_location_id=source.id, target_location_id=target.id, quantity=Decimal("11"), unit_cost=Decimal("10"), business_date="2026-09-14", idempotency_key=str(uuid4()))
        assert InventoryService(session).get_balance(product.id, source.id) == Decimal("10.000")
        assert InventoryService(session).get_balance(product.id, target.id) == Decimal("0.000")
    finally:
        session.rollback()
        session.close()


def test_stock_adjustment_sets_actual_quantity():
    initialize_database()
    session = get_session()
    try:
        product, source, _ = setup_inventory(session)
        movement = InventoryService(session).adjust_stock(product_id=product.id, stock_location_id=source.id, actual_quantity=Decimal("7"), unit_cost=Decimal("10"), business_date="2026-09-14", idempotency_key=str(uuid4()), reason="جرد فعلي")
        assert movement.direction == "OUT"
        assert movement.movement_type == "ADJUSTMENT_OUT"
        assert InventoryService(session).get_balance(product.id, source.id) == Decimal("7.000")
        session.commit()
    finally:
        session.close()


def test_adjustment_can_increase_stock_and_same_location_is_invalid_for_transfer():
    initialize_database()
    session = get_session()
    try:
        product, source, _ = setup_inventory(session)
        InventoryService(session).adjust_stock(product_id=product.id, stock_location_id=source.id, actual_quantity=Decimal("13"), unit_cost=Decimal("10"), business_date="2026-09-14", idempotency_key=str(uuid4()), reason="جرد فعلي")
        assert InventoryService(session).get_balance(product.id, source.id) == Decimal("13.000")
        with pytest.raises(InventoryError):
            InventoryService(session).transfer_stock(product_id=product.id, source_location_id=source.id, target_location_id=source.id, quantity=Decimal("1"), unit_cost=Decimal("10"), business_date="2026-09-14", idempotency_key=str(uuid4()))
        session.rollback()
    finally:
        session.close()
