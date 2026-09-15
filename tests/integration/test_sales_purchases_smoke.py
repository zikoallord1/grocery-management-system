from datetime import date
from decimal import Decimal
from uuid import uuid4


def test_sales_and_purchases_accept_input():
    from sqlalchemy import select
    from backend.app.core.database import get_session, initialize_database
    from backend.app.core.models import Product, StockLocation, Customer, Supplier
    from backend.app.modules.finance.models import Cashbox
    from backend.app.modules.finance.service import CashboxService
    from backend.app.modules.inventory.service import InventoryService
    from backend.app.modules.sales.service import SaleService
    from backend.app.modules.purchases.service import PurchaseService

    initialize_database()
    suffix = uuid4().hex[:10].upper()
    session = get_session()
    try:
        location = session.scalar(select(StockLocation).where(StockLocation.code == "MAIN"))
        assert location is not None
        product = Product(sku=f"SMK-{suffix}", name=f"صنف مبيعات {suffix}", default_unit_id=1, purchase_price=Decimal("10"), sale_price=Decimal("15"), minimum_stock=Decimal("0"), reorder_level=Decimal("0"), is_active=True)
        session.add(product); session.flush()
        customer = Customer(code=f"SMK-C-{suffix}", name=f"عميل {suffix}", is_active=True)
        supplier = Supplier(code=f"SMK-S-{suffix}", name=f"مورد {suffix}", is_active=True)
        session.add_all([customer, supplier]); session.flush()
        InventoryService(session).add_stock(product_id=product.id, stock_location_id=location.id, quantity=Decimal("20"), unit_cost=Decimal("10"), business_date=date.today().isoformat(), idempotency_key=f"smk-stock-{suffix}")
        cashbox = session.scalar(select(Cashbox).where(Cashbox.code == "CASH")); assert cashbox is not None
        CashboxService(session).move_money(cashbox_id=cashbox.id, amount=Decimal("1000"), direction="IN", movement_type="SMOKE_OPENING", business_date=date.today().isoformat(), idempotency_key=f"smk-cash-{suffix}")
        session.commit()

        sale = SaleService(session).create_sale(
            document_no=f"SMK-SALE-{suffix}", business_date=date.today().isoformat(),
            items=[{"product_id": product.id, "quantity": Decimal("2"), "unit_price": Decimal("15"), "discount": Decimal("0"), "stock_location_id": location.id}],
            payments=[{"payment_method": "CASH", "amount": Decimal("30"), "currency": "BASE"}],
            idempotency_key=f"smk-sale-{suffix}", customer_id=customer.id,
        )
        session.commit(); assert sale.total == Decimal("30.00")

        purchase = PurchaseService(session).create_purchase(
            document_no=f"SMK-PUR-{suffix}", business_date=date.today().isoformat(), supplier_id=supplier.id,
            items=[{"product_id": product.id, "quantity": Decimal("5"), "unit_cost": Decimal("9"), "discount": Decimal("0"), "stock_location_id": location.id}],
            payments=[{"payment_method": "CASH", "amount": Decimal("45"), "currency": "BASE"}],
            idempotency_key=f"smk-pur-{suffix}",
        )
        session.commit(); assert purchase.total == Decimal("45.00")
        assert InventoryService(session).get_balance(product.id, location.id) == Decimal("23.000")
    finally:
        session.rollback(); session.close()
