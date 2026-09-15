from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import delete, text, select

from backend.app.core.database import DATA_DIR, Base, SessionLocal, initialize_database
from backend.app.core.models import (
    Category, Customer, CustomerAccountMovement, CustomerPayment, Product,
    ProductBarcode, Purchase, PurchaseItem, PurchasePayment, Sale, SaleItem,
    SalePayment, StockLocation, StockMovement, Supplier, SupplierAccountMovement,
    SupplierPayment, Unit,
)
from backend.app.modules.finance.models import Cashbox, PaymentMethod, ExpenseCategory, Expense
from backend.app.modules.finance.revenue import Revenue

DEMO_MARKER = DATA_DIR / "demo_data.json"


def _key():
    return str(uuid4())


def seed_demo_data() -> dict[str, int]:
    initialize_database()
    session = SessionLocal()
    today = date.today().isoformat()
    try:
        unit = session.scalar(select(Unit).where(Unit.name == "قطعة"))
        if unit is None:
            unit = Unit(name="قطعة", symbol="قطعة", is_active=True)
            session.add(unit); session.flush()
        box = session.scalar(select(StockLocation).where(StockLocation.code == "MAIN"))
        if box is None:
            box = StockLocation(code="MAIN", name="المخزن الرئيسي", location_type="STORE", is_active=True)
            session.add(box); session.flush()
        cat = session.scalar(select(Category).where(Category.name == "مواد غذائية"))
        if cat is None:
            cat = Category(name="مواد غذائية", description="بيانات اختبارية", is_active=True)
            session.add(cat); session.flush()

        products = []
        for sku, name, purchase, sale, qty, barcode in [
            ("DEMO-001", "مياه معدنية 500 مل", 80, 100, 120, "6281000000011"),
            ("DEMO-002", "عصير برتقال", 150, 200, 80, "6281000000028"),
            ("DEMO-003", "بسكويت شوكولاتة", 120, 175, 60, "6281000000035"),
            ("DEMO-004", "سكر 1 كجم", 650, 750, 40, "6281000000042"),
            ("DEMO-005", "أرز 5 كجم", 3200, 3700, 25, "6281000000059"),
        ]:
            product = session.scalar(select(Product).where(Product.sku == sku))
            if product is None:
                product = Product(sku=sku, name=name, category_id=cat.id, default_unit_id=unit.id,
                                  purchase_price=Decimal(purchase), sale_price=Decimal(sale),
                                  minimum_stock=5, reorder_level=10, is_active=True)
                session.add(product); session.flush()
                session.add(ProductBarcode(product_id=product.id, barcode=barcode, barcode_type="EAN", is_primary=True, is_active=True))
                session.add(StockMovement(product_id=product.id, stock_location_id=box.id, movement_type="DEMO_OPENING", quantity=qty,
                                          direction="IN", unit_cost=Decimal(purchase), business_date=today,
                                          reference_type="DEMO", reference_id=sku, idempotency_key=_key()))
            products.append(product)

        customer = session.scalar(select(Customer).where(Customer.code == "DEMO-C001"))
        if customer is None:
            customer = Customer(code="DEMO-C001", name="عميل تجريبي", phone="777000001", address="صنعاء", credit_limit=100000, is_active=True)
            session.add(customer); session.flush()

        supplier = session.scalar(select(Supplier).where(Supplier.code == "DEMO-S001"))
        if supplier is None:
            supplier = Supplier(code="DEMO-S001", name="مورد تجريبي", phone="777000002", address="صنعاء", credit_limit=500000, is_active=True)
            session.add(supplier); session.flush()

        cash = session.scalar(select(Cashbox).where(Cashbox.code == "CASH"))
        cash_method = session.scalar(select(PaymentMethod).where(PaymentMethod.code == "CASH"))
        category_exp = session.scalar(select(ExpenseCategory).where(ExpenseCategory.name == "أخرى"))

        purchase = session.scalar(select(Purchase).where(Purchase.document_no == "DEMO-P-001"))
        if purchase is None:
            p1, p2 = products[0], products[1]
            total = Decimal("5000")
            purchase = Purchase(document_no="DEMO-P-001", supplier_id=supplier.id, business_date=today,
                                 subtotal=total, discount=0, tax=0, total=total, paid_amount=total,
                                 credit_amount=0, status="CONFIRMED", payment_status="PAID", idempotency_key=_key())
            session.add(purchase); session.flush()
            session.add_all([
                PurchaseItem(purchase_id=purchase.id, product_id=p1.id, quantity=25, unit_cost=100, discount=0, total=2500),
                PurchaseItem(purchase_id=purchase.id, product_id=p2.id, quantity=10, unit_cost=250, discount=0, total=2500),
                PurchasePayment(purchase_id=purchase.id, payment_method="CASH", amount=total, currency="BASE", reference_no="DEMO-PAY-001"),
                SupplierAccountMovement(supplier_id=supplier.id, movement_type="PURCHASE", amount=total, direction="IN", currency="BASE",
                                        reference_type="PURCHASE", reference_id=str(purchase.id), business_date=today, idempotency_key=_key()),
                SupplierPayment(supplier_id=supplier.id, amount=total, currency="BASE", payment_method="CASH", business_date=today,
                                reference_no="DEMO-PAY-001", idempotency_key=_key()),
            ])

        sale = session.scalar(select(Sale).where(Sale.document_no == "DEMO-S-001"))
        if sale is None:
            p1, p2 = products[0], products[2]
            total = Decimal("575")
            sale = Sale(document_no="DEMO-S-001", customer_id=customer.id, business_date=today, subtotal=total,
                        discount=0, tax=0, total=total, paid_amount=total, credit_amount=0,
                        status="CONFIRMED", payment_status="PAID", idempotency_key=_key())
            session.add(sale); session.flush()
            session.add_all([
                SaleItem(sale_id=sale.id, product_id=p1.id, quantity=2, unit_price=100, discount=0, total=200, cost_price_snapshot=80),
                SaleItem(sale_id=sale.id, product_id=p2.id, quantity=3, unit_price=125, discount=0, total=375, cost_price_snapshot=120),
                SalePayment(sale_id=sale.id, payment_method="CASH", amount=total, currency="BASE", reference_no="DEMO-S-PAY-001"),
                CustomerAccountMovement(customer_id=customer.id, movement_type="SALE", amount=total, direction="IN", currency="BASE",
                                        reference_type="SALE", reference_id=str(sale.id), business_date=today, idempotency_key=_key()),
                CustomerPayment(customer_id=customer.id, amount=total, currency="BASE", payment_method="CASH", business_date=today,
                                reference_no="DEMO-S-PAY-001", idempotency_key=_key()),
            ])
            session.add(StockMovement(product_id=p1.id, stock_location_id=box.id, movement_type="DEMO_SALE", quantity=2, direction="OUT",
                                      unit_cost=80, reference_type="SALE", reference_id=str(sale.id), business_date=today, idempotency_key=_key()))
            session.add(StockMovement(product_id=p2.id, stock_location_id=box.id, movement_type="DEMO_SALE", quantity=3, direction="OUT",
                                      unit_cost=120, reference_type="SALE", reference_id=str(sale.id), business_date=today, idempotency_key=_key()))

        if category_exp and cash_method and not session.scalar(select(Expense).where(Expense.expense_no == "DEMO-E-001")):
            session.add(Expense(expense_no="DEMO-E-001", category_id=category_exp.id, description="مصروف تشغيل تجريبي",
                                amount=1000, currency="BASE", business_date=today, status="CONFIRMED", payment_status="PAID",
                                payment_method_id=cash_method.id, idempotency_key=_key()))
        if cash and not session.scalar(select(Revenue).where(Revenue.revenue_no == "DEMO-R-001")):
            session.add(Revenue(revenue_no="DEMO-R-001", description="إيراد إضافي تجريبي", amount=1500, currency="BASE",
                                business_date=today, payment_method_id=cash_method.id, cashbox_id=cash.id, status="CONFIRMED", idempotency_key=_key()))

        session.commit()
        DEMO_MARKER.write_text(json.dumps({"seeded_at": today, "mode": "demo"}, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"products": len(products), "customers": 1, "suppliers": 1, "sales": 1, "purchases": 1, "expenses": 1, "revenues": 1}
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def prepare_for_delivery() -> None:
    """Remove business/test data while preserving authentication, license and schema."""
    initialize_database()
    session = SessionLocal()
    keep = {"users", "roles", "permissions", "user_roles", "role_permissions", "audit_logs", "alembic_version"}
    try:
        session.execute(text("PRAGMA foreign_keys=OFF"))
        tables = list(Base.metadata.tables)
        for table_name in reversed(tables):
            if table_name in keep:
                continue
            session.execute(delete(Base.metadata.tables[table_name]))
        session.commit()
    finally:
        session.execute(text("PRAGMA foreign_keys=ON"))
        session.close()
    try:
        if DEMO_MARKER.exists():
            DEMO_MARKER.unlink()
    except OSError:
        pass
    # Restore required defaults after clearing business records.
    initialize_database()
