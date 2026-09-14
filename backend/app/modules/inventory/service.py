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
            select(func.coalesce(func.sum(case(
                (StockMovement.direction == "IN", StockMovement.quantity),
                (StockMovement.direction == "OUT", -StockMovement.quantity),
                else_=0,
            )), 0)).where(
                StockMovement.product_id == product_id,
                StockMovement.stock_location_id == stock_location_id,
            )
        ).scalar_one()
        return Decimal(str(total))

    def _ensure_idempotency_unused(self, idempotency_key: str):
        session = self._get_session()
        existing = session.execute(select(StockMovement.id).where(StockMovement.idempotency_key == idempotency_key)).scalar_one_or_none()
        if existing is not None:
            raise DuplicateInventoryOperationError(f"Inventory operation already exists: {idempotency_key}")

    def add_stock(self, *, product_id: int, stock_location_id: int, quantity: Decimal, unit_cost: Decimal,
                  business_date: str, idempotency_key: str, reference_type: str = "MANUAL",
                  reference_id: str | None = None, created_by: int | None = None) -> StockMovement:
        return self._create_movement(product_id=product_id, stock_location_id=stock_location_id, quantity=quantity,
                                     direction="IN", unit_cost=unit_cost, business_date=business_date,
                                     idempotency_key=idempotency_key, reference_type=reference_type,
                                     reference_id=reference_id, created_by=created_by, movement_type="ADJUSTMENT_IN")

    def remove_stock(self, *, product_id: int, stock_location_id: int, quantity: Decimal, unit_cost: Decimal,
                     business_date: str, idempotency_key: str, reference_type: str = "MANUAL",
                     reference_id: str | None = None, created_by: int | None = None,
                     allow_negative: bool = False) -> StockMovement:
        if quantity <= 0:
            raise InventoryError("Quantity must be greater than zero.")
        current = self.get_balance(product_id, stock_location_id)
        if not allow_negative and current < quantity:
            raise InsufficientStockError(f"Insufficient stock. Current={current}, requested={quantity}")
        return self._create_movement(product_id=product_id, stock_location_id=stock_location_id, quantity=quantity,
                                     direction="OUT", unit_cost=unit_cost, business_date=business_date,
                                     idempotency_key=idempotency_key, reference_type=reference_type,
                                     reference_id=reference_id, created_by=created_by, movement_type="ADJUSTMENT_OUT")

    def transfer_stock(self, *, product_id: int, source_location_id: int, target_location_id: int,
                       quantity: Decimal, unit_cost: Decimal, business_date: str,
                       idempotency_key: str, created_by: int | None = None) -> tuple[StockMovement, StockMovement]:
        if source_location_id == target_location_id:
            raise InventoryError("مصدر التحويل ومخزن الاستلام يجب أن يكونا مختلفين.")
        if quantity <= 0:
            raise InventoryError("Quantity must be greater than zero.")
        self._ensure_idempotency_unused(idempotency_key)
        session = self._get_session()
        balance = self.get_balance(product_id, source_location_id)
        if balance < quantity:
            raise InsufficientStockError(f"Insufficient stock. Current={balance}, requested={quantity}")
        transfer_id = idempotency_key
        out_key = f"{idempotency_key}:OUT"
        in_key = f"{idempotency_key}:IN"
        self._ensure_idempotency_unused(out_key)
        self._ensure_idempotency_unused(in_key)
        try:
            out_move = StockMovement(product_id=product_id, stock_location_id=source_location_id,
                movement_type="TRANSFER_OUT", quantity=quantity, direction="OUT", unit_cost=unit_cost,
                reference_type="STOCK_TRANSFER", reference_id=transfer_id, business_date=business_date,
                created_by=created_by, idempotency_key=out_key)
            in_move = StockMovement(product_id=product_id, stock_location_id=target_location_id,
                movement_type="TRANSFER_IN", quantity=quantity, direction="IN", unit_cost=unit_cost,
                reference_type="STOCK_TRANSFER", reference_id=transfer_id, business_date=business_date,
                created_by=created_by, idempotency_key=in_key)
            session.add_all([out_move, in_move])
            session.flush()
            if self._owns_session:
                session.commit()
            return out_move, in_move
        except IntegrityError as exc:
            if self._owns_session:
                session.rollback()
            raise DuplicateInventoryOperationError(f"Inventory transfer could not be created: {idempotency_key}") from exc

    def adjust_stock(self, *, product_id: int, stock_location_id: int, actual_quantity: Decimal,
                     unit_cost: Decimal, business_date: str, idempotency_key: str,
                     reason: str | None = None, created_by: int | None = None) -> StockMovement | None:
        if actual_quantity < 0:
            raise InventoryError("الكمية الفعلية لا يمكن أن تكون سالبة.")
        self._ensure_idempotency_unused(idempotency_key)
        current = self.get_balance(product_id, stock_location_id)
        difference = actual_quantity - current
        if difference == 0:
            raise InventoryError("الكمية الفعلية مساوية للرصيد الحالي، لا توجد تسوية.")
        reference_id = reason.strip() if reason and reason.strip() else None
        if difference > 0:
            return self._create_movement(product_id=product_id, stock_location_id=stock_location_id,
                quantity=difference, direction="IN", unit_cost=unit_cost, business_date=business_date,
                idempotency_key=idempotency_key, reference_type="STOCK_ADJUSTMENT", reference_id=reference_id,
                created_by=created_by, movement_type="ADJUSTMENT_IN")
        return self._create_movement(product_id=product_id, stock_location_id=stock_location_id,
            quantity=-difference, direction="OUT", unit_cost=unit_cost, business_date=business_date,
            idempotency_key=idempotency_key, reference_type="STOCK_ADJUSTMENT", reference_id=reference_id,
            created_by=created_by, movement_type="ADJUSTMENT_OUT")

    def _create_movement(self, *, product_id: int, stock_location_id: int, quantity: Decimal,
                         direction: str, unit_cost: Decimal, business_date: str, idempotency_key: str,
                         reference_type: str, reference_id: str | None, created_by: int | None,
                         movement_type: str | None = None) -> StockMovement:
        if quantity <= 0:
            raise InventoryError("Quantity must be greater than zero.")
        if direction not in {"IN", "OUT"}:
            raise InventoryError("Direction must be IN or OUT.")
        self._ensure_idempotency_unused(idempotency_key)
        session = self._get_session()
        movement = StockMovement(product_id=product_id, stock_location_id=stock_location_id,
            movement_type=movement_type or ("ADJUSTMENT_IN" if direction == "IN" else "ADJUSTMENT_OUT"),
            quantity=quantity, direction=direction, unit_cost=unit_cost, reference_type=reference_type,
            reference_id=reference_id, business_date=business_date, created_by=created_by,
            idempotency_key=idempotency_key)
        session.add(movement)
        try:
            session.flush()
            if self._owns_session:
                session.commit()
        except IntegrityError as exc:
            if self._owns_session:
                session.rollback()
            raise DuplicateInventoryOperationError(f"Inventory operation could not be created: {idempotency_key}") from exc
        return movement
