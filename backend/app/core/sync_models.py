from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.database import Base


class SyncTransaction(Base):
    __tablename__ = "sync_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_transaction_id: Mapped[str] = mapped_column(String(150), unique=True, index=True)
    idempotency_key: Mapped[str] = mapped_column(String(150), unique=True, index=True)
    document_type: Mapped[str] = mapped_column(String(60), nullable=False)
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING", index=True)
    temp_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    final_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    server_received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    created_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    accepted_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    settlement_status: Mapped[str] = mapped_column(String(20), nullable=False, default="OPEN")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    reversed_transaction_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
