from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.database import Base


class SaleReturn(Base):
    __tablename__ = "sale_returns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_no: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    sale_id: Mapped[int] = mapped_column(ForeignKey("sales.id"), nullable=False, index=True)
    business_date: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    refunded_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    credit_reduction: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="CONFIRMED")
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    created_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.current_timestamp())


class SaleReturnItem(Base):
    __tablename__ = "sale_return_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    return_id: Mapped[int] = mapped_column(ForeignKey("sale_returns.id"), nullable=False, index=True)
    sale_item_id: Mapped[int] = mapped_column(ForeignKey("sale_items.id"), nullable=False, index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False, index=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)


class PurchaseReturn(Base):
    __tablename__ = "purchase_returns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_no: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    purchase_id: Mapped[int] = mapped_column(ForeignKey("purchases.id"), nullable=False, index=True)
    business_date: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    refunded_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    credit_reduction: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="CONFIRMED")
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    created_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.current_timestamp())


class PurchaseReturnItem(Base):
    __tablename__ = "purchase_return_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    return_id: Mapped[int] = mapped_column(ForeignKey("purchase_returns.id"), nullable=False, index=True)
    purchase_item_id: Mapped[int] = mapped_column(ForeignKey("purchase_items.id"), nullable=False, index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False, index=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
