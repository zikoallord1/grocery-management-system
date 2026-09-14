from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import case, func, select

from backend.app.core.models import (
    CustomerAccountMovement,
    Purchase,
    Sale,
    SaleItem,
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

    def _sum(self, statement) -> Decimal:
        return Decimal(str(self._session.execute(statement).scalar_one()))
