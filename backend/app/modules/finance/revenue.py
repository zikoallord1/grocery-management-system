from datetime import date
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import DateTime, Integer, Numeric, String, ForeignKey, func, select
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.database import Base, get_session
from backend.app.modules.finance.service import CashboxService


class Revenue(Base):
    __tablename__ = "revenues"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    revenue_no: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="BASE")
    business_date: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    payment_method_id: Mapped[int] = mapped_column(ForeignKey("payment_methods.id"), nullable=False)
    cashbox_id: Mapped[int] = mapped_column(ForeignKey("cashboxes.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="CONFIRMED")
    idempotency_key: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    created_at: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.current_timestamp())


class RevenueService:
    def __init__(self, session=None):
        self._session = session or get_session()
        self._owns_session = session is None

    def create_revenue(self, *, revenue_no: str, description: str, amount: Decimal,
                       business_date: str, payment_method_id: int,
                       idempotency_key: str | None = None) -> Revenue:
        from backend.app.modules.finance.models import PaymentMethod

        if amount <= 0:
            raise ValueError("مبلغ الإيراد يجب أن يكون أكبر من صفر.")
        if not description.strip():
            raise ValueError("بيان الإيراد مطلوب.")
        key = idempotency_key or str(uuid4())
        if self._session.scalar(select(Revenue.id).where(Revenue.idempotency_key == key)) is not None:
            raise ValueError("عملية الإيراد مكررة.")
        method = self._session.get(PaymentMethod, payment_method_id)
        if method is None or not method.is_active or method.cashbox_id is None:
            raise ValueError("وسيلة الدفع غير صالحة أو غير مرتبطة بحساب مالي.")
        revenue = Revenue(
            revenue_no=revenue_no,
            description=description.strip(),
            amount=amount,
            currency="BASE",
            business_date=business_date,
            payment_method_id=payment_method_id,
            cashbox_id=method.cashbox_id,
            status="CONFIRMED",
            idempotency_key=key,
        )
        self._session.add(revenue)
        self._session.flush()
        CashboxService(self._session).move_money(
            cashbox_id=method.cashbox_id,
            amount=amount,
            direction="IN",
            movement_type="OTHER_REVENUE",
            business_date=business_date,
            idempotency_key=f"{key}:cashbox",
            reference_type="REVENUE",
            reference_id=str(revenue.id),
        )
        if self._owns_session:
            self._session.commit()
        return revenue
