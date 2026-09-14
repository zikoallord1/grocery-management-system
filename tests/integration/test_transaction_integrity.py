from uuid import uuid4

import pytest
from sqlalchemy import select

from backend.app.core.database import get_session, initialize_database
from backend.app.core.models import Purchase, Sale
from backend.app.modules.inventory.service import InventoryService
from backend.app.modules.purchases.service import PurchaseService
from backend.app.modules.sales.service import SaleService
from tests.unit.test_purchases_suppliers import setup_supplier_and_product
from tests.unit.test_sales_service import setup_product_and_stock


@pytest.fixture(autouse=True)
def initialize_db():
    initialize_database()


def test_sale_failure_rolls_back_sale_and_side_effects(monkeypatch):
    setup_session = get_session()
    try:
        product, location = setup_product_and_stock(setup_session)
        setup_session.commit()
    finally:
        setup_session.close()

    operation_id = str(uuid4())

    def fail_after_operation(*args, **kwargs):
        raise RuntimeError("forced inventory failure")

    monkeypatch.setattr(InventoryService, "remove_stock", fail_after_operation)

    service = SaleService()
    try:
        with pytest.raises(RuntimeError, match="forced inventory failure"):
            service.create_sale(
                document_no="TX-ROLLBACK-SALE",
                business_date="2026-09-14",
                items=[
                    {
                        "product_id": product.id,
                        "stock_location_id": location.id,
                        "quantity": "1",
                        "unit_price": "120",
                        "discount": "0",
                    }
                ],
                payments=[],
                idempotency_key=operation_id,
            )
    finally:
        service._session.close()

    session = get_session()
    try:
        assert session.execute(
            select(Sale.id).where(Sale.idempotency_key == operation_id)
        ).scalar_one_or_none() is None
    finally:
        session.close()


def test_purchase_failure_rolls_back_purchase_and_side_effects(monkeypatch):
    setup_session = get_session()
    try:
        supplier, product, location = setup_supplier_and_product(setup_session)
        setup_session.commit()
    finally:
        setup_session.close()

    operation_id = str(uuid4())

    def fail_after_operation(*args, **kwargs):
        raise RuntimeError("forced inventory failure")

    monkeypatch.setattr(InventoryService, "add_stock", fail_after_operation)

    service = PurchaseService()
    try:
        with pytest.raises(RuntimeError, match="forced inventory failure"):
            service.create_purchase(
                document_no="TX-ROLLBACK-PURCHASE",
                business_date="2026-09-14",
                supplier_id=supplier.id,
                items=[
                    {
                        "product_id": product.id,
                        "stock_location_id": location.id,
                        "quantity": "1",
                        "unit_cost": "100",
                        "discount": "0",
                    }
                ],
                payments=[],
                idempotency_key=operation_id,
            )
    finally:
        service._session.close()

    session = get_session()
    try:
        assert session.execute(
            select(Purchase.id).where(Purchase.idempotency_key == operation_id)
        ).scalar_one_or_none() is None
    finally:
        session.close()
