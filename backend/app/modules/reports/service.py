from dataclasses import dataclass
from typing import Any
from decimal import Decimal

from sqlalchemy import case, func, select

from backend.app.core.models import (
    CustomerAccountMovement,
    Product,
    Purchase,
    Sale,
    SaleItem,
    StockMovement,
    SupplierAccountMovement,
)
from backend.app.modules.finance.models import CashboxMovement, Expense


@dataclass(frozen=True)
class DashboardSummary:
    sales_total: Decimal
    sales_paid: Decimal
    sales_credit: Decimal
    purchases_total: Decimal
    purchases_paid: Decimal
    purchases_credit: Decimal
    expenses_total: Decimal
    cash_balance: Decimal
    customer_receivables: Decimal
    supplier_payables: Decimal
    gross_profit: Decimal


@dataclass(frozen=True)
class StatementRow:
    business_date: str
    movement_type: str
    amount: Decimal
    direction: str
    reference_type: str | None
    reference_id: str | None


class ReportService:
    """Read-only reporting queries over the transactional core."""

    def __init__(self, session):
        self._session = session

    @staticmethod
    def _period_filter(column, date_from: str, date_to: str):
        return (column >= date_from, column <= date_to)

    @staticmethod
    def _as_of_filter(column, date_to: str):
        return column <= date_to

    def dashboard_summary(self, *, date_from: str, date_to: str) -> DashboardSummary:
        sales_total = self._sum(
            select(func.coalesce(func.sum(Sale.total), 0)).where(
                *self._period_filter(Sale.business_date, date_from, date_to),
                Sale.status == "CONFIRMED",
            )
        )
        sales_paid = self._sum(
            select(func.coalesce(func.sum(Sale.paid_amount), 0)).where(
                *self._period_filter(Sale.business_date, date_from, date_to),
                Sale.status == "CONFIRMED",
            )
        )
        sales_credit = self._sum(
            select(func.coalesce(func.sum(Sale.credit_amount), 0)).where(
                *self._period_filter(Sale.business_date, date_from, date_to),
                Sale.status == "CONFIRMED",
            )
        )

        purchases_total = self._sum(
            select(func.coalesce(func.sum(Purchase.total), 0)).where(
                *self._period_filter(Purchase.business_date, date_from, date_to),
                Purchase.status == "CONFIRMED",
            )
        )
        purchases_paid = self._sum(
            select(func.coalesce(func.sum(Purchase.paid_amount), 0)).where(
                *self._period_filter(Purchase.business_date, date_from, date_to),
                Purchase.status == "CONFIRMED",
            )
        )
        purchases_credit = self._sum(
            select(func.coalesce(func.sum(Purchase.credit_amount), 0)).where(
                *self._period_filter(Purchase.business_date, date_from, date_to),
                Purchase.status == "CONFIRMED",
            )
        )

        expenses_total = self._sum(
            select(func.coalesce(func.sum(Expense.amount), 0)).where(
                *self._period_filter(Expense.business_date, date_from, date_to),
                Expense.status == "CONFIRMED",
            )
        )

        cash_balance = self._sum(
            select(
                func.coalesce(
                    func.sum(
                        case(
                            (CashboxMovement.direction == "IN", CashboxMovement.amount),
                            (CashboxMovement.direction == "OUT", -CashboxMovement.amount),
                            else_=0,
                        )
                    ),
                    0,
                )
            ).where(self._as_of_filter(CashboxMovement.business_date, date_to))
        )

        customer_receivables = self._sum(
            select(
                func.coalesce(
                    func.sum(
                        case(
                            (CustomerAccountMovement.direction == "DEBIT", CustomerAccountMovement.amount),
                            (CustomerAccountMovement.direction == "CREDIT", -CustomerAccountMovement.amount),
                            else_=0,
                        )
                    ),
                    0,
                )
            ).where(self._as_of_filter(CustomerAccountMovement.business_date, date_to))
        )

        supplier_payables = self._sum(
            select(
                func.coalesce(
                    func.sum(
                        case(
                            (SupplierAccountMovement.direction == "CREDIT", SupplierAccountMovement.amount),
                            (SupplierAccountMovement.direction == "DEBIT", -SupplierAccountMovement.amount),
                            else_=0,
                        )
                    ),
                    0,
                )
            ).where(self._as_of_filter(SupplierAccountMovement.business_date, date_to))
        )

        gross_profit = self._sum(
            select(
                func.coalesce(
                    func.sum(
                        SaleItem.total
                        - (SaleItem.quantity * SaleItem.cost_price_snapshot)
                    ),
                    0,
                )
            ).join(Sale, Sale.id == SaleItem.sale_id).where(
                *self._period_filter(Sale.business_date, date_from, date_to),
                Sale.status == "CONFIRMED",
            )
        )

        return DashboardSummary(
            sales_total=sales_total,
            sales_paid=sales_paid,
            sales_credit=sales_credit,
            purchases_total=purchases_total,
            purchases_paid=purchases_paid,
            purchases_credit=purchases_credit,
            expenses_total=expenses_total,
            cash_balance=cash_balance,
            customer_receivables=customer_receivables,
            supplier_payables=supplier_payables,
            gross_profit=gross_profit,
        )

    def low_stock_count(self) -> int:
        """Count active products whose total stock is at or below minimum stock."""
        balance = (
            select(
                StockMovement.product_id.label("product_id"),
                func.coalesce(
                    func.sum(
                        case(
                            (StockMovement.direction == "IN", StockMovement.quantity),
                            (StockMovement.direction == "OUT", -StockMovement.quantity),
                            else_=0,
                        )
                    ),
                    0,
                ).label("quantity"),
            )
            .group_by(StockMovement.product_id)
            .subquery()
        )
        statement = select(func.count(Product.id)).outerjoin(
            balance, balance.c.product_id == Product.id
        ).where(
            Product.is_active.is_(True),
            func.coalesce(balance.c.quantity, 0) <= Product.minimum_stock,
        )
        return int(self._session.execute(statement).scalar_one())

    def customer_statement(
        self,
        *,
        customer_id: int,
        date_from: str,
        date_to: str,
        fields: tuple[str, ...] | None = None,
    ) -> list[dict[str, Any]]:
        rows = self._session.execute(
            select(CustomerAccountMovement)
            .where(
                CustomerAccountMovement.customer_id == customer_id,
                CustomerAccountMovement.business_date >= date_from,
                CustomerAccountMovement.business_date <= date_to,
            )
            .order_by(CustomerAccountMovement.business_date, CustomerAccountMovement.id)
        ).scalars()
        return self._project_statement(rows, fields)

    def supplier_statement(
        self,
        *,
        supplier_id: int,
        date_from: str,
        date_to: str,
        fields: tuple[str, ...] | None = None,
    ) -> list[dict[str, Any]]:
        rows = self._session.execute(
            select(SupplierAccountMovement)
            .where(
                SupplierAccountMovement.supplier_id == supplier_id,
                SupplierAccountMovement.business_date >= date_from,
                SupplierAccountMovement.business_date <= date_to,
            )
            .order_by(SupplierAccountMovement.business_date, SupplierAccountMovement.id)
        ).scalars()
        return self._project_statement(rows, fields)

    def cashbox_statement(
        self,
        *,
        cashbox_id: int,
        date_from: str,
        date_to: str,
        fields: tuple[str, ...] | None = None,
    ) -> list[dict[str, Any]]:
        rows = self._session.execute(
            select(CashboxMovement)
            .where(
                CashboxMovement.cashbox_id == cashbox_id,
                CashboxMovement.business_date >= date_from,
                CashboxMovement.business_date <= date_to,
            )
            .order_by(CashboxMovement.business_date, CashboxMovement.id)
        ).scalars()
        return self._project_statement(rows, fields)

    @staticmethod
    def _project_statement(rows, fields: tuple[str, ...] | None) -> list[dict[str, Any]]:
        allowed = {
            "business_date",
            "movement_type",
            "amount",
            "direction",
            "reference_type",
            "reference_id",
        }
        selected = tuple(fields or (
            "business_date",
            "movement_type",
            "amount",
            "direction",
            "reference_type",
            "reference_id",
        ))
        unknown = set(selected) - allowed
        if unknown:
            raise ValueError(f"حقول كشف غير مدعومة: {', '.join(sorted(unknown))}")
        result = []
        for row in rows:
            values = {
                "business_date": row.business_date,
                "movement_type": row.movement_type,
                "amount": Decimal(str(row.amount)),
                "direction": row.direction,
                "reference_type": row.reference_type,
                "reference_id": row.reference_id,
            }
            result.append({field: values[field] for field in selected})
        return result

    def _sum(self, statement) -> Decimal:
        return Decimal(str(self._session.execute(statement).scalar_one()))
