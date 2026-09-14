import uuid
from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import inspect

from backend.app.core.database import engine, get_session, initialize_database
from backend.app.core.models import Category, Customer, Product, StockLocation, Unit
from backend.app.modules.customers.service import CustomerCreditError, CustomerError, CustomerService, DuplicateCustomerOperationError
from backend.app.modules.finance.models import Cashbox, CashboxMovement, PaymentMethod
from backend.app.modules.inventory.service import InventoryService
from backend.app.modules.sales.service import SaleService


@pytest.fixture(autouse=True)
def clean_database():
    initialize_database()
    with engine.begin() as connection:
        tables = set(inspect(engine).get_table_names())
        cleanup_order = [
            "cashbox_movements", "expense_payments", "expenses", "purchase_payments",
            "purchase_items", "purchases", "supplier_payments", "supplier_account_movements",
            "sale_payments", "sale_items", "sales", "customer_payments",
            "customer_account_movements", "stock_movements", "product_barcodes",
            "customers", "suppliers", "products", "stock_locations", "units", "categories",
        ]
        for table in cleanup_order:
            if table in tables:
                connection.exec_driver_sql(f'DELETE FROM "{table}"')

    session = get_session()
    try:
        cashbox = session.query(Cashbox).filter_by(code="CASH").first()
        if cashbox is None:
            raise RuntimeError("Default CASH cashbox was not created")
        method = session.query(PaymentMethod).filter_by(code="CASH").first()
        if method is None:
            method = PaymentMethod(code="CASH", name="نقد", method_type="CASH", cashbox_id=cashbox.id, is_active=True)
            session.add(method)
        session.add(CashboxMovement(
            cashbox_id=cashbox.id,
            movement_type="OPENING_BALANCE",
            amount=100000,
            direction="IN",
            currency="BASE",
            business_date=date.today().isoformat(),
            idempotency_key=f"TEST-CUSTOMER-OPENING-{uuid4()}",
        ))
        session.commit()
    finally:
        session.close()


def setup_customer_product_stock(session, credit_limit=None):
    customer = Customer(code="CUS-001", name="عميل تجريبي", credit_limit=credit_limit)
    category = Category(name="عملاء")
    unit = Unit(name="قطعة", symbol="قطعة")
    location = StockLocation(code="CUS-MAIN", name="المخزن الرئيسي", location_type="STORE")
    session.add_all([customer, category, unit, location])
    session.flush()
    product = Product(
        sku="CUS-P-001", name="صنف للعميل", category_id=category.id,
        default_unit_id=unit.id, purchase_price=Decimal("50"), sale_price=Decimal("100"),
    )
    session.add(product)
    session.flush()
    InventoryService(session).add_stock(
        product_id=product.id, stock_location_id=location.id, quantity=Decimal("20"),
        unit_cost=Decimal("50"), business_date="2026-09-14", idempotency_key=str(uuid4()),
    )
    return customer, product, location


def test_customer_credit_increases_balance():
    session = get_session()
    try:
        customer, _, _ = setup_customer_product_stock(session, credit_limit=Decimal("1000"))
        service = CustomerService(session)
        service.register_sale_credit(customer_id=customer.id, amount=Decimal("300"), business_date="2026-09-14", reference_id="SALE-001", idempotency_key=str(uuid4()))
        assert service.get_balance(customer.id) == Decimal("300.00")
        session.commit()
    finally:
        session.close()


def test_customer_payment_reduces_balance_and_increases_cashbox():
    session = get_session()
    try:
        customer, _, _ = setup_customer_product_stock(session, credit_limit=Decimal("1000"))
        service = CustomerService(session)
        service.register_sale_credit(customer_id=customer.id, amount=Decimal("300"), business_date="2026-09-14", reference_id="SALE-002", idempotency_key=str(uuid4()))
        before = service._session.query(CashboxMovement).filter(CashboxMovement.movement_type == "OPENING_BALANCE").one().amount
        service.receive_payment(customer_id=customer.id, amount=Decimal("100"), business_date="2026-09-14", payment_method="CASH", idempotency_key=str(uuid.uuid4()))
        assert service.get_balance(customer.id) == Decimal("200.00")
        cashbox = service._session.query(Cashbox).filter_by(code="CASH").one()
        from backend.app.modules.finance.service import CashboxService
        assert CashboxService(session).get_balance(cashbox.id) == Decimal(str(before)) + Decimal("100.00")
        session.commit()
    finally:
        session.close()


def test_credit_limit_is_enforced():
    session = get_session()
    try:
        customer, _, _ = setup_customer_product_stock(session, credit_limit=Decimal("200"))
        with pytest.raises(CustomerCreditError):
            CustomerService(session).register_sale_credit(customer_id=customer.id, amount=Decimal("250"), business_date="2026-09-14", reference_id="SALE-003", idempotency_key=str(uuid.uuid4()))
    finally:
        session.close()


def test_payment_cannot_exceed_balance():
    session = get_session()
    try:
        customer, _, _ = setup_customer_product_stock(session, credit_limit=Decimal("1000"))
        service = CustomerService(session)
        service.register_sale_credit(customer_id=customer.id, amount=Decimal("200"), business_date="2026-09-14", reference_id="SALE-004", idempotency_key=str(uuid.uuid4()))
        with pytest.raises(CustomerError):
            service.receive_payment(customer_id=customer.id, amount=Decimal("250"), business_date="2026-09-14", payment_method="CASH", idempotency_key=str(uuid.uuid4()))
    finally:
        session.close()


def test_duplicate_customer_payment_is_rejected():
    session = get_session()
    try:
        customer, _, _ = setup_customer_product_stock(session, credit_limit=Decimal("1000"))
        service = CustomerService(session)
        service.register_sale_credit(customer_id=customer.id, amount=Decimal("300"), business_date="2026-09-14", reference_id="SALE-005", idempotency_key=str(uuid.uuid4()))
        key = str(uuid.uuid4())
        service.receive_payment(customer_id=customer.id, amount=Decimal("100"), business_date="2026-09-14", payment_method="CASH", idempotency_key=key)
        with pytest.raises(DuplicateCustomerOperationError):
            service.receive_payment(customer_id=customer.id, amount=Decimal("100"), business_date="2026-09-14", payment_method="CASH", idempotency_key=key)
    finally:
        session.close()


def test_credit_sale_requires_customer():
    session = get_session()
    try:
        _, product, location = setup_customer_product_stock(session)
        with pytest.raises(Exception):
            SaleService(session).create_sale(
                document_no="CREDIT-001", business_date="2026-09-14", customer_id=None,
                items=[{"product_id": product.id, "stock_location_id": location.id, "quantity": "2", "unit_price": "100"}],
                payments=[{"payment_method": "CASH", "amount": "100"}], idempotency_key=str(uuid.uuid4()),
            )
    finally:
        session.close()
