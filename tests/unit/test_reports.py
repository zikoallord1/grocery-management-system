from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import delete, select

from backend.app.core.database import get_session, initialize_database
from backend.app.core.models import Customer, CustomerAccountMovement, Product, Sale, SaleItem, Unit
from backend.app.modules.reports.service import ReportService


@pytest.fixture(autouse=True)
def initialize_db():
    initialize_database()


def test_dashboard_summary_calculates_sales_and_gross_profit_for_period():
    session = get_session()
    suffix = uuid4().hex[:8]
    business_date = "2099-12-31"

    try:
        old_sales = select(Sale.id).where(Sale.document_no.like("RPT-%"))
        session.execute(delete(SaleItem).where(SaleItem.sale_id.in_(old_sales)))
        session.execute(delete(Sale).where(Sale.document_no.like("RPT-%")))
        session.commit()
        unit = Unit(name=f"تقرير-{suffix}", symbol="وحدة")
        session.add(unit)
        session.flush()

        product = Product(
            sku=f"REPORT-{suffix}",
            name="منتج تقرير",
            default_unit_id=unit.id,
            purchase_price=Decimal("60"),
            sale_price=Decimal("100"),
        )
        session.add(product)
        session.flush()

        sale = Sale(
            document_no=f"RPT-{suffix}",
            business_date=business_date,
            subtotal=Decimal("200"),
            discount=Decimal("0"),
            tax=Decimal("0"),
            total=Decimal("200"),
            paid_amount=Decimal("150"),
            credit_amount=Decimal("50"),
            status="CONFIRMED",
            payment_status="PARTIAL",
            idempotency_key=f"REPORT-SALE-{suffix}",
        )
        session.add(sale)
        session.flush()

        session.add(
            SaleItem(
                sale_id=sale.id,
                product_id=product.id,
                quantity=Decimal("2"),
                unit_price=Decimal("100"),
                discount=Decimal("0"),
                total=Decimal("200"),
                cost_price_snapshot=Decimal("60"),
            )
        )
        session.commit()

        summary = ReportService(session).dashboard_summary(
            date_from=business_date,
            date_to=business_date,
        )

        assert summary.sales_total == Decimal("200.00")
        assert summary.sales_paid == Decimal("150.00")
        assert summary.sales_credit == Decimal("50.00")
        assert summary.gross_profit == Decimal("80.00")
    finally:
        session.close()


def test_customer_statement_supports_period_and_selected_fields():
    session = get_session()
    suffix = uuid4().hex[:8]
    try:
        customer = Customer(code=f"ST-{suffix}", name="عميل كشف")
        session.add(customer)
        session.flush()
        session.add(
            CustomerAccountMovement(
                customer_id=customer.id,
                movement_type="SALE_CREDIT",
                amount=Decimal("125"),
                direction="DEBIT",
                business_date="2099-01-10",
                reference_type="SALE",
                reference_id="S-1",
                idempotency_key=f"statement-{suffix}",
            )
        )
        session.commit()
        rows = ReportService(session).customer_statement(
            customer_id=customer.id,
            date_from="2099-01-01",
            date_to="2099-01-31",
            fields=("business_date", "amount", "reference_id"),
        )
        assert rows == [{"business_date": "2099-01-10", "amount": Decimal("125.00"), "reference_id": "S-1"}]
        with pytest.raises(ValueError):
            ReportService(session).customer_statement(
                customer_id=customer.id,
                date_from="2099-01-01",
                date_to="2099-01-31",
                fields=("password",),
            )
    finally:
        session.rollback()
        session.close()
