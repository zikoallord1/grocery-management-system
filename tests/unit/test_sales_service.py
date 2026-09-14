import uuid
from decimal import Decimal

import pytest
from sqlalchemy import inspect, select

from backend.app.core.audit_models import AuditLog
from backend.app.core.database import engine, get_session, initialize_database
from backend.app.core.models import Category, Customer, Product, StockLocation, Unit
from backend.app.modules.inventory.service import InventoryService
from backend.app.modules.sales.service import DuplicateSaleError, InvalidSaleError, SaleService


@pytest.fixture(autouse=True)
def clean_database():
    initialize_database()
    from backend.app.core.database import SessionLocal
    from backend.app.modules.finance.models import Cashbox, PaymentMethod

    with engine.begin() as connection:
        tables = set(inspect(engine).get_table_names())
        cleanup_order = [
            "sale_return_items", "purchase_return_items", "sale_returns", "purchase_returns",
            "cashbox_movements", "customer_payments", "customer_account_movements", "sale_payments",
            "sale_items", "sales", "stock_movements", "product_barcodes", "expense_payments", "expenses",
            "purchase_payments", "purchase_items", "purchases", "supplier_payments", "supplier_account_movements",
            "payment_methods", "customers", "suppliers", "products", "stock_locations", "units", "categories",
        ]
        for table in cleanup_order:
            if table in tables:
                connection.exec_driver_sql(f'DELETE FROM "{table}"')

    seed_session = SessionLocal()
    try:
        for code, name, account_type, method_type, method_name in [
            ("CASH", "النقد", "CASH", "CASH", "نقد"),
            ("WALLET", "المحفظة الإلكترونية", "WALLET", "WALLET", "محفظة إلكترونية"),
        ]:
            cash_box = seed_session.query(Cashbox).filter_by(code=code).first()
            if cash_box is None:
                cash_box = Cashbox(code=code, name=name, account_type=account_type, currency="BASE")
                seed_session.add(cash_box); seed_session.flush()
            payment_method = seed_session.query(PaymentMethod).filter_by(code=code).first()
            if payment_method is None:
                seed_session.add(PaymentMethod(code=code, name=method_name, method_type=method_type, cashbox_id=cash_box.id, is_active=True))
        seed_session.commit()
    finally:
        seed_session.close()


def setup_product_and_stock(session):
    category = Category(name="مبيعات")
    unit = Unit(name="حبة مبيع", symbol="حبة")
    location = StockLocation(code="SALE-MAIN", name="مخزن البيع", location_type="STORE")
    session.add_all([category, unit, location]); session.flush()
    product = Product(sku="SALE-001", name="صنف بيع", category_id=category.id, default_unit_id=unit.id, purchase_price=Decimal("80"), sale_price=Decimal("120"))
    session.add(product); session.flush()
    InventoryService(session).add_stock(product_id=product.id, stock_location_id=location.id, quantity=Decimal("10"), unit_cost=Decimal("80"), business_date="2026-09-14", idempotency_key=str(uuid.uuid4()))
    return product, location


def test_create_cash_sale_reduces_stock():
    session = get_session()
    try:
        product, location = setup_product_and_stock(session)
        sale = SaleService(session).create_sale(document_no="S-0001", business_date="2026-09-14", items=[{"product_id": product.id, "stock_location_id": location.id, "quantity": "2", "unit_price": "120", "discount": "0"}], payments=[{"payment_method": "CASH", "amount": "240"}], idempotency_key=str(uuid.uuid4()))
        assert sale.total == Decimal("240.00"); assert sale.paid_amount == Decimal("240.00"); assert sale.credit_amount == Decimal("0.00")
        assert InventoryService(session).get_balance(product.id, location.id) == Decimal("8.000")
        session.commit()
    finally: session.close()


def test_multi_line_sale_creates_all_items_and_reduces_each_stock():
    session = get_session()
    try:
        first, location = setup_product_and_stock(session)
        second = Product(sku="SALE-002", name="صنف بيع ثانٍ", category_id=first.category_id, default_unit_id=first.default_unit_id, purchase_price=Decimal("40"), sale_price=Decimal("70"))
        session.add(second); session.flush()
        InventoryService(session).add_stock(product_id=second.id, stock_location_id=location.id, quantity=Decimal("5"), unit_cost=Decimal("40"), business_date="2026-09-14", idempotency_key=str(uuid.uuid4()))
        sale = SaleService(session).create_sale(
            document_no="S-MULTI-0001", business_date="2026-09-14",
            items=[
                {"product_id": first.id, "stock_location_id": location.id, "quantity": "2", "unit_price": "120", "discount": "0"},
                {"product_id": second.id, "stock_location_id": location.id, "quantity": "3", "unit_price": "70", "discount": "0"},
            ], payments=[{"payment_method": "CASH", "amount": "450"}], idempotency_key=str(uuid.uuid4())
        )
        assert sale.total == Decimal("450.00")
        assert len(sale.items) == 2
        assert InventoryService(session).get_balance(first.id, location.id) == Decimal("8.000")
        assert InventoryService(session).get_balance(second.id, location.id) == Decimal("2.000")
        session.commit()
    finally: session.close()


def test_mixed_payment_is_supported():
    session = get_session()
    try:
        product, location = setup_product_and_stock(session); service = SaleService(session)
        customer = Customer(code="CUST-TEST-MIXED-001", name="test-customer-mixed-payment", phone="0000000000")
        session.add(customer); session.flush()
        sale = service.create_sale(document_no="S-0002", business_date="2026-09-14", customer_id=customer.id, items=[{"product_id": product.id, "stock_location_id": location.id, "quantity": "2", "unit_price": "100", "discount": "0"}], payments=[{"payment_method": "CASH", "amount": "100"}, {"payment_method": "WALLET", "amount": "50"}], idempotency_key=str(uuid.uuid4()))
        assert sale.total == Decimal("200.00"); assert sale.paid_amount == Decimal("150.00"); assert sale.credit_amount == Decimal("50.00"); assert sale.payment_status == "PARTIAL"
        session.commit()
    finally: session.close()


def test_duplicate_sale_is_rejected():
    session = get_session()
    try:
        product, location = setup_product_and_stock(session); service = SaleService(session); key = str(uuid.uuid4())
        payload = dict(document_no="S-0003", business_date="2026-09-14", items=[{"product_id": product.id, "stock_location_id": location.id, "quantity": "1", "unit_price": "100", "discount": "0"}], payments=[{"payment_method": "CASH", "amount": "100"}], idempotency_key=key)
        service.create_sale(**payload); session.commit()
        with pytest.raises(DuplicateSaleError): service.create_sale(**payload)
    finally: session.close()


def test_payment_cannot_exceed_total():
    session = get_session()
    try:
        product, location = setup_product_and_stock(session)
        with pytest.raises(InvalidSaleError): SaleService(session).create_sale(document_no="S-0004", business_date="2026-09-14", items=[{"product_id": product.id, "stock_location_id": location.id, "quantity": "1", "unit_price": "100"}], payments=[{"payment_method": "CASH", "amount": "101"}], idempotency_key=str(uuid.uuid4()))
    finally: session.close()


def test_sale_fails_when_stock_is_insufficient():
    session = get_session()
    try:
        product, location = setup_product_and_stock(session)
        with pytest.raises(Exception): SaleService(session).create_sale(document_no="S-0005", business_date="2026-09-14", items=[{"product_id": product.id, "stock_location_id": location.id, "quantity": "11", "unit_price": "100", "discount": "0"}], payments=[{"payment_method": "CASH", "amount": "1100"}], idempotency_key=str(uuid.uuid4()))
        assert InventoryService(session).get_balance(product.id, location.id) == Decimal("10.000")
    finally: session.close()


def test_sale_publishes_sale_confirmed_event():
    from backend.app.application.business_engine import BusinessEngine
    session = get_session()
    try:
        product, location = setup_product_and_stock(session); engine = BusinessEngine(); received = []
        engine.register_rule(name="TEST_CAPTURE_SALE_CONFIRMED", event_type="SALE_CONFIRMED", handler=lambda current_session, event: (received.append(event) or []))
        sale = SaleService(session, business_engine=engine).create_sale(document_no="S-ENGINE-0001", business_date="2026-09-14", items=[{"product_id": product.id, "stock_location_id": location.id, "quantity": "1", "unit_price": "100", "discount": "0"}], payments=[{"payment_method": "CASH", "amount": "100"}], idempotency_key=str(uuid.uuid4()))
        assert sale.status == "CONFIRMED"; assert len(received) == 1
        event = received[0]; assert event.event_type == "SALE_CONFIRMED"; assert event.operation_id == sale.idempotency_key; assert event.payload["sale_id"] == sale.id; assert event.payload["document_no"] == "S-ENGINE-0001"; assert Decimal(event.payload["total"]) == Decimal("100.00"); assert Decimal(event.payload["paid_amount"]) == Decimal("100.00"); assert Decimal(event.payload["credit_amount"]) == Decimal("0.00"); assert event.payload["payment_status"] == "PAID"
        session.commit()
    finally: session.close()


def test_real_sale_creates_audit_log_automatically():
    session = get_session()
    try:
        product, location = setup_product_and_stock(session); operation_id = str(uuid.uuid4())
        sale = SaleService(session).create_sale(document_no="S-AUDIT-0001", business_date="2026-09-14", items=[{"product_id": product.id, "stock_location_id": location.id, "quantity": "1", "unit_price": "120", "discount": "0"}], payments=[{"payment_method": "CASH", "amount": "120"}], idempotency_key=operation_id)
        audit = session.execute(select(AuditLog).where(AuditLog.operation_id == operation_id, AuditLog.event_type == "SALE_CONFIRMED", AuditLog.action == "EVENT_PROCESSED")).scalar_one_or_none()
        assert sale.status == "CONFIRMED"; assert audit is not None; assert audit.entity_type == "SALE"; assert audit.entity_id == str(sale.id)
        session.rollback()
    finally: session.close()
