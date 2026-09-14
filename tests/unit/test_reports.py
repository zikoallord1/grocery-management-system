from decimal import Decimal
from uuid import uuid4

import pytest

from backend.app.core.database import get_session, initialize_database
from backend.app.core.models import Product, Sale, SaleItem, Unit
from backend.app.modules.reports.service import ReportService


@pytest.fixture(autouse=True)
def initialize_db():
    initialize_database()


def test_dashboard_summary_calculates_sales_and_gross_profit_for_period():
    session = get_session()
    suffix = uuid4().hex[:8]
    business_date = "2099-12-31"

    try:
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
