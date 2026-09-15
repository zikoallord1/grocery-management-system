from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import inspect

from backend.app.core.database import engine, get_session, initialize_database
from backend.app.core.models import (
    Category,
    Customer,
    Product,
    StockLocation,
    Supplier,
    Unit,
)
from backend.app.modules.customers.service import CustomerService
from backend.app.modules.finance.models import PaymentMethod
from backend.app.modules.finance.service import CashboxService
from backend.app.modules.inventory.service import InventoryService
from backend.app.modules.purchases.service import PurchaseService
from backend.app.modules.sales.service import SaleService
from backend.app.modules.suppliers.service import SupplierService


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
            "payment_methods",
            "cashboxes",
            "stock_movements",
            "product_barcodes",
            "products",
            "stock_locations",
            "units",
            "categories",
            "customers",
            "suppliers",
        ]:
            if table in tables:
                connection.exec_driver_sql(f'DELETE FROM "{table}"')


def setup_sales_environment(session):
    category = Category(name="تكامل بيع")
    unit = Unit(name="حبة تكامل", symbol="حبة")
    location = StockLocation(
        code="INT-SALE",
        name="مخزن التكامل",
        location_type="STORE",
    )
    customer = Customer(
        code="INT-CUS",
        name="عميل التكامل",
        credit_limit=Decimal("5000"),
    )

    session.add_all([category, unit, location, customer])
    session.flush()

    product = Product(
        sku="INT-SALE-001",
        name="صنف تكامل بيع",
        category_id=category.id,
        default_unit_id=unit.id,
        purchase_price=Decimal("50"),
        sale_price=Decimal("100"),
    )
    session.add(product)
    session.flush()

    inventory = InventoryService(session)

    inventory.add_stock(
        product_id=product.id,
        stock_location_id=location.id,
        quantity=Decimal("20"),
        unit_cost=Decimal("50"),
        business_date="2026-09-14",
        idempotency_key=str(uuid4()),
    )

    finance = CashboxService(session)

    cash = finance.create_cashbox(
        code="INT-CASH",
        name="نقد التكامل",
        account_type="CASH",
    )

    wallet = finance.create_cashbox(
        code="INT-WALLET",
        name="محفظة التكامل",
        account_type="WALLET",
        provider_name="محفظة",
    )

    cash_method = finance.create_payment_method(
        code="INT-CASH-METHOD",
        name="نقد التكامل",
        method_type="CASH",
        cashbox_id=cash.id,
    )

    wallet_method = finance.create_payment_method(
        code="INT-WALLET-METHOD",
        name="محفظة التكامل",
        method_type="E_WALLET",
        cashbox_id=wallet.id,
    )

    return (
        product,
        location,
        customer,
        cash,
        wallet,
        cash_method,
        wallet_method,
    )


def setup_purchase_environment(session):
    category = Category(name="تكامل شراء")
    unit = Unit(name="كرتون تكامل", symbol="كرتون")
    location = StockLocation(
        code="INT-PUR",
        name="مخزن شراء التكامل",
        location_type="STORE",
    )
    supplier = Supplier(
        code="INT-SUP",
        name="مورد التكامل",
        credit_limit=Decimal("5000"),
    )

    session.add_all([category, unit, location, supplier])
    session.flush()

    product = Product(
        sku="INT-PUR-001",
        name="صنف تكامل شراء",
        category_id=category.id,
        default_unit_id=unit.id,
        purchase_price=Decimal("100"),
        sale_price=Decimal("140"),
    )
    session.add(product)
    session.flush()

    finance = CashboxService(session)

    cash = finance.create_cashbox(
        code="INT-PUR-CASH",
        name="نقد مشتريات",
        account_type="CASH",
    )

    wallet = finance.create_cashbox(
        code="INT-PUR-WALLET",
        name="محفظة مشتريات",
        account_type="WALLET",
        provider_name="محفظة شراء",
    )

    cash_method = finance.create_payment_method(
        code="INT-PUR-CASH-METHOD",
        name="نقد شراء",
        method_type="CASH",
        cashbox_id=cash.id,
    )

    wallet_method = finance.create_payment_method(
        code="INT-PUR-WALLET-METHOD",
        name="محفظة شراء",
        method_type="E_WALLET",
        cashbox_id=wallet.id,
    )

    finance.move_money(
        cashbox_id=cash.id,
        amount=2000,
        direction="IN",
        movement_type="OPENING_BALANCE",
        business_date="2026-09-14",
        idempotency_key=str(uuid4()),
    )

    finance.move_money(
        cashbox_id=wallet.id,
        amount=2000,
        direction="IN",
        movement_type="OPENING_BALANCE",
        business_date="2026-09-14",
        idempotency_key=str(uuid4()),
    )

    return (
        product,
        location,
        supplier,
        cash,
        wallet,
        cash_method,
        wallet_method,
    )


def test_cash_sale_updates_cashbox_and_stock():
    session = get_session()

    try:
        (
            product,
            location,
            customer,
            cash,
            wallet,
            cash_method,
            wallet_method,
        ) = setup_sales_environment(session)

        sale = SaleService(session).create_sale(
            document_no="INT-SALE-001",
            customer_id=customer.id,
            business_date="2026-09-14",
            items=[
                {
                    "product_id": product.id,
                    "stock_location_id": location.id,
                    "quantity": "2",
                    "unit_price": "100",
                }
            ],
            payments=[
                {
                    "payment_method": cash_method.code,
                    "amount": "200",
                }
            ],
            idempotency_key=str(uuid4()),
        )

        assert sale.credit_amount == Decimal("0.00")

        assert CashboxService(session).get_balance(
            cash.id
        ) == Decimal("200.00")

        assert InventoryService(session).get_balance(
            product.id,
            location.id,
        ) == Decimal("18.000")

        session.commit()

    finally:
        session.close()


def test_wallet_sale_updates_wallet():
    session = get_session()

    try:
        (
            product,
            location,
            customer,
            cash,
            wallet,
            cash_method,
            wallet_method,
        ) = setup_sales_environment(session)

        sale = SaleService(session).create_sale(
            document_no="INT-SALE-002",
            customer_id=customer.id,
            business_date="2026-09-14",
            items=[
                {
                    "product_id": product.id,
                    "stock_location_id": location.id,
                    "quantity": "3",
                    "unit_price": "100",
                }
            ],
            payments=[
                {
                    "payment_method": wallet_method.code,
                    "amount": "300",
                }
            ],
            idempotency_key=str(uuid4()),
        )

        assert sale.paid_amount == Decimal("300.00")
        assert CashboxService(session).get_balance(
            wallet.id
        ) == Decimal("300.00")

        session.commit()

    finally:
        session.close()


def test_mixed_sale_updates_cash_wallet_and_customer():
    session = get_session()

    try:
        (
            product,
            location,
            customer,
            cash,
            wallet,
            cash_method,
            wallet_method,
        ) = setup_sales_environment(session)

        SaleService(session).create_sale(
            document_no="INT-SALE-003",
            customer_id=customer.id,
            business_date="2026-09-14",
            items=[
                {
                    "product_id": product.id,
                    "stock_location_id": location.id,
                    "quantity": "5",
                    "unit_price": "100",
                }
            ],
            payments=[
                {
                    "payment_method": cash_method.code,
                    "amount": "200",
                },
                {
                    "payment_method": wallet_method.code,
                    "amount": "150",
                },
            ],
            idempotency_key=str(uuid4()),
        )

        assert CashboxService(session).get_balance(
            cash.id
        ) == Decimal("200.00")

        assert CashboxService(session).get_balance(
            wallet.id
        ) == Decimal("150.00")

        assert CustomerService(session).get_balance(
            customer.id
        ) == Decimal("150.00")

        session.commit()

    finally:
        session.close()


def test_credit_sale_updates_customer_without_cashbox():
    session = get_session()

    try:
        (
            product,
            location,
            customer,
            cash,
            wallet,
            cash_method,
            wallet_method,
        ) = setup_sales_environment(session)

        SaleService(session).create_sale(
            document_no="INT-SALE-004",
            customer_id=customer.id,
            business_date="2026-09-14",
            items=[
                {
                    "product_id": product.id,
                    "stock_location_id": location.id,
                    "quantity": "2",
                    "unit_price": "100",
                }
            ],
            payments=[],
            idempotency_key=str(uuid4()),
        )

        assert CustomerService(session).get_balance(
            customer.id
        ) == Decimal("200.00")

        assert CashboxService(session).get_balance(
            cash.id
        ) == Decimal("0.00")

        assert CashboxService(session).get_balance(
            wallet.id
        ) == Decimal("0.00")

        session.commit()

    finally:
        session.close()


def test_cash_purchase_updates_cashbox_and_stock():
    session = get_session()

    try:
        (
            product,
            location,
            supplier,
            cash,
            wallet,
            cash_method,
            wallet_method,
        ) = setup_purchase_environment(session)

        PurchaseService(session).create_purchase(
            document_no="INT-PUR-001",
            supplier_id=supplier.id,
            business_date="2026-09-14",
            items=[
                {
                    "product_id": product.id,
                    "stock_location_id": location.id,
                    "quantity": "5",
                    "unit_cost": "100",
                }
            ],
            payments=[
                {
                    "payment_method": cash_method.code,
                    "amount": "500",
                }
            ],
            idempotency_key=str(uuid4()),
        )

        assert InventoryService(session).get_balance(
            product.id,
            location.id,
        ) == Decimal("5.000")

        assert CashboxService(session).get_balance(
            cash.id
        ) == Decimal("1500.00")

        assert SupplierService(session).get_balance(
            supplier.id
        ) == Decimal("0.00")

        session.commit()

    finally:
        session.close()


def test_mixed_purchase_updates_wallet_and_supplier():
    session = get_session()

    try:
        (
            product,
            location,
            supplier,
            cash,
            wallet,
            cash_method,
            wallet_method,
        ) = setup_purchase_environment(session)

        PurchaseService(session).create_purchase(
            document_no="INT-PUR-002",
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
                    "payment_method": wallet_method.code,
                    "amount": "700",
                }
            ],
            idempotency_key=str(uuid4()),
        )

        assert CashboxService(session).get_balance(
            wallet.id
        ) == Decimal("1300.00")

        assert SupplierService(session).get_balance(
            supplier.id
        ) == Decimal("300.00")

        session.commit()

    finally:
        session.close()


def test_credit_purchase_updates_supplier_without_cashbox_outflow():
    session = get_session()

    try:
        (
            product,
            location,
            supplier,
            cash,
            wallet,
            cash_method,
            wallet_method,
        ) = setup_purchase_environment(session)

        PurchaseService(session).create_purchase(
            document_no="INT-PUR-003",
            supplier_id=supplier.id,
            business_date="2026-09-14",
            items=[
                {
                    "product_id": product.id,
                    "stock_location_id": location.id,
                    "quantity": "4",
                    "unit_cost": "100",
                }
            ],
            payments=[],
            idempotency_key=str(uuid4()),
        )

        assert SupplierService(session).get_balance(
            supplier.id
        ) == Decimal("400.00")

        assert CashboxService(session).get_balance(
            cash.id
        ) == Decimal("2000.00")

        assert CashboxService(session).get_balance(
            wallet.id
        ) == Decimal("2000.00")

        session.commit()

    finally:
        session.close()
