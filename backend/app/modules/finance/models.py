from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.database import Base


class Cashbox(Base):
    __tablename__ = "cashboxes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True, index=True
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    account_type: Mapped[str] = mapped_column(
        String(30), nullable=False, default="CASH"
    )
    currency: Mapped[str] = mapped_column(
        String(10), nullable=False, default="BASE"
    )
    provider_name: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    account_reference: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
    )


class PaymentMethod(Base):
    __tablename__ = "payment_methods"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    method_type: Mapped[str] = mapped_column(
        String(30), nullable=False
    )
    cashbox_id: Mapped[int | None] = mapped_column(
        ForeignKey("cashboxes.id"),
        nullable=True,
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
    )


class CashboxMovement(Base):
    __tablename__ = "cashbox_movements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cashbox_id: Mapped[int] = mapped_column(
        ForeignKey("cashboxes.id"),
        nullable=False,
        index=True,
    )
    movement_type: Mapped[str] = mapped_column(
        String(40), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False
    )
    direction: Mapped[str] = mapped_column(
        String(10), nullable=False
    )
    currency: Mapped[str] = mapped_column(
        String(10), nullable=False, default="BASE"
    )
    reference_type: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )
    reference_id: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    business_date: Mapped[str] = mapped_column(
        String(10), nullable=False
    )
    idempotency_key: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True
    )
    created_by: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
    )


class ExpenseCategory(Base):
    __tablename__ = "expense_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(
        String(150), nullable=False, unique=True, index=True
    )
    description: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )


class Expense(Base):
    __tablename__ = "expenses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    expense_no: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True, index=True
    )
    category_id: Mapped[int] = mapped_column(
        ForeignKey("expense_categories.id"),
        nullable=False,
        index=True,
    )
    description: Mapped[str] = mapped_column(
        String(500), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False
    )
    currency: Mapped[str] = mapped_column(
        String(10), nullable=False, default="BASE"
    )
    business_date: Mapped[str] = mapped_column(
        String(10), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="CONFIRMED"
    )
    payment_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="PAID"
    )
    payment_method_id: Mapped[int | None] = mapped_column(
        ForeignKey("payment_methods.id"),
        nullable=True,
        index=True,
    )
    idempotency_key: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True
    )
    created_by: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
    )


class ExpensePayment(Base):
    __tablename__ = "expense_payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    expense_id: Mapped[int] = mapped_column(
        ForeignKey("expenses.id"),
        nullable=False,
        index=True,
    )
    payment_method_id: Mapped[int] = mapped_column(
        ForeignKey("payment_methods.id"),
        nullable=False,
        index=True,
    )
    amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False
    )
    currency: Mapped[str] = mapped_column(
        String(10), nullable=False, default="BASE"
    )
    reference_no: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
