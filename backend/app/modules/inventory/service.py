from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import case, func, select
from sqlalchemy.exc import IntegrityError

from backend.app.core.database import get_session
from backend.app.core.models import StockMovement


class InventoryError(Exception):
    """Base error for inventory operations."""


class InsufficientStockError(InventoryError):
    """Raised when an outbound movement would create negative stock."""


class DuplicateInventoryOperationError(InventoryError):
    """Raised when an idempotency key already exists."""


@dataclass(frozen=True)
class StockBalance:
    product_id: int
    stock_location_id: int
    quantity: Decimal


class InventoryService:
    def __init__(self, session=None):
        self._session = session
        self._owns_session = session is None

    def _get_session(self):
        if self._session is None:
            self._session = get_session()
        return self._session

    def close(self):
        if self._owns_session and self._session is not None:
            self._session.close()
            self._session = None

    def get_balance(self, product_id: int, stock_location_id: int) -> Decimal:
        session = self._get_session()

        total = session.execute(
            select(
                func.coalesce(
                    func.sum(
                        case(
                            (StockMovement.direction == "IN", StockMovement.quantity),
                            (StockMovement.direction == "OUT", -StockMovement.quantity),
                            else_=0,
                        )
                    ),
                    0,
                )
            ).where(
                StockMovement.product_id == product_id,
                StockMovement.stock_location_id == stock_location_id,
            )
        ).scalar_one()

        return Decimal(str(total))

    def _ensure_idempotency_unused(self, idempotency_key: str):
        session = self._get_session()

        existing = session.execute(
            select(StockMovement.id).where(
                StockMovement.idempotency_key == idempotency_key
            )
        ).scalar_one_or_none()

        if existing is not None:
            raise DuplicateInventoryOperationError(
                f"Inventory operation already exists: {idempotency_key}"
            )

    def add_stock(
        self,
        *,
        product_id: int,
        stock_location_id: int,
        quantity: Decimal,
        unit_cost: Decimal,
        business_date: str,
        idempotency_key: str,
        reference_type: str = "MANUAL",
        reference_id: str | None = None,
        created_by: int | None = None,
    ) -> StockMovement:
        return self._create_movement(
            product_id=product_id,
            stock_location_id=stock_location_id,
            quantity=quantity,
            direction="IN",
            unit_cost=unit_cost,
            business_date=business_date,
            idempotency_key=idempotency_key,
            reference_type=reference_type,
            reference_id=reference_id,
            created_by=created_by,
        )

    def remove_stock(
        self,
        *,
        product_id: int,
        stock_location_id: int,
        quantity: Decimal,
        unit_cost: Decimal,
        business_date: str,
        idempotency_key: str,
        reference_type: str = "MANUAL",
        reference_id: str | None = None,
        created_by: int | None = None,
        allow_negative: bool = False,
    ) -> StockMovement:
        if quantity <= 0:
            raise InventoryError("Quantity must be greater than zero.")

        current = self.get_balance(product_id, stock_location_id)

        if not allow_negative and current < quantity:
            raise InsufficientStockError(
                f"Insufficient stock. Current={current}, requested={quantity}"
            )

        return self._create_movement(
            product_id=product_id,
            stock_location_id=stock_location_id,
            quantity=quantity,
            direction="OUT",
            unit_cost=unit_cost,
            business_date=business_date,
            idempotency_key=idempotency_key,
            reference_type=reference_type,
            reference_id=reference_id,
            created_by=created_by,
        )

    def _create_movement(
        self,
        *,
        product_id: int,
        stock_location_id: int,
        quantity: Decimal,
        direction: str,
        unit_cost: Decimal,
        business_date: str,
        idempotency_key: str,
        reference_type: str,
        reference_id: str | None,
        created_by: int | None,
    ) -> StockMovement:
        if quantity <= 0:
            raise InventoryError("Quantity must be greater than zero.")

        if direction not in {"IN", "OUT"}:
            raise InventoryError("Direction must be IN or OUT.")

        self._ensure_idempotency_unused(idempotency_key)

        session = self._get_session()

        movement_type = (
            "ADJUSTMENT_IN" if direction == "IN" else "ADJUSTMENT_OUT"
        )

        movement = StockMovement(
            product_id=product_id,
            stock_location_id=stock_location_id,
            movement_type=movement_type,
            quantity=quantity,
            direction=direction,
            unit_cost=unit_cost,
            reference_type=reference_type,
            reference_id=reference_id,
            business_date=business_date,
            created_by=created_by,
            idempotency_key=idempotency_key,
        )

        session.add(movement)

        try:
            session.flush()
            if self._owns_session:
                session.commit()
        except IntegrityError as exc:
            if self._owns_session:
                session.rollback()
            raise DuplicateInventoryOperationError(
                f"Inventory operation could not be created: {idempotency_key}"
            ) from exc

        return movement

