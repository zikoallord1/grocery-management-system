from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import inspect, select

from backend.app.core.database import engine, get_session, initialize_database
from backend.app.core.models import Category, Product, Sale, SaleItem, StockLocation, StockMovement, Unit
from backend.app.modules.finance.models import Cashbox
from backend.app.modules.finance.service import CashboxService
from backend.app.modules.inventory.service import InventoryService
from backend.app.modules.returns.models import PurchaseReturn, SaleReturn, SaleReturnItem
from backend.app.modules.returns.service import ReturnError, ReturnService


@pytest.fixture(autouse=True)
def clean_returns_data():
    initialize_database()
    with engine.begin() as connection:
        tables = set(inspect(engine).get_table_names())
        for table in [
            "sale_return_items", "sale_returns", "purchase_return_items", "purchase_returns",
            "sale_payments", "sale_items", "sales", "stock_movements", "products", "units", "categories", "stock_locations"
        ]:
            if table in tables:
                connection.exec_driver_sql(f'DELETE FROM "{table}"')


def setup_product(session):
    category = Category(name="مرتجعات")
    unit = Unit(name="حبة", symbol="حبة")
    location = StockLocation(code="RET-MAIN", name="مخزن المرتجعات", location_type="STORE")
    product = Product(sku="RET-001", name="صنف مرتجع", category=category, default_unit_id=None, purchase_price=Decimal("60"), sale_price=Decimal("100"))
    session.add_all([category, unit, location])
    session.flush()
    product.default_unit_id = unit.id
    session.add(product)
    session.flush()
    return product, location


def create_cash_sale(session, product, location, quantity=Decimal("5"), paid=Decimal("500")):
    sale = Sale(document_no=f"S-RET-{uuid4().hex[:8]}", business_date="2026-09-14", subtotal=paid, discount=0, tax=0,
                total=paid, paid_amount=paid, credit_amount=0, status="CONFIRMED", payment_status="PAID", idempotency_key=str(uuid4()))
    session.add(sale); session.flush()
    item = SaleItem(sale_id=sale.id, product_id=product.id, quantity=quantity, unit_price=Decimal("100"), discount=0, total=paid, cost_price_snapshot=Decimal("60"))
    session.add(item)
    InventoryService(session).add_stock(product_id=product.id, stock_location_id=location.id, quantity=quantity, unit_cost=Decimal("60"), business_date="2026-09-14", idempotency_key=str(uuid4()), reference_type="OPENING_STOCK", reference_id=str(sale.id))
    InventoryService(session).remove_stock(product_id=product.id, stock_location_id=location.id, quantity=quantity, unit_cost=Decimal("60"), business_date="2026-09-14", idempotency_key=str(uuid4()), reference_type="SALE", reference_id=str(sale.id))
    session.flush()
    return sale, item


def test_sale_return_restores_stock_and_refunds_cash():
    session = get_session()
    try:
        product, location = setup_product(session)
        cash = session.execute(select(Cashbox).where(Cashbox.code == "CASH")).scalar_one()
        CashboxService(session).move_money(cashbox_id=cash.id, amount=Decimal("1000"), direction="IN", movement_type="TEST_OPENING", business_date="2026-09-14", idempotency_key=str(uuid4()), reference_type="TEST")
        sale, item = create_cash_sale(session, product, location)
        before_cash = CashboxService(session).get_balance(cash.id)

        result = ReturnService(session).return_sale(
            sale_id=sale.id,
            items=[{"sale_item_id": item.id, "quantity": "2"}],
            business_date="2026-09-14",
            document_no="SR-0001",
            refund_payment_method="CASH",
            idempotency_key=str(uuid4()),
        )
        session.commit()

        assert result.total == Decimal("200.00")
        assert result.refunded_amount == Decimal("200.00")
        assert result.credit_reduction == Decimal("0.00")
        assert InventoryService(session).get_balance(product.id, location.id) == Decimal("2.000")
        assert CashboxService(session).get_balance(cash.id) == before_cash - Decimal("200.00")
    finally:
        session.close()


def test_sale_return_cannot_exceed_remaining_quantity():
    session = get_session()
    try:
        product, location = setup_product(session)
        cash = session.execute(select(Cashbox).where(Cashbox.code == "CASH")).scalar_one()
        CashboxService(session).move_money(cashbox_id=cash.id, amount=Decimal("1000"), direction="IN", movement_type="TEST_OPENING", business_date="2026-09-14", idempotency_key=str(uuid4()), reference_type="TEST")
        sale, item = create_cash_sale(session, product, location)
        key = str(uuid4())
        ReturnService(session).return_sale(sale_id=sale.id, items=[{"sale_item_id": item.id, "quantity": "5"}], business_date="2026-09-14", document_no="SR-0002", refund_payment_method="CASH", idempotency_key=key)
        session.commit()
        with pytest.raises(ReturnError):
            ReturnService(session).return_sale(sale_id=sale.id, items=[{"sale_item_id": item.id, "quantity": "1"}], business_date="2026-09-14", document_no="SR-0003", refund_payment_method="CASH", idempotency_key=str(uuid4()))
    finally:
        session.close()
