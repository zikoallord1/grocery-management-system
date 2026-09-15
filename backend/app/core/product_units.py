from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.database import Base


class ProductUnit(Base):
    """Per-product unit definition. Conversion is never global: each product owns its factor."""

    __tablename__ = "product_units"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False, index=True)
    unit_id: Mapped[int] = mapped_column(ForeignKey("units.id"), nullable=False, index=True)
    conversion_factor: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    sale_price: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    purchase_price: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    barcode: Mapped[str | None] = mapped_column(String(100), nullable=True, unique=True, index=True)
    is_base: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    __table_args__ = (
        UniqueConstraint("product_id", "unit_id", name="uq_product_unit"),
        CheckConstraint("conversion_factor > 0", name="ck_product_unit_factor_positive"),
    )


class SaleItemUnit(Base):
    """Immutable transaction snapshot of the unit actually sold."""

    __tablename__ = "sale_item_units"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sale_item_id: Mapped[int] = mapped_column(ForeignKey("sale_items.id"), nullable=False, unique=True)
    unit_id: Mapped[int] = mapped_column(ForeignKey("units.id"), nullable=False)
    entered_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    conversion_factor: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    base_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    unit_name_snapshot: Mapped[str] = mapped_column(String(100), nullable=False)
    unit_symbol_snapshot: Mapped[str] = mapped_column(String(30), nullable=False)

    __table_args__ = (
        CheckConstraint("entered_quantity > 0", name="ck_sale_item_unit_entered_positive"),
        CheckConstraint("conversion_factor > 0", name="ck_sale_item_unit_factor_positive"),
        CheckConstraint("base_quantity > 0", name="ck_sale_item_unit_base_positive"),
    )


class PurchaseItemUnit(Base):
    """Immutable transaction snapshot of the unit actually purchased/received."""

    __tablename__ = "purchase_item_units"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    purchase_item_id: Mapped[int] = mapped_column(ForeignKey("purchase_items.id"), nullable=False, unique=True)
    unit_id: Mapped[int] = mapped_column(ForeignKey("units.id"), nullable=False)
    entered_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    conversion_factor: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    base_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    unit_name_snapshot: Mapped[str] = mapped_column(String(100), nullable=False)
    unit_symbol_snapshot: Mapped[str] = mapped_column(String(30), nullable=False)

    __table_args__ = (
        CheckConstraint("entered_quantity > 0", name="ck_purchase_item_unit_entered_positive"),
        CheckConstraint("conversion_factor > 0", name="ck_purchase_item_unit_factor_positive"),
        CheckConstraint("base_quantity > 0", name="ck_purchase_item_unit_base_positive"),
    )
