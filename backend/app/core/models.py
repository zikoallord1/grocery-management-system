from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.database import Base


# -----------------------------
# Existing inventory entities
# -----------------------------

class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False, unique=True, index=True)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )


class Unit(Base):
    __tablename__ = "units"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    symbol: Mapped[str] = mapped_column(String(30), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sku: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id"), nullable=True
    )
    default_unit_id: Mapped[int] = mapped_column(
        ForeignKey("units.id"), nullable=False
    )
    purchase_price: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=0
    )
    sale_price: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=0
    )
    minimum_stock: Mapped[Decimal] = mapped_column(
        Numeric(14, 3), nullable=False, default=0
    )
    reorder_level: Mapped[Decimal] = mapped_column(
        Numeric(14, 3), nullable=False, default=0
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )


class ProductBarcode(Base):
    __tablename__ = "product_barcodes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id"), nullable=False, index=True
    )
    barcode: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True, index=True
    )
    barcode_type: Mapped[str] = mapped_column(
        String(30), nullable=False, default="EAN"
    )
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class StockLocation(Base):
    __tablename__ = "stock_locations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True, index=True
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    location_type: Mapped[str] = mapped_column(
        String(30), nullable=False, default="STORE"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class StockMovement(Base):
    __tablename__ = "stock_movements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id"), nullable=False, index=True
    )
    stock_location_id: Mapped[int] = mapped_column(
        ForeignKey("stock_locations.id"), nullable=False, index=True
    )
    movement_type: Mapped[str] = mapped_column(String(40), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    direction: Mapped[str] = mapped_column(String(10), nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=0
    )
    reference_type: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )
    reference_id: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    business_date: Mapped[str] = mapped_column(String(10), nullable=False)
    created_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    idempotency_key: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )

    __table_args__ = (
        CheckConstraint(
            "quantity > 0",
            name="ck_stock_movement_quantity_positive",
        ),
        CheckConstraint(
            "direction IN ('IN', 'OUT')",
            name="ck_stock_movement_direction",
        ),
    )


# -----------------------------
# Sales
# -----------------------------

class Sale(Base):
    __tablename__ = "sales"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_no: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True, index=True
    )
    customer_id: Mapped[int | None] = mapped_column(
        ForeignKey("customers.id"), nullable=True, index=True
    )
    business_date: Mapped[str] = mapped_column(
        String(10), nullable=False, index=True
    )
    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False
    )
    discount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=0
    )
    tax: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=0
    )
    total: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False
    )
    paid_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False
    )
    credit_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="DRAFT"
    )
    payment_status: Mapped[str] = mapped_column(
        String(20), nullable=False
    )
    idempotency_key: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True
    )
    created_by: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )


class SaleItem(Base):
    __tablename__ = "sale_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sale_id: Mapped[int] = mapped_column(
        ForeignKey("sales.id"), nullable=False, index=True
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id"), nullable=False, index=True
    )
    quantity: Mapped[Decimal] = mapped_column(
        Numeric(14, 3), nullable=False
    )
    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False
    )
    discount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=0
    )
    total: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False
    )
    cost_price_snapshot: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False
    )


class SalePayment(Base):
    __tablename__ = "sale_payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sale_id: Mapped[int] = mapped_column(
        ForeignKey("sales.id"), nullable=False, index=True
    )
    payment_method: Mapped[str] = mapped_column(
        String(40), nullable=False
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


# -----------------------------
# Customers
# -----------------------------

class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True, index=True
    )
    name: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True
    )
    phone: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )
    address: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )
    credit_limit: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 2), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )


class CustomerAccountMovement(Base):
    __tablename__ = "customer_account_movements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id"), nullable=False, index=True
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
        DateTime, nullable=False, server_default=func.current_timestamp()
    )


class CustomerPayment(Base):
    __tablename__ = "customer_payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id"), nullable=False, index=True
    )
    amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False
    )
    currency: Mapped[str] = mapped_column(
        String(10), nullable=False, default="BASE"
    )
    payment_method: Mapped[str] = mapped_column(
        String(40), nullable=False
    )
    business_date: Mapped[str] = mapped_column(
        String(10), nullable=False
    )
    reference_no: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    idempotency_key: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True
    )
    created_by: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )



